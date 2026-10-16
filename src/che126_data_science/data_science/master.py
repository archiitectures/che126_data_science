"""Versioned observation exports; legacy Observation/CSV interfaces stay intact."""

import csv
import hashlib
import io
import json
import math
import os
from collections import Counter
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from .observations import CONVERSIONS, UNITS, Observation

SCHEMA_VERSION = "1"
EXTRACTION_VERSION = "separator-v5"


def fingerprint(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()


def atomic_bytes(path: str | Path, data: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    try:
        temporary.write_bytes(data)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_json(path: str | Path, value) -> None:
    atomic_bytes(
        path,
        (
            json.dumps(
                value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False
            )
            + "\n"
        ).encode(),
    )


@dataclass(frozen=True)
class MasterObservation:
    observation_id: str
    source_id: str
    source_type: str
    source_file: str
    source_sha256: str
    sample_id: str
    property: str
    original_property_label: str
    original_value: str
    original_unit: str
    value: float | None = None
    unit: str | None = None
    source_url: str | None = None
    source_page: int | None = None
    source_table: str | None = None
    source_figure: str | None = None
    source_row: str | None = None
    source_column: str | None = None
    extraction_method: str = "unknown"
    extraction_version: str = EXTRACTION_VERSION
    manufacturer: str | None = None
    product: str | None = None
    polymer: str | None = None
    separator_architecture: str | None = None
    coating: str | None = None
    material_grade: str | None = None
    material_class: str | None = None
    sample_form: str | None = None
    electrolyte_state: str = "not_reported"
    electrolyte_salt: str | None = None
    electrolyte_solvent: str | None = None
    electrolyte_concentration: str | None = None
    statistic: str = "reported"
    temperature_C: float | None = None
    temperature_role: str = "unknown"
    duration_min: float | None = None
    heating_rate_C_min: float | None = None
    direction: str = "unspecified"
    method: str | None = None
    measurement_context: str | None = None
    shrinkage_basis: str | None = None
    record_type: str = "unknown"
    replicate_id: str | None = None
    curve_id: str | None = None
    uncertainty: float | None = None
    conversion_metadata: str | None = None
    quality_flag: str | None = None
    review_status: str = "accepted"
    notes: str | None = None
    family_id: str | None = None
    evidence_group: str | None = None
    source_restrictions: str | None = None

    def __post_init__(self):
        if self.review_status not in {"accepted", "pending"}:
            raise ValueError("Invalid review status")
        if self.record_type not in {
            "measured",
            "claimed_range",
            "spec_limit",
            "digitized_estimate",
            "calculated",
            "unknown",
        }:
            raise ValueError("Invalid record type")
        if self.statistic not in {"reported", "typical", "minimum", "maximum", "mean"}:
            raise ValueError("Invalid statistic")
        if self.electrolyte_state not in {"not_reported", "dry", "electrolyte_wet"}:
            raise ValueError("Invalid electrolyte state")
        for name in (
            "temperature_C",
            "duration_min",
            "heating_rate_C_min",
            "uncertainty",
            "value",
        ):
            value = getattr(self, name)
            if value is not None and not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if self.temperature_C is not None and self.temperature_C < -273.15:
            raise ValueError("Temperature below absolute zero")
        if self.temperature_role not in {"measurement", "exposure", "unknown"}:
            raise ValueError("Invalid temperature role")
        if (self.temperature_C is None) != (self.temperature_role == "unknown"):
            raise ValueError("Temperature and role must agree")
        if any(
            getattr(self, n) is not None and getattr(self, n) < 0
            for n in ("duration_min", "uncertainty")
        ):
            raise ValueError("Negative duration or uncertainty")
        if self.review_status == "accepted":
            if (
                not self.sample_id
                or not self.source_sha256
                or not self.original_property_label
            ):
                raise ValueError("Missing identity or source provenance")
            if self.value is None or self.unit is None:
                raise ValueError("Accepted records require normalized value/unit")
            # Reuse legacy physical and unit validation; local citations remain
            # source_file/hash in exports, never the validator-only placeholder.
            Observation(
                record_id=self.observation_id,
                sample_id=self.sample_id,
                material=self.polymer or "not_reported",
                property=self.property,
                value=self.value,
                unit=self.unit,
                source_url=self.source_url or "https://local.invalid/validation-only",
                source_locator=self.source_table
                or self.source_row
                or self.source_figure
                or "source file",
                sample_form=self.sample_form or "not_reported",
                temperature_C=self.temperature_C,
                temperature_role=self.temperature_role,
            )


def make_observation(
    document,
    *,
    label: str,
    prop: str,
    raw_value,
    raw_unit: str,
    sample_id: str,
    **metadata,
) -> MasterObservation:
    """Normalize explicit units. Ambiguity is an exportable review record."""
    unit_for_conversion = metadata.pop("normalization_unit", raw_unit)
    value, unit, conversion, flag = None, None, None, metadata.pop("quality_flag", None)
    try:
        number = float(raw_value)
        if not math.isfinite(number):
            raise ValueError("nonfinite value")
        canonical = UNITS[prop]
        if unit_for_conversion == canonical:
            value, unit = number, canonical
            if raw_unit != canonical:
                conversion = json.dumps(
                    {"unit_alias": raw_unit, "canonical_unit": canonical},
                    sort_keys=True,
                )
        else:
            scale, offset = CONVERSIONS[(unit_for_conversion, canonical)]
            value, unit = number * scale + offset, canonical
            conversion = json.dumps({"scale": scale, "offset": offset}, sort_keys=True)
    except (ValueError, TypeError, KeyError):
        flag = flag or "unresolved_property_value_or_unit"
    if flag:
        metadata["review_status"] = "pending"
    source_url = metadata.pop("source_url", document.url)
    identity = {
        "sha256": document.sha256,
        "sample": sample_id,
        "property": prop,
        "label": label,
        "raw_value": str(raw_value),
        "raw_unit": raw_unit,
        **{
            k: metadata.get(k)
            for k in (
                "source_page",
                "source_table",
                "source_row",
                "source_column",
                "source_figure",
                "statistic",
                "direction",
                "temperature_C",
                "replicate_id",
                "curve_id",
                "duration_min",
                "temperature_role",
                "heating_rate_C_min",
                "polymer",
                "sample_form",
                "separator_architecture",
                "coating",
                "record_type",
                "electrolyte_state",
                "electrolyte_salt",
                "electrolyte_solvent",
                "electrolyte_concentration",
                "method",
                "measurement_context",
                "shrinkage_basis",
            )
        },
    }
    payload = dict(
        observation_id=fingerprint(identity),
        source_id=document.source_id,
        source_type=document.source,
        source_url=source_url,
        source_file=document.path,
        source_sha256=document.sha256,
        source_restrictions=document.restrictions,
        sample_id=sample_id,
        property=prop,
        original_property_label=label,
        original_value=str(raw_value),
        original_unit=raw_unit,
        value=value,
        unit=unit,
        conversion_metadata=conversion,
        quality_flag=flag,
        **metadata,
    )
    try:
        return MasterObservation(**payload)
    except ValueError as exc:
        # Physical-value violations become review evidence, not a silent drop or
        # the rejection of otherwise valid rows in the same source table.
        payload.update(
            review_status="pending",
            quality_flag="validation_failed",
            notes=(payload.get("notes") or "") + " Validation: " + str(exc),
        )
        return MasterObservation(**payload)


def csv_bytes(records: list[dict], columns: list[str]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return stream.getvalue().encode()


def export_master(
    records: list[MasterObservation],
    out_dir: str | Path,
    *,
    measured_only: bool = False,
) -> dict:
    """Stable CSV/Parquet views and explicit review records, replaced atomically."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    by_id = {}
    for row in records:
        existing = by_id.get(row.observation_id)
        if existing and existing != row:
            raise ValueError(f"Conflicting observation ID {row.observation_id}")
        by_id[row.observation_id] = row
    rows = sorted(by_id.values(), key=lambda r: r.observation_id)
    accepted = [
        asdict(r)
        for r in rows
        if r.review_status == "accepted"
        and (not measured_only or r.record_type == "measured")
    ]
    review = [asdict(r) for r in rows if r.review_status == "pending"]
    columns = [f.name for f in fields(MasterObservation)]
    directory = Path(out_dir)
    atomic_bytes(directory / "master_observations.csv", csv_bytes(accepted, columns))
    atomic_bytes(directory / "review_queue.csv", csv_bytes(review, columns))
    numeric = {
        "value",
        "temperature_C",
        "duration_min",
        "heating_rate_C_min",
        "uncertainty",
    }
    schema = pa.schema(
        [
            (
                name,
                pa.float64()
                if name in numeric
                else pa.int64()
                if name == "source_page"
                else pa.string(),
            )
            for name in columns
        ],
        metadata={b"schema_version": SCHEMA_VERSION.encode()},
    )
    sink = pa.BufferOutputStream()
    pq.write_table(
        pa.Table.from_pylist(accepted, schema=schema), sink, compression="zstd"
    )
    atomic_bytes(
        directory / "master_observations.parquet", sink.getvalue().to_pybytes()
    )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "accepted": len(accepted),
        "review": len(review),
        "measured_only": measured_only,
        "by_source": dict(sorted(Counter(r["source_type"] for r in accepted).items())),
        "by_record_type": dict(
            sorted(Counter(r["record_type"] for r in accepted).items())
        ),
        "unknown_temperature": sum(r["temperature_C"] is None for r in accepted),
    }
    atomic_json(directory / "qc_summary.json", summary)
    return summary
