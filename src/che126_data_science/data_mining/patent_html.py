"""HTML-first patent tables, contextual evidence, and figure discovery."""

import re
from pathlib import Path
from urllib.parse import urljoin

from che126_data_science.data_science.master import make_observation

from .normalization import (
    ALIASES,
    canonical_unit_text,
    conditions,
    direction,
    property_name,
    values,
)


def expand_rows(container) -> list[list[str]]:
    """Expand rowspan/colspan while preserving empty cells and split HTML tables."""
    grid, spans = [], {}
    for tr in container.find_all("tr"):
        if tr.find_parent("tr") is not None:
            continue
        row, column = [], 0
        for cell in tr.find_all(["td", "th"], recursive=False):
            while column in spans:
                value, remaining = spans[column]
                row.append(value)
                if remaining == 1:
                    del spans[column]
                else:
                    spans[column] = (value, remaining - 1)
                column += 1
            text = re.sub(r"\s+", " ", cell.get_text(" ", strip=True))
            width, height = int(cell.get("colspan", 1)), int(cell.get("rowspan", 1))
            for _ in range(width):
                row.append(text)
                if height > 1:
                    spans[column] = (text, height - 1)
                column += 1
        while column in spans:
            value, remaining = spans[column]
            row.append(value)
            if remaining == 1:
                del spans[column]
            else:
                spans[column] = (value, remaining - 1)
            column += 1
        grid.append(row)
    return grid


def _headers(rows, count, first_value=1):
    headers = [""] * count
    for row in rows:
        if len(row) != count + first_value:
            continue
        for i, cell in enumerate(row[first_value:]):
            if re.search(
                r"example|comparative|control|\bex\.?\s*\d", cell, re.IGNORECASE
            ):
                headers[i] = (headers[i] + " " + cell).strip()
    return [re.sub(r"\s+", " ", h) for h in headers]


def _protocol_blocks(paragraphs):
    """Associate numbered property headings with explicit adjacent test methods."""
    protocols = {}
    for i, paragraph in enumerate(paragraphs):
        heading = paragraph.get_text(" ", strip=True)
        if len(heading) > 160 or not re.match(r"^\(?\d+\)[ .]", heading):
            continue
        body = []
        for following in paragraphs[i + 1 : i + 4]:
            text = following.get_text(" ", strip=True)
            if re.match(r"^\(?\d+\)[ .]", text) or len(text) < 10:
                break
            body.append(text)
        text = " ".join([heading, *body])
        if not re.search(
            r"measur|determined|according to|ASTM|JIS", " ".join(body), re.IGNORECASE
        ):
            continue
        for pattern, prop in ALIASES:
            if re.search(pattern, heading, re.IGNORECASE):
                protocols.setdefault(prop, {})[text] = paragraph.get(
                    "id"
                ) or paragraph.get("num")
    return protocols


def _text_rows(text):
    # Only delimiters/column spacing, never split arbitrary prose into numbers.
    return [
        [cell.strip() for cell in re.split(r"\t|\s{2,}|\s*\|\s*", line.strip())]
        for line in text.splitlines()
        if line.strip()
    ]


def extract_patent(document, context: dict) -> tuple[list, list]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(Path(document.path).read_text(encoding="utf-8"), "lxml")
    description = soup.select_one('section[itemprop="description"]') or soup.select_one(
        ".description"
    )
    if description is None:
        pdf = soup.select_one('meta[name="citation_pdf_url"]')
        return [], (
            [{"kind": "pdf_fallback", "url": pdf["content"]}]
            if pdf and pdf.get("content")
            else []
        )
    publication = soup.select_one('meta[name="DC.relation"][scheme="docdb"]')
    number = context.get("publication_number") or (
        publication.get("content") if publication else None
    )
    if not number:
        match = re.search(
            r"(?:US|EP|WO|CN|JP|KR)\d+[A-Z]\d?",
            soup.title.get_text() if soup.title else document.url or "",
        )
        number = match[0] if match else document.sha256[:16]
    paragraphs = description.select(".description-paragraph, .description-line")
    protocols = _protocol_blocks(paragraphs)
    shrink_methods = [
        p
        for p in paragraphs
        if re.search(r"shrink", p.get_text(), re.IGNORECASE)
        and re.search(r"(?:minutes?|hours?)", p.get_text(), re.IGNORECASE)
        and re.search(r"measur|lines|length|area", p.get_text(), re.IGNORECASE)
    ]
    # Link only a unique, explicit test protocol; conflicting conditions go to review.
    method_context = (
        shrink_methods[-1].get_text(" ", strip=True) if len(shrink_methods) == 1 else ""
    )
    method_locator = shrink_methods[-1].get("id") if len(shrink_methods) == 1 else None
    base_meta = conditions(method_context)
    base_meta.pop("temperature_C", None)
    base_meta.pop("temperature_role", None)
    base_meta.pop("quality_flag", None)
    containers = description.select("patent-tables")
    if not containers:
        containers = [
            t for t in description.select("table") if not t.find_parent("table")
        ]
    artifacts, records = [], []
    for index, container in enumerate([*containers, *description.select("pre")], 1):
        rows = (
            expand_rows(container)
            if container.name != "pre"
            else _text_rows(container.get_text())
        )
        caption = next(
            (
                " ".join(row)
                for row in rows[:5]
                if re.search(r"\bTABLE\s+\d", " ".join(row), re.IGNORECASE)
            ),
            f"table_{index}",
        )
        caption_match = re.search(r"TABLE\s+\d+", caption, re.IGNORECASE)
        table_name = caption_match[0] if caption_match else f"table_{index}"
        artifacts.append(
            {
                "kind": "table",
                "table": table_name,
                "cells": rows,
                "html": str(container),
                "context": method_context,
                "context_locator": method_locator,
                "method": "patent_html",
            }
        )
        # Transpose only explicit example-per-row tables; preserve original coordinates.
        transposed = (
            len(rows) > 1
            and len({len(r) for r in rows}) == 1
            and any(property_name(c) for c in rows[0][1:])
            and all(
                re.search(r"example|comparative|control", r[0], re.IGNORECASE)
                for r in rows[1:]
            )
        )
        working_rows = [list(r) for r in zip(*rows)] if transposed else rows
        for row_index, row in enumerate(working_rows):
            # Example columns establish the boundary even when values are bounded,
            # ranges, blanks or unparseable. Never use the first scalar as a boundary.
            if len(row) < 2:
                continue
            first_value = 1
            for header in working_rows[:row_index]:
                example_columns = [
                    i
                    for i, c in enumerate(header)
                    if re.search(r"example|comparative|control", c, re.IGNORECASE)
                ]
                if example_columns and example_columns == list(
                    range(example_columns[0], len(row))
                ):
                    first_value = example_columns[0]
            label = row[0].strip()
            following = []
            for next_row in working_rows[row_index + 1 : row_index + 7]:
                if len(next_row) != 1:
                    break
                following.extend(next_row)
            label = " ".join([label, *following]).strip()
            prop = property_name(label)
            if not prop:
                continue
            value_cells = row[first_value:]
            headers = _headers(working_rows[:row_index], len(value_cells), first_value)
            unit_match = re.search(r"\(([^)]+)\)", label)
            raw_unit = (
                row[1]
                if first_value == 2
                else unit_match[1]
                if unit_match
                else "%"
                if "percentage" in label.lower()
                else context.get("units", {}).get(prop, "")
            )
            if not raw_unit:
                terminal = re.search(
                    r"(%|[μµu]m|nm|mm|MPa|kPa|mN|gf|N|kgf/cm\s*2)\s*$", label
                )
                if terminal:
                    raw_unit = terminal[1]
            # The temperature is part of the label, not the property unit.
            temp_meta = conditions(label) if prop == "thermal_shrinkage" else {}
            if prop == "thermal_shrinkage" and "%" in label:
                raw_unit = "%"
            unit = canonical_unit_text(raw_unit)
            property_context = method_context if prop == "thermal_shrinkage" else ""
            property_locator = method_locator if prop == "thermal_shrinkage" else None
            if prop != "thermal_shrinkage":
                methods = [
                    p
                    for p in paragraphs
                    if property_name(p.get_text(" ", strip=True)) == prop
                    and re.search(
                        r"measur|determin|test|micrometer", p.get_text(), re.IGNORECASE
                    )
                ]
                if len(methods) == 1:
                    property_context = methods[0].get_text(" ", strip=True)
                    property_locator = methods[0].get("id")
            linked = protocols.get(prop, {})
            if len(linked) == 1:
                property_context, property_locator = next(iter(linked.items()))
            elif len(linked) > 1:
                property_context, property_locator = "", None
            for column, cell in enumerate(value_cells, 1):
                sample = headers[column - 1]
                for value, statistic in values(cell, label):
                    meta = (
                        (
                            {**base_meta, **temp_meta}
                            if temp_meta
                            else conditions(property_context)
                        )
                        if prop == "thermal_shrinkage"
                        else {}
                    )
                    pending = meta.pop("quality_flag", None)
                    if not sample:
                        pending = "unresolved_example_header"
                    elif not property_context:
                        pending = "unresolved_test_protocol"
                    records.append(
                        make_observation(
                            document,
                            label=label,
                            prop=prop,
                            raw_value=value,
                            raw_unit=raw_unit,
                            normalization_unit=unit,
                            sample_id=f"{number}:{sample or 'column_' + str(column)}",
                            source_table=table_name,
                            source_row=str(
                                first_value + column if transposed else row_index + 1
                            ),
                            source_column=str(
                                row_index + 1 if transposed else first_value + column
                            ),
                            polymer=context.get("polymer"),
                            sample_form="separator",
                            separator_architecture=context.get(
                                "separator_architecture"
                            ),
                            statistic=statistic,
                            record_type="spec_limit"
                            if statistic in {"minimum", "maximum"}
                            else "measured",
                            quality_flag=pending,
                            direction=direction(label),
                            shrinkage_basis="length"
                            if "length" in method_context.lower()
                            else "area"
                            if "area" in method_context.lower()
                            else None,
                            measurement_context=property_context or label,
                            method=f"Patent experimental protocol {property_locator}"
                            if property_locator
                            else None,
                            family_id=context.get("family_id"),
                            extraction_method="patent_html_table"
                            if container.name != "pre"
                            else "patent_text_table",
                            notes=f"Publication {number}; {sample}; printed unit: {raw_unit}. "
                            "Example identity and experimental protocol retained; no processing temperature inferred.",
                            **meta,
                        )
                    )
    for image in soup.select('li[itemprop="images"]'):
        full = image.select_one('meta[itemprop="full"]')
        if full:
            artifacts.append(
                {
                    "kind": "figure",
                    "url": urljoin(
                        document.url or "https://patents.google.com", full["content"]
                    ),
                    "caption": " ".join(
                        p.get_text(" ", strip=True)
                        for p in paragraphs
                        if re.search(
                            r"FIG(?:URE)?\.?\s*\d+.*(?:is |shows |showing )",
                            p.get_text(),
                            re.IGNORECASE,
                        )
                    ),
                    "sheet": str(
                        len([a for a in artifacts if a["kind"] == "figure"]) + 1
                    ),
                }
            )
    pdf = soup.select_one('meta[name="citation_pdf_url"]')
    if pdf and pdf.get("content"):
        artifacts.append({"kind": "pdf_fallback", "url": pdf["content"]})
    return records, artifacts
