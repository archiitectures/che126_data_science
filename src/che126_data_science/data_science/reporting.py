"""Current coverage and missing-temperature inventories, derived without imputation."""

import csv
import hashlib
import io
import re
from collections import Counter, defaultdict
from pathlib import Path

from .master import atomic_bytes, atomic_json


def gap_status(row):
    if row["property"] in {
        "melting_temperature",
        "meltdown_temperature",
        "shutdown_temperature",
    }:
        return "temperature_is_response_value_not_test_condition"
    text = " ".join(
        str(row.get(k) or "")
        for k in ("method", "measurement_context", "original_property_label")
    )
    if re.search(r"[-+]?\d+(?:\.\d+)?\s*(?:[°º]|deg(?:rees?)?\.?)\s*[CKF]\b", text):
        return "numeric_context_requires_property_link_review"
    if re.search(r"room[ -]temp|ambient[ -]temp", text, re.IGNORECASE):
        return "room_or_ambient_without_supported_numeric_value"
    if re.search(r"\b(?:ASTM|ISO|JIS)\s*[A-Z]?\s*\d", text, re.IGNORECASE):
        return "standard_cited_without_explicit_test_temperature"
    return "no_temperature_in_linked_method"


def refresh(root):
    root = Path(root)
    data = root / "datasets"
    rows = list(csv.DictReader((data / "unique_points.csv").open(newline="")))

    def write(name, columns, records):
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)
        for directory in (data, root / "data/processed"):
            atomic_bytes(directory / name, stream.getvalue().encode())

    for name, keys in (
        ("separator_type_property_coverage.csv", ["polymer", "property"]),
        (
            "separator_product_property_coverage.csv",
            ["polymer", "manufacturer", "product", "property"],
        ),
    ):
        groups = defaultdict(list)
        for row in rows:
            if row["sample_form"] in {"separator", "separator_component"}:
                groups[tuple(row[k] or "Not reported" for k in keys)].append(row)
        records = []
        for key, group in sorted(groups.items()):
            known = [r for r in group if r["temperature_C"] != ""]
            temperatures = sorted({float(r["temperature_C"]) for r in known})
            records.append(
                {
                    **dict(zip(keys, key)),
                    "distinct_points": len(group),
                    "points_with_temperature": len(known),
                    "distinct_temperatures": len(temperatures),
                    "temperatures_C": ";".join(f"{v:g}" for v in temperatures),
                    "temperature_roles": ";".join(
                        sorted({r["temperature_role"] for r in known})
                    ),
                }
            )
        write(
            name,
            keys
            + [
                "distinct_points",
                "points_with_temperature",
                "distinct_temperatures",
                "temperatures_C",
                "temperature_roles",
            ],
            records,
        )
    gaps = [
        {
            **{
                k: r[k]
                for k in (
                    "unique_point_id",
                    "property",
                    "polymer",
                    "sample_id",
                    "source_url",
                    "source_file",
                )
            },
            "temperature_recovery_status": gap_status(r),
            "next_action": "Review the exact sample/property method and source; do not transfer temperatures from an equal value or a general standard.",
        }
        for r in rows
        if r["temperature_C"] == ""
    ]
    gap_fields = [
        "unique_point_id",
        "property",
        "polymer",
        "sample_id",
        "source_url",
        "source_file",
        "temperature_recovery_status",
        "next_action",
    ]
    write("temperature_gap_audit.csv", gap_fields, gaps)
    identity_fields = [
        "unique_point_id",
        "observation_id",
        "sample_id",
        "property",
        "polymer",
        "source_url",
        "source_file",
        "source_sha256",
        "source_table",
        "source_row",
        "source_column",
        "material_identity_status",
        "material_identity_evidence",
        "material_identity_reason",
    ]
    write(
        "material_identity.csv",
        identity_fields,
        ({k: r[k] for k in identity_fields} for r in rows),
    )
    summary = {
        "input_sha256": hashlib.sha256(
            (data / "unique_points.csv").read_bytes()
        ).hexdigest(),
        "distinct_points": len(rows),
        "properties": len({r["property"] for r in rows}),
        "numeric_temperature_points": len(rows) - len(gaps),
        "missing_temperature_points": len(gaps),
        "missing_temperature_categories": dict(
            Counter(r["temperature_recovery_status"] for r in gaps)
        ),
        "by_property": dict(Counter(r["property"] for r in rows)),
        "interpretation": "Context counts, not independent experiments. Gap labels inspect linked method metadata, not the whole source. Standards do not supply automatic temperatures.",
    }
    for directory in (data, root / "data/processed"):
        atomic_json(directory / "coverage_audit.json", summary)
    return summary
