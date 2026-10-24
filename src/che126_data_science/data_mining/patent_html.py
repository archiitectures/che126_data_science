"""HTML-first patent tables, contextual evidence, and figure discovery."""

import re
from pathlib import Path
from urllib.parse import urljoin

from che126_data_science.data_science.master import make_observation

from .material_identity import Identity, PatentIdentities
from .normalization import (
    ALIASES,
    NUMBER,
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
    for row_index, row in enumerate(rows):
        if any(re.fullmatch(r"TABLE\s+\d+", c, re.IGNORECASE) for c in row):
            headers = [""] * count
            continue
        header_start = len(row) - count
        if header_start != first_value and not (first_value == 2 and header_start == 1):
            continue
        if re.search(
            r"substrate|raw material|starting|used",
            " ".join(row[:header_start]),
            re.IGNORECASE,
        ):
            continue
        for i, cell in enumerate(row[header_start:]):
            if re.search(r"example\s*\d|control|\bex\.?\s*\d", cell, re.IGNORECASE):
                prefix = ""
                if row_index and len(rows[row_index - 1]) == len(row):
                    above = rows[row_index - 1][i + header_start]
                    if re.fullmatch(
                        r"comp(?:arative)?\.?", above, re.IGNORECASE
                    ) and not re.search(r"comparative|comp\.", cell, re.IGNORECASE):
                        prefix = "Comparative "
                headers[i] = (prefix + cell).strip()
    return [re.sub(r"\s+", " ", h) for h in headers]


def _split_example_header(rows, width):
    """A single explicit Example group plus an aligned number row only."""
    for index in range(len(rows) - 1, -1, -1):
        row = rows[index]
        if len(row) != width:
            continue
        for first in range(1, min(width, 6)):
            if first >= width or not all(re.fullmatch(r"\d+", c) for c in row[first:]):
                continue
            if not all(
                not c or re.fullmatch(r"item|unit|property|no\.?", c, re.IGNORECASE)
                for c in row[:first]
            ):
                continue
            group_cells = [c for r in rows[max(0, index - 3) : index] for c in r if c]
            if any(
                re.search(r"comparative|control", c, re.IGNORECASE) for c in group_cells
            ):
                continue
            if any(
                re.fullmatch(r"examples?(?:\s+no\.?)?", c, re.IGNORECASE)
                for c in group_cells
            ):
                return (
                    first,
                    ["Example " + c for c in row[first:]],
                    first == 2 and row[1].lower() == "unit",
                )
    return None


def _table_polymers(rows, count, first_value):
    """Resolve only explicit PE/PP recipe tables whose components total 100%."""
    names = {
        "PE": "PE",
        "PP": "PP",
        "PP/PE/PP": "PP/PE/PP",
        "PE/PP": "PE/PP",
        "POLYETHYLENE": "PE",
        "POLYPROPYLENE": "PP",
    }
    for i, row in enumerate(rows):
        if len(row) != count + first_value or not re.fullmatch(
            r"description|polymer|material", row[0].strip(), re.IGNORECASE
        ):
            continue
        explicit = {
            col: (names[cell.strip().upper()], f"Explicit material row {i + 1}")
            for col, cell in enumerate(row[first_value:])
            if cell.strip().upper() in names
        }
        if explicit:
            return explicit
    starts = [
        i
        for i, row in enumerate(rows)
        if re.fullmatch(
            r"(?:Polyolefin|Polyethylene|PE) (?:Composition|\(PO\))",
            " ".join(row).strip(),
            re.IGNORECASE,
        )
    ]
    start = starts[-1] if starts else None
    if start is None:
        return {}
    components = []
    current = None
    for i, row in enumerate(rows[start + 1 :], start + 1):
        label = row[0].strip() if row else ""
        if re.search(
            r"production conditions|membrane.forming|properties of|melt blend",
            label,
            re.IGNORECASE,
        ):
            break
        if re.fullmatch(r"UHMWPE|HDPE|LDPE|LLDPE|PE|PP", label, re.IGNORECASE):
            current = "PP" if label.upper() == "PP" else "PE"
        elif re.match(
            r"(?:Content\s*\((?:wt\.\s*%|% by mass)\)|% by mass)", label, re.IGNORECASE
        ):
            if current is None or len(row) != count + first_value:
                return {}
            components.append((current, row[first_value:], i + 1))
            current = None
    if not components:
        return {}
    result = {}
    for col in range(count):
        parts = []
        for polymer, cells, locator in components:
            cell = cells[col]
            if cell in {"—", "-", "", "0"}:
                amount = 0.0
            elif re.fullmatch(r"\d+(?:\.\d+)?", cell):
                amount = float(cell)
            else:
                break
            parts.append((polymer, amount, locator))
        else:
            if abs(sum(p[1] for p in parts) - 100) < 0.01:
                polymers = {p[0] for p in parts if p[1] > 0}
                result[col] = (
                    "PE/PP" if polymers == {"PE", "PP"} else next(iter(polymers)),
                    "Composition rows " + ", ".join(str(p[2]) for p in parts),
                )
    return result


def _verified_sample_context(soup, context):
    """Optional reviewed annotations must match exact immutable source evidence."""
    verified = {}
    allowed = {"polymer", "separator_architecture", "coating", "material_grade"}
    for selector, annotation in context.get("sample_annotations", {}).items():
        metadata = annotation.get("metadata", {})
        if not metadata or set(metadata) - allowed or not annotation.get("evidence"):
            raise ValueError("Invalid sample annotation metadata/evidence")
        citations = []
        for evidence in annotation["evidence"]:
            locator = evidence["locator"]
            if locator.startswith("num:"):
                matches = soup.find_all(attrs={"num": locator[4:]})
                element = matches[0] if len(matches) == 1 else None
            elif locator.startswith("css:"):
                matches = soup.select(locator[4:])
                element = matches[0] if len(matches) == 1 else None
            else:
                element = soup.find(id=locator)
            actual = (
                " ".join(element.get_text(" ", strip=True).split()) if element else ""
            )
            if not evidence["text"] or evidence["text"] not in actual:
                raise ValueError("Sample annotation does not match source evidence")
            citations.append(evidence["locator"])
        verified[selector] = (
            metadata,
            " Reviewed sample identity: " + " | ".join(citations),
        )
    return verified


def _measurement_conditions(text):
    # Never use apparatus dimensions, preparation temperatures, or a standard's
    # assumed defaults as a measurement temperature.
    if not re.search(
        r"(?:measur\w*|test\w*|conducted|performed|carried out)\s+(?:\w+\s+){0,5}"
        r"(?:at|under)\s+(?:(?:a\s+)?room temperature of\s+)?[−+-]?\d+(?:\.\d+)?\s*[°º]?\s*[CKF]\b",
        text,
        re.IGNORECASE,
    ):
        return {}
    meta = conditions(text, role="measurement")
    if meta.get("quality_flag"):
        return {}
    return {k: v for k, v in meta.items() if k in {"temperature_C", "temperature_role"}}


def _protocol_blocks(paragraphs):
    """Associate numbered property headings with explicit adjacent test methods."""
    protocols = {}
    numbered_heading = r"^\s*(?:\(\d+\)|\d+[.)])\s*"
    for i, paragraph in enumerate(paragraphs):
        heading = paragraph.get_text(" ", strip=True)
        if len(heading) > 160 or (
            paragraph.name != "heading" and not re.match(numbered_heading, heading)
        ):
            continue
        body = []
        for following in paragraphs[i + 1 : i + 4]:
            text = following.get_text(" ", strip=True)
            if (
                following.name == "heading"
                or re.match(numbered_heading, text)
                or len(text) < 10
            ):
                break
            body.append(text)
        text = " ".join([heading, *body])
        if not re.search(
            r"measur|determined|calculated|performed|according to|ASTM|JIS",
            " ".join(body),
            re.IGNORECASE,
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


def _example_per_row(rows):
    """Join explicit multi-line column headings, preserving physical row numbers."""
    sample = re.compile(
        r"(?:(?:comparative|comparison|control)\s+)?(?:example|ex\.?)\s*\d+(?:-\d+)?",
        re.IGNORECASE,
    )
    first = next(
        (
            i
            for i, row in enumerate(rows)
            if len(row) >= 3 and sample.fullmatch(row[0].strip())
        ),
        None,
    )
    if first is None:
        return None
    width = len(rows[first])
    # Include a split "Comparative / Example 1" row immediately before it.
    if first and rows[first - 1][0].strip().lower() in {"comparative", "comparison"}:
        first -= 1
    headers = []
    for col in range(1, width):
        fragments = []
        for row in rows[:first]:
            if len(row) != width or sum(bool(c.strip()) for c in row) < 2:
                continue
            cell = row[col].strip()
            if (
                cell
                and not re.match(r"^TABLE\s+\d", cell, re.IGNORECASE)
                and cell not in fragments
            ):
                fragments.append(cell)
        headers.append(" ".join(fragments))
    props = {property_name(h) for h in headers} - {None}
    if len(props) < 2 or not props.intersection(
        {
            "porosity",
            "tensile_strength",
            "thermal_shrinkage",
            "puncture_force",
            "air_permeability_time",
            "gurley_time",
        }
    ):
        return None
    body, locators = [], []
    for i in range(first, len(rows)):
        row = rows[i]
        if len(row) != width:
            continue
        label = row[0].strip()
        if label.lower() in {"comparative", "comparison"} and i + 1 < len(rows):
            following = rows[i + 1]
            if (
                len(following) == width
                and sample.fullmatch(following[0].strip())
                and not any(c.strip() for c in following[1:])
            ):
                label += " " + following[0].strip()
        if not sample.fullmatch(label) or not any(c.strip() for c in row[1:]):
            continue
        body.append([label, *row[1:]])
        locators.append(i + 1)
    if not body:
        return None
    return [
        ["Property", *[r[0] for r in body]],
        *[[h, *[r[c] for r in body]] for c, h in enumerate(headers, 1)],
    ], locators


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
    sample_annotations = _verified_sample_context(soup, context)
    recipe_identities = None
    paragraphs = [
        p
        for p in description.select(
            ".description-paragraph, .description-line, heading"
        )
        if p.name == "heading" or p.find("heading") is None
    ]
    protocols = _protocol_blocks(paragraphs)
    property_methods = {}
    for paragraph in paragraphs:
        if paragraph.name == "heading":
            continue
        text = paragraph.get_text(" ", strip=True)
        prop = property_name(text)
        if prop and re.search(
            r"measur|determin|test|micrometer", paragraph.get_text(), re.IGNORECASE
        ):
            property_methods.setdefault(prop, []).append((text, paragraph.get("id")))
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
        normalized = _example_per_row(rows)
        sample_source_rows = None
        if normalized:
            working_rows, sample_source_rows = normalized
            transposed = True
        else:
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
                    range(example_columns[0], len(header))
                ):
                    if len(header) == len(row):
                        first_value = example_columns[0]
                    elif (
                        len(row) == len(header) + 1
                        and example_columns[0] == 1
                        and re.fullmatch(
                            r"%|[μµu]m|nm|mm|[mk]?Pa|MPa|[mk]?N|gf|kgf|[°º]?\s*C\.?|"
                            r"s(?:ec\.?)?(?:/100\s*(?:cc|cm\s*3|ml))?|g/m\s*2|"
                            r"kgf/cm\s*2|[WJ]/.*",
                            row[1],
                            re.IGNORECASE,
                        )
                    ):
                        first_value = 2
            split = _split_example_header(working_rows[:row_index], len(row))
            unit_column = first_value == 2
            if split:
                first_value, split_headers, unit_column = split
            label = " ".join(row[: 1 if unit_column else first_value]).strip()
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
            if split and not any(headers):
                headers = split_headers
            table_polymers = _table_polymers(
                working_rows[:row_index], len(value_cells), first_value
            )
            unit_match = re.search(r"\(([^)]+)\)", label)
            raw_unit = (
                row[1]
                if unit_column
                else unit_match[1]
                if unit_match
                else "%"
                if "percentage" in label.lower()
                else context.get("units", {}).get(prop, "")
            )
            if not raw_unit:
                terminal = re.search(
                    r"(%|[μµu]m|nm|mm|MPa|kPa|mN|gf|N|kgf/cm\s*2|[°º]\s*C\.?)\s*$",
                    label,
                )
                if terminal:
                    raw_unit = terminal[1]
                elif prop == "tortuosity":
                    # A dimensionless property; never infer units for a magnitude.
                    raw_unit = "1"
            # The temperature is part of the label, not the property unit.
            temp_meta = conditions(label) if prop == "thermal_shrinkage" else {}
            if prop == "thermal_shrinkage" and "%" in label:
                raw_unit = "%"
            unit = canonical_unit_text(raw_unit)
            property_context = method_context if prop == "thermal_shrinkage" else ""
            property_locator = method_locator if prop == "thermal_shrinkage" else None
            if prop != "thermal_shrinkage":
                methods = property_methods.get(prop, [])
                if len(methods) == 1:
                    property_context, property_locator = methods[0]
            linked = protocols.get(prop, {})
            if len(linked) == 1:
                property_context, property_locator = next(iter(linked.items()))
            elif len(linked) > 1:
                property_context, property_locator = "", None
            for column, cell in enumerate(value_cells, 1):
                sample = headers[column - 1]
                sample_meta, identity_note = sample_annotations.get(
                    table_name + ":" + sample,
                    sample_annotations.get(sample, ({}, "")),
                )
                if sample_meta.get("polymer"):
                    identity = Identity(
                        sample_meta["polymer"],
                        "reviewed_sample_link",
                        tuple(
                            context.get("sample_annotations", {})
                            .get(
                                table_name + ":" + sample,
                                context.get("sample_annotations", {}).get(sample, {}),
                            )
                            .get("evidence", [])
                        ),
                    )
                elif context.get("polymer"):
                    identity = Identity(
                        context["polymer"],
                        "supplied_source_identity",
                        reason="Material supplied in source ingestion context",
                    )
                elif table_polymers.get(column - 1, (None, ""))[0]:
                    identity = Identity(
                        table_polymers[column - 1][0],
                        "explicit_composition_table",
                        (
                            {
                                "locator": table_name,
                                "text": table_polymers[column - 1][1],
                            },
                        ),
                    )
                else:
                    if recipe_identities is None:
                        recipe_identities = PatentIdentities(soup)
                    identity = recipe_identities.resolve(sample)
                parsed_values = [
                    (v, s, direction(label)) for v, s in values(cell, label)
                ]
                pair = re.fullmatch(
                    rf"\s*({NUMBER})\s*/\s*({NUMBER})\s*", cell.replace("−", "-")
                )
                paired_note = ""
                if (
                    pair
                    and prop in {"thermal_shrinkage", "tensile_strength", "elongation"}
                    and re.search(r"\bMD\s*/{1,2}\s*TD\b", label, re.IGNORECASE)
                ):
                    parsed_values = [
                        (pair[1], "reported", "MD"),
                        (pair[2], "reported", "TD"),
                    ]
                    paired_note = f" Printed MD/TD cell: {cell}. "
                for value, statistic, value_direction in parsed_values:
                    meta = (
                        (
                            {**base_meta, **temp_meta}
                            if temp_meta
                            else conditions(property_context)
                        )
                        if prop == "thermal_shrinkage"
                        else _measurement_conditions(property_context)
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
                                sample_source_rows[column - 1]
                                if sample_source_rows is not None
                                else first_value + column
                                if transposed
                                else row_index + 1
                            ),
                            source_column=str(
                                row_index + 1 if transposed else first_value + column
                            ),
                            polymer=identity.polymer,
                            **identity.fields(),
                            sample_form="separator",
                            separator_architecture=sample_meta.get(
                                "separator_architecture"
                            )
                            or context.get("separator_architecture"),
                            coating=sample_meta.get("coating"),
                            material_grade=sample_meta.get("material_grade"),
                            statistic=statistic,
                            record_type="spec_limit"
                            if statistic in {"minimum", "maximum"}
                            else "measured",
                            quality_flag=pending,
                            direction=value_direction,
                            shrinkage_basis="length"
                            if prop == "thermal_shrinkage"
                            and "length" in property_context.lower()
                            else "area"
                            if prop == "thermal_shrinkage"
                            and "area" in property_context.lower()
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
                            "Example identity and experimental protocol retained; no processing temperature inferred. "
                            + table_polymers.get(column - 1, (None, ""))[1]
                            + identity_note
                            + paired_note,
                            **meta,
                        )
                    )
    images = soup.select('li[itemprop="images"]')
    figure_caption = (
        " ".join(
            p.get_text(" ", strip=True)
            for p in paragraphs
            if re.search(
                r"FIG(?:URE)?\.?\s*\d+.*(?:is |shows |showing )",
                p.get_text(),
                re.IGNORECASE,
            )
        )
        if images
        else ""
    )
    sheet = 0
    for image in images:
        full = image.select_one('meta[itemprop="full"]')
        if full:
            sheet += 1
            artifacts.append(
                {
                    "kind": "figure",
                    "url": urljoin(
                        document.url or "https://patents.google.com", full["content"]
                    ),
                    "caption": figure_caption,
                    "sheet": str(sheet),
                }
            )
    pdf = soup.select_one('meta[name="citation_pdf_url"]')
    if pdf and pdf.get("content"):
        artifacts.append({"kind": "pdf_fallback", "url": pdf["content"]})
    return records, artifacts
