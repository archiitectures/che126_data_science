"""Geometry-first PDF table artifacts and conservative Celgard normalization."""

import re
import sys
from contextlib import redirect_stdout
from pathlib import Path

from che126_data_science.data_science.master import make_observation

from .normalization import (
    canonical_unit_text,
    conditions,
    direction,
    property_name,
    values,
)


def extract_tables(path: str | Path) -> list[dict]:
    import pymupdf

    artifacts = []
    with pymupdf.open(path) as pdf:
        for page in pdf:
            text = page.get_text()
            with redirect_stdout(sys.stderr):
                tables = page.find_tables().tables
            for i, table in enumerate(tables, 1):
                artifacts.append(
                    {
                        "kind": "table",
                        "page": page.number + 1,
                        "table": str(i),
                        "bbox": list(table.bbox),
                        "cells": table.extract(),
                        "context": text,
                        "method": "pymupdf.find_tables",
                    }
                )
    if not artifacts:
        try:
            import pdfplumber
        except ImportError:
            return []
        with pdfplumber.open(path) as pdf:
            for page_number, page in enumerate(pdf.pages, 1):
                for i, table in enumerate(page.find_tables(), 1):
                    artifacts.append(
                        {
                            "kind": "table",
                            "page": page_number,
                            "table": str(i),
                            "bbox": list(table.bbox),
                            "cells": table.extract(),
                            "context": page.extract_text() or "",
                            "method": "pdfplumber",
                        }
                    )
    return artifacts


def extract_celgard(document, context: dict) -> tuple[list, list]:
    artifacts = extract_tables(document.path)
    records = []
    for artifact in artifacts:
        text = artifact["context"]
        products = list(
            dict.fromkeys(
                re.findall(r"Celgard[®\s]*([A-Z]*\d+[A-Z0-9]*)", text, re.IGNORECASE)
            )
        )
        product = context.get("product") or (
            products[0] if len(products) == 1 else None
        )
        polymer = context.get("polymer") or (
            "PP/PE/PP"
            if re.search(r"PP\s*/\s*PE\s*/\s*PP", text)
            else "PP"
            if re.search(r"\(PP\)|Polypropylene", text, re.IGNORECASE)
            else None
        )
        laminated = bool(re.search(r"laminated\s+to", text, re.IGNORECASE))
        coated = bool(
            re.search(r"ceramic\s+coated|ceramic coating", text, re.IGNORECASE)
        )
        cells = artifact["cells"]
        for row_number, raw in enumerate(cells, 1):
            cells_row = [re.sub(r"\s+", " ", c or "").strip() for c in raw]
            if len(cells_row) != 3:
                continue
            # Some datasheets put value before unit and label.
            if property_name(cells_row[0]):
                label, original_unit, cell = cells_row
                value_column = "3"
            elif property_name(cells_row[2]):
                cell, original_unit, label = cells_row
                value_column = "1"
            else:
                continue
            prop = property_name(label)
            if not cell or "typical value" in cell.lower():
                continue
            unit = canonical_unit_text(original_unit)
            component = laminated and not label.lower().startswith("total film")
            sample = f"celgard_{product or 'unresolved'}" + (
                "_microporous_component" if component else ""
            )
            flag = (
                "ambiguous_product_identity"
                if not product
                else "unknown_polymer"
                if not polymer
                else None
            )
            for value, statistic in values(cell, label, default="typical"):
                meta = conditions(label) if prop == "thermal_shrinkage" else {}
                flag_for_row = meta.pop("quality_flag", None) or flag
                record_type = (
                    "calculated"
                    if "calculated" in label.lower()
                    else "spec_limit"
                    if statistic in {"minimum", "maximum"}
                    else "unknown"
                )
                records.append(
                    make_observation(
                        document,
                        label=label,
                        prop=prop,
                        raw_value=value,
                        raw_unit=original_unit,
                        normalization_unit=unit,
                        sample_id=sample,
                        source_page=artifact["page"],
                        source_table=artifact["table"],
                        source_row=str(row_number),
                        source_column=value_column,
                        manufacturer="Celgard",
                        product=product,
                        polymer=polymer,
                        separator_architecture="microporous film component"
                        if component
                        else "laminate"
                        if laminated
                        else "trilayer"
                        if polymer == "PP/PE/PP"
                        else "monolayer",
                        coating="ceramic"
                        if coated
                        else "surfactant"
                        if "surfactant" in text.lower()
                        else None,
                        sample_form="separator_component" if component else "separator",
                        material_class="polyolefin separator",
                        direction=direction(label),
                        statistic=statistic,
                        record_type=record_type,
                        quality_flag=flag_for_row,
                        shrinkage_basis="length"
                        if prop == "thermal_shrinkage"
                        and direction(label) != "unspecified"
                        else None,
                        method="Gurley JIS (number unspecified)"
                        if "JIS" in label
                        else "Gurley ASTM (number unspecified)"
                        if "ASTM" in label
                        else None,
                        measurement_context=label,
                        extraction_method=artifact["method"],
                        notes=f"Manufacturer table; source unit as printed: {original_unit}. "
                        "Typical specifications do not establish an experimental measurement temperature. "
                        + (
                            "Values describe the microporous component, not the total laminate. "
                            if component
                            else ""
                        ),
                        **meta,
                    )
                )
    if not records:
        # Retain the existing narrow extractor as a fallback, without guessing units.
        from .celgard import parse_datasheet, pdf_text

        product = context.get("product")
        if product:
            result = parse_datasheet(
                pdf_text(document.path),
                product=product,
                material=context.get("polymer", "not_reported"),
                source_url=document.url or "https://www.celgard.com",
            )
            for row in result["observations"]:
                records.append(
                    make_observation(
                        document,
                        label=row.property,
                        prop=row.property,
                        raw_value=row.raw_value,
                        raw_unit=row.raw_unit,
                        sample_id=row.sample_id,
                        source_row=row.source_locator,
                        manufacturer="Celgard",
                        product=product,
                        polymer=context.get("polymer"),
                        sample_form=row.sample_form,
                        statistic=row.value_type
                        if row.value_type in {"typical", "minimum", "maximum"}
                        else "reported",
                        record_type="calculated"
                        if row.value_type == "calculated"
                        else "unknown",
                        temperature_C=row.temperature_C,
                        temperature_role=row.temperature_role,
                        direction=row.direction,
                        extraction_method="legacy_celgard_text",
                    )
                )
            artifacts.append({"kind": "unresolved", "items": result["unresolved"]})
    return records, artifacts
