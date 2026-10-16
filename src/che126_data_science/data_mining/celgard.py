"""Conservative extraction of current Celgard 'Basic Film Properties' tables."""

import re
from pathlib import Path

from che126_data_science.data_science.observations import Observation


def pdf_text(path: str | Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ImportError("Install PDF extraction: uv sync --extra pdf") from exc
    return "\f".join(page.extract_text() or "" for page in PdfReader(path).pages)


def parse_datasheet(text: str, *, product: str, material: str, source_url: str) -> dict:
    """Return observations plus unresolved rows; no OCR or implicit unit assumptions.

    Caller supplies identity from the discovery card. Only the known table layout
    is supported. Unknown rows remain visible for review, including Kg/cm2.
    """
    marker = "Basic Film Properties Unit of Measure Typical Value"
    pages = [(i, page) for i, page in enumerate(text.split("\f"), 1) if marker in page]
    if len(pages) != 1:
        raise ValueError("Unsupported Celgard table layout; review raw PDF")
    page_number, text = pages[0]
    if not product.strip() or not re.search(
        r"Celgard[®\s]*" + re.escape(product) + r"(?![a-zA-Z0-9])", text, re.IGNORECASE
    ):
        raise ValueError("Product identity does not match the PDF text")
    header_line = text[: text.index(marker)].count("\n") + 1
    rows, unresolved = [], []
    patterns = [
        (r"Thickness [μµ]m ([\d.]+)", "thickness", "um", 1, "typical"),
        (r"Gurley \(JIS\) Seconds ([\d.]+)", "gurley_time", "s", 1, "typical"),
        (r"Porosity \(Calculated\) % ([\d.]+)", "porosity", "%", 1, "calculated"),
        (
            r"Puncture Strength \(typical / min\) Grams Force \(gf\) ([\d.]+) / ([\d.]+)",
            "puncture_force",
            "N",
            0.00980665,
            "typical",
        ),
    ]
    for line_number, line in enumerate(text.splitlines(), 1):
        if line_number <= header_line or not line.strip():
            continue
        line = line.strip()
        direction, temperature, role, conditions = (
            "unspecified",
            None,
            "unknown",
            "unspecified",
        )
        match = re.fullmatch(
            r"(MD|TD) Shrinkage @ ([\d.]+)°C / ([\d.]+) Hour \(typical(?: / max)?\) % ([\d.]+)(?: / ([\d.]+))?",
            line,
        )
        if match:
            direction, temp, hours, typical, maximum = match.groups()
            temperature, role = float(temp), "exposure"
            conditions = (
                f"heat exposure {hours} hour; measurement temperature unspecified"
            )
            prop, unit, factor, kind = "thermal_shrinkage", "%", 1, "typical"
            values = [typical] + ([maximum] if maximum else [])
            bound = "maximum"
        else:
            for pattern, prop, unit, factor, kind in patterns:
                match = re.fullmatch(pattern, line)
                if match:
                    values = list(match.groups())
                    bound = "minimum"
                    break
            else:
                unresolved.append(
                    {
                        "line": line_number,
                        "text": line,
                        "reason": "Unsupported row or ambiguous unit; manual review required",
                    }
                )
                continue
        for index, value in enumerate(values):
            rows.append(
                Observation(
                    record_id=f"celgard_{product}_{line_number}_{index}",
                    sample_id=f"celgard_{product}",
                    material=material,
                    property=prop,
                    value=float(value) * factor,
                    unit=unit,
                    source_url=source_url,
                    source_locator=f"PDF page {page_number}; text line {line_number}: {line}",
                    sample_form="separator",
                    temperature_C=temperature,
                    temperature_role=role,
                    direction=direction,
                    conditions=conditions,
                    method="JIS (number unspecified)"
                    if prop == "gurley_time"
                    else "unspecified",
                    value_type=kind if index == 0 else bound,
                    raw_value=value,
                    raw_unit="gf" if prop == "puncture_force" else unit,
                    notes="Manufacturer typical/specification data; no temperature inferred from ambient conditions.",
                )
            )
    if not rows:
        raise ValueError("No supported property rows; review raw PDF")
    return {"observations": rows, "unresolved": unresolved}
