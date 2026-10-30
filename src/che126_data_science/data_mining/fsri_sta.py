"""FSRI source-exported STA channels, selected without interpolating curves."""

import csv
import hashlib
import io
import math
import re
from pathlib import Path

from che126_data_science.data_science.master import make_observation

CHANNELS = {
    "DSC(subtr.2)/mW": ("heat_flow", "mW"),
    "DSC(subtr.2)/(mW/mg)": ("mass_specific_heat_flow", "mW/mg"),
    "Mass loss(subtr.2)/mg": ("sta_mass_change", "mg"),
    "Mass(subtr.2)/%": ("sta_mass_percent", "%"),
}


def extract_sta(document, context):
    """Require matching immutable metadata; retain real temperatures and row IDs.

    The source exports may themselves be processed. They are not untouched sensor
    streams. No additional interpolation, smoothing or mass normalization is done.
    """
    name = context["filename"]
    match = re.fullmatch(
        r"(HDPE|LDPE|PP|PET)_STA_N2_(3|10|30)KData_\d+_(R\d+)\.csv", name
    )
    if not match:
        raise ValueError("Unsupported STA data filename")
    material, rate, replicate = match.groups()
    meta = context["sta_metadata"]
    if Path(meta["filename"]).name != name.replace("Data_", "Meta_"):
        raise ValueError("STA data/metadata filenames differ")
    rawmeta = Path(meta["path"]).read_bytes()
    if hashlib.sha256(rawmeta).hexdigest() != meta["sha256"]:
        raise ValueError("STA metadata hash mismatch")
    cells = list(csv.reader(io.StringIO(rawmeta.decode("utf-8-sig"))))
    metadata = {r[0].strip().rstrip(":"): r[1].strip() for r in cells if len(r) >= 2}
    if metadata.get("#MATERIAL") != material:
        raise ValueError("STA metadata material mismatch")
    sample = metadata.get("#SAMPLE", "")
    if material == "PP":
        sample = re.sub(r"^Polypropylene_", "PP_", sample)
    sample_match = re.fullmatch(rf"{material}_{rate}K(?:_(R?\d+))?", sample)
    if not sample_match or (
        sample_match[1] and sample_match[1].lstrip("R") != replicate[1:]
    ):
        raise ValueError("STA metadata sample/rate/replicate mismatch")
    if not re.fullmatch(
        rf"{material}_STA_N2_{rate}K_\d+_{replicate}\.ngb-ss3",
        metadata.get("#FILE", ""),
    ):
        raise ValueError("STA original instrument filename mismatch")
    mass = float(metadata["#SAMPLE MASS /mg"])
    if not math.isfinite(mass) or mass <= 0:
        raise ValueError("Invalid STA specimen mass")
    # File paths pin atmosphere; instrument purge channel settings are preserved,
    # not interpreted as a gas composition or proof of zero oxygen.
    if f"/{material}/STA/N2/{rate}K_min/{name}" not in (document.url or ""):
        raise ValueError("STA source path/material/atmosphere/rate mismatch")
    reader = csv.DictReader(
        io.StringIO(Path(document.path).read_text(encoding="utf-8-sig"))
    )
    headers = reader.fieldnames or []
    channels = [c for c in headers if c in CHANNELS]
    if len(headers) != len(set(headers)) or headers[:2] != ["##Temp./°C", "Time/min"]:
        raise ValueError("Unexpected STA header")
    if len(channels) != 2 or sum(c.startswith("DSC(") for c in channels) != 1:
        raise ValueError("Require heat flow and one understood mass channel")
    native = []
    for number, row in enumerate(reader, 2):
        if None in row or any(v is None for v in row.values()):
            raise ValueError("Malformed STA source row")
        values = [float(row[c]) for c in ["##Temp./°C", *channels]]
        if not all(math.isfinite(v) for v in values) or values[0] < -273.15:
            raise ValueError("Nonphysical/nonfinite STA row")
        if native and values[0] <= native[-1][1]:
            raise ValueError("STA temperatures must increase strictly")
        native.append((number, values[0], row))
    if not native:
        raise ValueError("Empty STA curve")
    # Fixed bounded comparison domain: changing this requires a new import context.
    selected = {}
    for target in range(50, 301, 5):
        point = min(native, key=lambda p: abs(p[1] - target))
        if abs(point[1] - target) <= 0.25:
            selected[point[0]] = point
    curve = "fsri:STA:" + name.removesuffix(".csv")
    rows = []
    for number, temp, raw in selected.values():
        for column in channels:
            prop, unit = CHANNELS[column]
            rows.append(
                make_observation(
                    document,
                    label=column,
                    prop=prop,
                    raw_value=raw[column],
                    raw_unit=unit,
                    sample_id=name.removesuffix(".csv"),
                    source_row=f"{name}:CSV row {number}",
                    source_column=column,
                    polymer=material,
                    sample_form="bulk_reference",
                    material_class="bulk polymer reference",
                    temperature_C=temp,
                    temperature_role="measurement",
                    heating_rate_C_min=float(rate),
                    replicate_id=replicate,
                    curve_id=curve,
                    record_type="measured",
                    method="NETZSCH STA 449F3; source-exported baseline-subtracted STA signal",
                    measurement_context="N2 source directory; dynamic heating; source signal sign retained",
                    extraction_method="fsri_sta_native_csv",
                    evidence_group=f"{curve}:row:{number}:{prop}",
                    notes=f"Bulk polymer, not separator performance. Correlated samples of one curve, not independent experiments. Native source-exported row selected within 0.25 C of 5 C grid, 50–300 C; no further interpolation. Mass signals retain baseline offsets, not normalized mass loss. DSC is heat flow, not heat capacity. Metadata SHA256 {meta['sha256']}; initial mass {mass} mg; EXO {metadata.get('#EXO')}; metadata URL {meta['url']}.",
                )
            )
    return rows, [
        {
            "kind": "fsri_sta_native_curve",
            "curve_id": curve,
            "native_rows": len(native),
            "selected_rows": len(selected),
            "metadata": metadata,
            "metadata_document": meta,
            "temperature_range_C": [native[0][1], native[-1][1]],
            "source_channels": channels,
        }
    ]
