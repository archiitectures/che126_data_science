"""Parse FSRI HFM result-table excerpts without importing its processing stack."""

import math
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class HFMObservation:
    table_row: int
    temperature_C: float
    value: float


def parse_hfm_results(
    results_si: str, property_name: str
) -> tuple[HFMObservation, ...]:
    """Read all SI result rows, retaining repeated temperature setpoints.

    conductivity values are W/(m K); heatcapacity values are J/(m³ K).
    Results-table excerpts begin immediately after 'Results Table -- SI Units'.
    Headers/units are checked rather than interpreted as data rows.
    """
    if property_name not in {"conductivity", "heatcapacity"}:
        raise ValueError("property_name must be conductivity or heatcapacity")
    expected_header = "Average Cond" if property_name == "conductivity" else "Spc Heat"
    if expected_header not in results_si or "Mean Temp" not in results_si:
        raise ValueError("Missing expected HFM SI result-table header")
    if property_name == "heatcapacity" and "J/(m³K)" not in results_si:
        raise ValueError("Heat capacity must be volumetric SI J/(m³K)")
    observations = []
    width = 4 if property_name == "conductivity" else 3
    for line in results_si.splitlines():
        cells = [c.strip() for c in line.split("\t") if c.strip()]
        if not cells or not re.fullmatch(r"[-+]?\d+(?:\.\d+)?", cells[0]):
            continue
        if len(cells) != width:
            raise ValueError(f"Unexpected HFM row width: {line!r}")
        if (
            not all(math.isfinite(float(c)) for c in cells)
            or float(cells[0]) < -273.15
            or float(cells[-1]) < 0
        ):
            raise ValueError("Nonphysical HFM numeric result")
        observations.append(
            HFMObservation(len(observations) + 1, float(cells[0]), float(cells[-1]))
        )
    if not observations:
        raise ValueError("HFM result table has no numeric observations")
    return tuple(observations)


def hfm_reference_thickness_um(header: list[str]) -> float:
    """Convert the instrument's file-header thickness, not a thermal size curve."""
    for line in header:
        match = re.search(r"Thickness:\s*(\d+(?:\.\d+)?)\s*mm", line)
        if match:
            return round(float(match[1]) * 1000, 6)
    raise ValueError("Missing HFM instrument thickness header in mm")


def polyethylene_reference_rows(snapshot: dict) -> list[dict]:
    """Convert the pinned HDPE/LDPE excerpts into dry-table reference rows.

    Heat capacity normalization follows FSRI's mean-density convention. Header
    geometry is explicitly reference geometry; separator measurements stay blank.
    """
    import csv
    import io
    from statistics import mean

    commit = snapshot["source_commit"]
    exports = snapshot["exports"]
    densities = {}
    for material in ("HDPE", "LDPE"):
        files = [x for x in exports if f"/{material}/HFM/" in x["path"] and "csv" in x]
        if len(files) != 3:
            raise ValueError(f"Expected three density replicates for {material}")
        values = [
            float(
                dict(list(csv.reader(io.StringIO(x["csv"])))[1:])[
                    "Sample Density [kg/m3]"
                ]
            )
            for x in files
        ]
        if any(value <= 0 for value in values):
            raise ValueError("Density must be positive")
        densities[material] = (mean(values), values, [x["path"] for x in files])
    rows = []
    for source in exports:
        if "results_si" not in source:
            continue
        material = source["path"].split("/")[1]
        filename = source["path"].split("/")[-1]
        kind = "conductivity" if "conductivity" in filename else "heatcapacity"
        replicate = filename.removesuffix(".tst").split("_")[-1]
        sample_id = "fsri_" + filename.removesuffix(".tst").lower()
        for observation in parse_hfm_results(source["results_si"], kind):
            row = {
                "record_id": f"{sample_id}_si_{observation.table_row:02d}",
                "sample_id": sample_id,
                "material": f"Polyethylene ({material})",
                "separator_type": "bulk sheet reference; not a battery separator",
                "temperature_C": observation.temperature_C,
                "measurement_direction": "through-plane",
                "source_id": f"fsri_map_{commit}",
                "source_type": "public_materials_database",
                "source_url": f"https://github.com/ulfsri/fsri_materials_database/blob/{commit}/{source['path']}",
                "source_locator": f"{source['path']}; Results Table -- SI Units; data row {observation.table_row}; blob {source['blob_sha']}",
                "value_type": "measured",
                "replicate_id": replicate,
                "sample_form": "bulk_sheet_reference",
                "source_condition": "FSRI Wet: unconditioned ambient-moisture; no battery electrolyte reported",
                "reference_thickness_um": hfm_reference_thickness_um(source["header"]),
                "thermal_method": f"TA Instruments FOX 200 HFM; {kind}; instrument SI results table",
                "notes": "Bulk polyethylene reference, not separator data. Temperature is the unrounded reported mean temperature. File-header thickness is test geometry at unspecified temperature, not temperature-dependent separator thickness. Repeated setpoints are distinct rows, not independent specimen replicates.",
            }
            if kind == "conductivity":
                row["thermal_conductivity_W_m_K"] = observation.value
                row["notes"] += (
                    " Conductivity is the reported Average Cond (W/mK), not a replicate mean."
                )
            else:
                density, density_values, density_paths = densities[material]
                row["volumetric_heat_capacity_J_m3_K"] = observation.value
                row["reference_density_kg_m3"] = density
                row["specific_heat_capacity_J_kg_K"] = round(
                    observation.value / density, 3
                )
                row["value_type"] = "measured_and_calculated"
                row["source_locator"] += "; mean-density inputs: " + ", ".join(
                    density_paths
                )
                row["notes"] += (
                    f" Measured volumetric heat capacity (J/(m3 K)); mass-specific heat capacity is calculated as volumetric value / arithmetic mean density of {density_values} kg/m3, rounded to 0.001 J/(kg K), following FSRI's processing convention. Reference density is not measured at this temperature."
                )
                if material == "LDPE":
                    row["notes"] += (
                        " Source quality: LDPE density CSV column labels incorrectly say HDPE_WET; material identity uses the LDPE directory/filenames, consistent with FSRI processing."
                    )
            rows.append(row)
    return rows


def hfm_observations(snapshot: dict):
    """Normalize every raw HFM result in a pinned snapshot, for any material.

    Snapshot entries use the existing {path, blob_sha, results_si} format.
    No mass-specific heat is derived without independently validated density.
    """
    from che126_data_science.data_science.observations import Observation

    commit = snapshot["source_commit"]
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError("source_commit must be an immutable Git commit")
    rows = []
    for entry in snapshot["exports"]:
        if "results_si" not in entry:
            continue
        path = entry["path"]
        parts = path.split("/")
        if len(parts) != 4 or parts[0] != "01_Data" or parts[2] != "HFM":
            raise ValueError(f"Unexpected HFM source path: {path}")
        material, filename = parts[1], parts[-1]
        if "conductivity" in filename.lower():
            kind, prop, unit = "conductivity", "thermal_conductivity", "W/(m K)"
        elif "heatcapacity" in filename.lower():
            kind, prop, unit = "heatcapacity", "volumetric_heat_capacity", "J/(m3 K)"
        else:
            raise ValueError(f"Unknown HFM measurement type: {filename}")
        for point in parse_hfm_results(entry["results_si"], kind):
            rows.append(
                Observation(
                    record_id=f"{filename}:{point.table_row}",
                    sample_id=filename,
                    material=material,
                    property=prop,
                    value=point.value,
                    unit=unit,
                    source_url=f"https://github.com/ulfsri/fsri_materials_database/blob/{commit}/{path}",
                    source_locator=f"SI results row {point.table_row}; blob {entry['blob_sha']}",
                    sample_form=entry.get("sample_form", "bulk_reference"),
                    temperature_C=point.temperature_C,
                    temperature_role="measurement",
                    direction="through-plane",
                    method=f"HFM {kind}",
                    conditions="FSRI conditioning encoded in source filename; Wet is not electrolyte-soaked",
                    raw_value=str(point.value),
                    raw_unit=unit,
                    notes="Distinct repeated setpoints retained; no battery separator properties inferred.",
                )
            )
    return rows


def extract_public_curves(html: str) -> list[dict]:
    """Read embedded JSON curves from a saved FSRI material-detail page.

    This never evaluates JavaScript. Axes, trace labels and error bars are
    preserved. These are source curves, NOT automatically classified observations:
    time, temperature, heating rate and exposure must be reviewed before import.
    """
    import json

    decoder = json.JSONDecoder()
    curves = []
    for index, match in enumerate(
        re.finditer(r'Plotly\.newPlot\(\s*"[^"]+"\s*,\s*', html), 1
    ):
        try:
            traces, end = decoder.raw_decode(html, match.end())
            layout_start = re.match(r"\s*,\s*", html[end:])
            if layout_start is None:
                raise ValueError("Missing Plotly layout")
            layout, _ = decoder.raw_decode(html, end + layout_start.end())
            curves.append(
                {
                    "figure": index,
                    "traces": traces,
                    "xaxis": layout.get("xaxis", {}),
                    "yaxis": layout.get("yaxis", {}),
                    "annotations": layout.get("annotations", []),
                    "title": layout.get("title", {}),
                }
            )
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError(
                f"Unsupported FSRI figure {index}; review saved source"
            ) from exc
    if not curves:
        raise ValueError("No embedded FSRI JSON figures found; page may have changed")
    return curves
