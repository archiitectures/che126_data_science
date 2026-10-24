"""Tidy measurements with explicit conditions, validation and conservative coverage."""

import csv
import math
from collections import defaultdict
from dataclasses import MISSING, asdict, dataclass, fields
from pathlib import Path
from urllib.parse import urlparse

# Canonical units; aliases are intentionally explicit, not guessed from labels.
UNITS = {
    "thickness": "um",
    "pore_size": "um",
    "porosity": "%",
    "tensile_strength": "MPa",
    "elongation": "%",
    "puncture_force": "N",
    "thermal_shrinkage": "%",
    "thermal_conductivity": "W/(m K)",
    "specific_heat_capacity": "J/(kg K)",
    "volumetric_heat_capacity": "J/(m3 K)",
    "density": "kg/m3",
    "melting_temperature": "C",
    "shutdown_temperature": "C",
    "meltdown_temperature": "C",
    "ionic_conductivity": "S/m",
    "electrolyte_uptake": "%",
    "gurley_time": "s",
    "air_permeability_time": "s",
    "basis_weight": "g/m2",
    "shutdown_response_time": "s",
    "tortuosity": "1",
    "electrical_resistance": "ohm",
    "contact_angle": "deg",
}
CONVERSIONS = {
    ("mm", "um"): (1000, 0),
    ("nm", "um"): (0.001, 0),
    ("Pa", "MPa"): (1e-6, 0),
    ("kPa", "MPa"): (0.001, 0),
    ("gf", "N"): (0.00980665, 0),
    ("kgf", "N"): (9.80665, 0),
    ("mN", "N"): (0.001, 0),
    ("kgf/cm2", "MPa"): (0.0980665, 0),
    ("g/cm3", "kg/m3"): (1000, 0),
    ("kJ/(kg K)", "J/(kg K)"): (1000, 0),
    ("mS/cm", "S/m"): (0.1, 0),
    ("K", "C"): (1, -273.15),
}


@dataclass(frozen=True)
class Observation:
    record_id: str
    sample_id: str
    material: str
    property: str
    value: float
    unit: str
    source_url: str
    source_locator: str
    sample_form: str
    state: str = "unknown"
    temperature_C: float | None = None
    temperature_role: str = "unknown"
    direction: str = "unspecified"
    method: str = "unspecified"
    conditions: str = "unspecified"
    value_type: str = "measured"
    replicate_id: str = ""
    raw_value: str = ""
    raw_unit: str = ""
    notes: str = ""

    def __post_init__(self):
        for name in (
            "record_id",
            "sample_id",
            "material",
            "source_locator",
            "sample_form",
            "direction",
            "method",
            "conditions",
        ):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must be nonblank")
        if (
            urlparse(self.source_url).scheme not in {"https", "http"}
            or not urlparse(self.source_url).netloc
        ):
            raise ValueError("source_url must be an HTTP(S) source citation")
        if self.property not in UNITS or self.unit != UNITS[self.property]:
            raise ValueError(
                f"Unknown property or noncanonical unit: {self.property}/{self.unit}"
            )
        if not math.isfinite(self.value):
            raise ValueError("value must be finite")
        if self.property == "porosity" and not 0 <= self.value <= 100:
            raise ValueError("porosity must be in [0, 100]")
        if self.property == "contact_angle" and not 0 <= self.value <= 180:
            raise ValueError("contact angle must be in [0, 180]")
        if (
            self.property
            not in {
                "thermal_shrinkage",
                "melting_temperature",
                "shutdown_temperature",
                "meltdown_temperature",
            }
            and self.value < 0
        ):
            raise ValueError("Negative physical magnitude")
        if self.unit == "C" and self.value < -273.15:
            raise ValueError("Property temperature below absolute zero")
        if self.state not in {"dry", "electrolyte_wet", "unknown"}:
            raise ValueError("state must be dry, electrolyte_wet or unknown")
        if self.temperature_role not in {"measurement", "exposure", "unknown"}:
            raise ValueError("Processing temperatures are not measurement conditions")
        if self.temperature_C is None:
            if self.temperature_role != "unknown":
                raise ValueError("Temperature role requires a temperature")
        elif (
            not math.isfinite(self.temperature_C)
            or self.temperature_C < -273.15
            or self.temperature_role == "unknown"
        ):
            raise ValueError("Known temperature requires a valid value and role")
        if self.value_type not in {
            "measured",
            "typical",
            "calculated",
            "minimum",
            "maximum",
            "claim",
        }:
            raise ValueError("Unknown value_type")


def read_observations(path: str | Path) -> list[Observation]:
    """Strict CSV import, safe unit conversion and exact-ID deduplication.

    Replicates with different IDs survive. Conflicting IDs fail rather than
    silently selecting a value. Missing temperature remains unknown.
    """
    result = {}
    names = {field.name for field in fields(Observation)}
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(
            reader.fieldnames
        ):
            raise ValueError("Missing or duplicate CSV headers")
        required = {f.name for f in fields(Observation) if f.default is MISSING}
        missing = required - set(reader.fieldnames)
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")
        extra = set(reader.fieldnames) - names
        if extra:
            raise ValueError(f"Unknown columns: {sorted(extra)}")
        for number, row in enumerate(reader, 2):
            try:
                if None in row or any(v is None for v in row.values()):
                    raise ValueError("Row width differs from header")
                row = {k: v.strip() for k, v in row.items()}
                raw_value, raw_unit = row["value"], row["unit"]
                value = float(raw_value)
                canonical = UNITS[row["property"]]
                if raw_unit != canonical:
                    factor, offset = CONVERSIONS[(raw_unit, canonical)]
                    value = value * factor + offset
                row.update(
                    value=value,
                    unit=canonical,
                    raw_value=row.get("raw_value") or raw_value,
                    raw_unit=row.get("raw_unit") or raw_unit,
                    temperature_C=float(row["temperature_C"])
                    if row.get("temperature_C")
                    else None,
                )
                # Blank optional columns mean the documented defaults.
                for field in fields(Observation):
                    if (
                        row.get(field.name) == ""
                        and isinstance(field.default, str)
                        and field.default
                    ):
                        row.pop(field.name)
                observation = Observation(**row)
                existing = result.get(observation.record_id)
                if existing is not None and existing != observation:
                    raise ValueError(f"Conflicting record_id: {observation.record_id}")
                result[observation.record_id] = observation
            except (TypeError, ValueError, KeyError) as exc:
                raise ValueError(f"{path}: row {number}: {exc}") from exc
    return list(result.values())


def write_observations(observations: list[Observation], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=[f.name for f in fields(Observation)]
        )
        writer.writeheader()
        writer.writerows(asdict(row) for row in observations)


def coverage(
    observations: list[Observation],
    properties: list[str],
    temperatures: list[float],
    *,
    tolerance: float = 0,
) -> dict:
    """Report a requested grid per sample/source/condition; never interpolate.

    Bounds, claims and calculated values do not fill measured coverage. Exposure
    and measurement grids remain separate. Temperature tolerance is explicit.
    """
    if not properties or any(p not in UNITS for p in properties):
        raise ValueError("Request known properties")
    if not temperatures or any(
        not math.isfinite(t) or t < -273.15 for t in temperatures
    ):
        raise ValueError("Request finite physical temperatures")
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("tolerance must be finite and nonnegative")
    keys = (
        "material",
        "sample_id",
        "source_url",
        "sample_form",
        "state",
        "temperature_role",
        "direction",
        "conditions",
    )
    groups = defaultdict(list)
    for row in observations:
        groups[tuple(getattr(row, key) for key in keys)].append(row)
    output = []
    for key, rows in sorted(groups.items()):
        cells = []
        for temperature in dict.fromkeys(temperatures):
            for prop in dict.fromkeys(properties):
                matches = [
                    r
                    for r in rows
                    if r.property == prop
                    and r.temperature_C is not None
                    and abs(r.temperature_C - temperature) <= tolerance
                    and r.value_type in {"measured", "typical"}
                ]
                cells.append(
                    {
                        "temperature_C": temperature,
                        "property": prop,
                        "record_ids": [r.record_id for r in matches],
                        "reported_temperatures_C": sorted(
                            {r.temperature_C for r in matches}
                        ),
                        "methods": sorted({r.method for r in matches}),
                        "status": "reported" if matches else "missing",
                    }
                )
        output.append({**dict(zip(keys, key)), "cells": cells})
    return {
        "tolerance_C": tolerance,
        "observation_count": len(observations),
        "unknown_temperature_count": sum(r.temperature_C is None for r in observations),
        "groups": output,
        "note": "Coverage of requested properties only; no claim of complete characterization. No interpolation.",
    }
