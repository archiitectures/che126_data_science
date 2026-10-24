"""Regression cases from the automation audit; no network or paid providers."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from che126_data_science.data_mining.acquisition import DocumentStore
from che126_data_science.data_mining.normalization import conditions
from che126_data_science.data_mining.pipeline import Pipeline


def observations(result):
    return json.loads(Path(result["artifact_file"]).read_text())["observations"]


def patent(tmp_path, table, method):
    path = tmp_path / "patent.html"
    path.write_text(
        '<html><title>US123456B2</title><section itemprop="description">'
        f'<p class="description-paragraph" id="method">{method}</p>'
        f"<table>{table}</table></section></html>"
    )
    return observations(Pipeline(tmp_path / "data").ingest("patents", path))


@pytest.mark.parametrize(
    "text", ["100–150 C", "100-150 C", "100 to 150 C", "100 C and 150 C"]
)
def test_temperature_ambiguity_not_accepted(tmp_path, text):
    assert conditions(text)["quality_flag"] == "ambiguous_temperature_condition"
    rows = patent(
        tmp_path,
        "<tr><td>Property</td><td>Example 1</td></tr>"
        f"<tr><td>Shrinkage (%) at {text}</td><td>5</td></tr>",
        "Shrinkage length was measured for 1 hour.",
    )
    assert len(rows) == 1
    assert rows[0]["review_status"] == "pending"
    assert rows[0]["temperature_C"] is None


def test_structured_invalid_row_preserves_neighbors_and_evidence(tmp_path):
    path = tmp_path / "rows.csv"
    path.write_text(
        "property,value,unit,sample_id,temperature_C,temperature_role\n"
        "thickness,20,um,a,,unknown\n"
        "thickness,21,um,b,25,unknown\n"
        "thickness,22,um,c,,unknown\n"
    )
    rows = observations(Pipeline(tmp_path / "data").ingest("manual", path))
    assert [r["value"] for r in rows if r["review_status"] == "accepted"] == [20, 22]
    invalid = next(r for r in rows if r["review_status"] == "pending")
    assert invalid["source_row"] == "3"
    assert json.loads(invalid["original_value"])["temperature_C"] == "25"


def test_bounded_patent_cells_keep_examples(tmp_path):
    rows = patent(
        tmp_path,
        "<tr><td>Property</td><td>Example 1</td><td>Example 2</td></tr>"
        "<tr><td>Thickness (um)</td><td>≤20</td><td>≥21</td></tr>",
        "Thickness was measured with a micrometer.",
    )
    assert [(r["value"], r["statistic"], r["source_column"]) for r in rows] == [
        (20, "maximum", "2"),
        (21, "minimum", "3"),
    ]
    assert [r["sample_id"].split(":")[-1] for r in rows] == ["Example 1", "Example 2"]
    assert all(r["record_type"] == "spec_limit" for r in rows)


@pytest.mark.parametrize(
    "table, coords",
    [
        (
            (
                "<tr><td>Property</td><td>Unit</td><td>Example 1</td></tr>"
                "<tr><td>Porosity</td><td>%</td><td>40</td></tr>"
            ),
            ("2", "3"),
        ),
        (
            (
                "<tr><td>Sample</td><td>Porosity (%)</td></tr>"
                "<tr><td>Example 1</td><td>40</td></tr>"
            ),
            ("2", "2"),
        ),
    ],
)
def test_property_protocol_and_layouts(tmp_path, table, coords):
    rows = patent(tmp_path, table, "Porosity was measured by mass and volume.")
    assert len(rows) == 1
    assert rows[0]["review_status"] == "accepted"
    assert rows[0]["value"] == 40
    assert (rows[0]["source_row"], rows[0]["source_column"]) == coords


def test_conflicting_methods_remain_review(tmp_path):
    rows = patent(
        tmp_path,
        "<tr><td>Property</td><td>Example 1</td></tr>"
        "<tr><td>Porosity (%)</td><td>40</td></tr>",
        'Porosity was measured by mass.</p><p class="description-paragraph">'
        "Porosity was measured by another method.",
    )
    assert rows[0]["review_status"] == "pending"


def test_collection_advances_persisted_cursor_and_refreshes(tmp_path, monkeypatch):
    from che126_data_science.data_mining import discovery

    path = tmp_path / "rows.csv"
    path.write_text("property,value,unit,sample_id\nthickness,20,um,a\n")
    calls = []

    class Store(DocumentStore):
        def fetch(self, source, location, **kwargs):
            calls.append(location)
            return super().fetch(source, path, source_url=location)

    # Distinct source IDs just like remote fetch; local fixture bytes may be identical.
    from dataclasses import replace

    from che126_data_science.data_science.master import fingerprint

    class RemoteStore(Store):
        def fetch(self, source, location, **kwargs):
            return replace(
                super().fetch(source, location, **kwargs),
                source_id=fingerprint(location),
            )

    docs = [{"url": f"https://example.org/{i}.csv"} for i in range(3)]
    monkeypatch.setattr(discovery, "fsri_files", lambda *a, **k: docs)
    root = tmp_path / "data"
    for index in range(3):
        p = Pipeline(root, store=RemoteStore(root))
        result = p.collect(sources=["fsri"], max_documents=1)
        assert result["remaining_candidates"] == 2 - index
    assert calls == [d["url"] for d in docs]
    assert not p.collect(sources=["fsri"], max_documents=1)["documents"]
    p.collect(sources=["fsri"], max_documents=1, refresh=True)
    assert calls[-1] == docs[0]["url"]


def test_sdk_failure_does_not_abort_other_sources(tmp_path, monkeypatch):
    exceptions = pytest.importorskip("google.api_core.exceptions")
    from che126_data_science.data_mining import discovery

    monkeypatch.setattr(
        discovery.EPOClient, "search", Mock(side_effect=exceptions.Forbidden("denied"))
    )
    monkeypatch.setattr(
        discovery, "fsri_files", lambda *a, **k: [{"url": "https://example.org/a.csv"}]
    )
    p = Pipeline(tmp_path / "data")
    p.ingest = Mock(return_value={"status": "complete"})
    result = p.collect(sources=["patents", "fsri"])
    assert result["discovery"][0]["status"] == "discovery_failed"
    p.ingest.assert_called_once()


def test_programming_errors_not_swallowed(tmp_path, monkeypatch):
    from che126_data_science.data_mining import discovery

    monkeypatch.setattr(
        discovery, "fsri_files", Mock(side_effect=AttributeError("bug"))
    )
    with pytest.raises(AttributeError):
        Pipeline(tmp_path / "data").collect(sources=["fsri"])


def test_protocol_temperature_range_requires_review(tmp_path):
    rows = patent(
        tmp_path,
        "<tr><td>Property</td><td>Example 1</td></tr>"
        "<tr><td>Shrinkage (%)</td><td>5</td></tr>",
        "Shrinkage length was measured at 100–150 C for 1 hour.",
    )
    assert rows[0]["review_status"] == "pending"
    assert rows[0]["temperature_C"] is None


def test_missing_html_description_retains_pdf_fallback(tmp_path):
    from che126_data_science.data_mining.patent_html import extract_patent

    path = tmp_path / "source.html"
    path.write_text(
        '<meta name="citation_pdf_url" content="https://example.org/patent.pdf">'
    )
    doc = DocumentStore(tmp_path / "data").fetch("patents", path)
    rows, artifacts = extract_patent(doc, {})
    assert not rows
    assert artifacts == [
        {"kind": "pdf_fallback", "url": "https://example.org/patent.pdf"}
    ]


def test_folder_continues_after_bad_document(tmp_path):
    from argparse import Namespace

    from che126_data_science.data_mining.pipeline_cli import run

    folder = tmp_path / "inputs"
    folder.mkdir()
    (folder / "a.xlsx").write_bytes(b"not an xlsx archive")
    (folder / "b.csv").write_text("property,value,unit,sample_id\nthickness,20,um,a\n")
    result = run(
        Namespace(
            command="ingest",
            source="manual",
            input=str(folder),
            context=None,
            data_dir=tmp_path / "data",
            refresh=False,
        )
    )
    assert result["outputs"]["accepted"] == 1
    assert len(result["documents"]) == 2


def test_numbered_protocol_heading_with_separate_body_and_ex_headers(tmp_path):
    rows = patent(
        tmp_path,
        "<tr><td>Property</td><td>Ex 1</td><td>Ex 2</td></tr>"
        "<tr><td>Porosity (%)</td><td>40</td><td>45</td></tr>",
        '(1) Porosity (%)</p><p class="description-paragraph" id="body">'
        "Measured by a weight method.",
    )
    assert len(rows) == 2
    assert all(r["review_status"] == "accepted" for r in rows)
    assert rows[0]["sample_id"].endswith(":Ex 1")
    assert "weight method" in rows[0]["measurement_context"]


def test_description_line_view_and_explicit_force_units(tmp_path):
    path = tmp_path / "source.html"
    path.write_text(
        '<html><title>US123456B2</title><section itemprop="description">'
        '<div class="description-line" num="1">(1) Tensile rupture strength</div>'
        '<div class="description-line">Measured according to ASTM D882.</div>'
        "<table><tr><td>Property</td><td>Example 1</td></tr>"
        "<tr><td>Tensile rupture strength (kgf/cm 2)</td><td>100</td></tr>"
        "</table></section></html>"
    )
    rows = observations(Pipeline(tmp_path / "data").ingest("patents", path))
    assert len(rows) == 1
    assert rows[0]["review_status"] == "accepted"
    assert rows[0]["value"] == pytest.approx(9.80665)
    assert rows[0]["unit"] == "MPa"


def test_numbered_shrinkage_method_supplies_temperature(tmp_path):
    rows = patent(
        tmp_path,
        "<tr><td>Property</td><td>Example 1</td></tr>"
        "<tr><td>Shrinkage (%)</td><td>5</td></tr>",
        '(1) Shrinkage (%)</p><p class="description-paragraph">'
        "Measured after exposure to 105 C for 8 hours.",
    )
    assert rows[0]["review_status"] == "accepted"
    assert rows[0]["temperature_C"] == 105
    assert rows[0]["duration_min"] == 480


def test_normalized_thickness_force_stays_unresolved(tmp_path):
    rows = patent(
        tmp_path,
        "<tr><td>Property</td><td>Example 1</td></tr>"
        "<tr><td>Puncture strength (mN/20 um)</td><td>2500</td></tr>",
        "Puncture strength was measured with a needle.",
    )
    assert rows[0]["review_status"] == "pending"
    assert rows[0]["unit"] is None


def test_shared_example_heading_with_number_and_unit_row(tmp_path):
    rows = patent(
        tmp_path,
        "<tr><td></td><td>Example</td></tr>"
        "<tr><td>Item</td><td>Unit</td><td>1</td><td>2</td></tr>"
        "<tr><td>Porosity</td><td>%</td><td>40</td><td>45</td></tr>",
        "Porosity was measured by a weight method.",
    )
    assert [r["sample_id"].split(":")[-1] for r in rows] == ["Example 1", "Example 2"]
    assert all(r["review_status"] == "accepted" for r in rows)
    assert [r["source_column"] for r in rows] == ["3", "4"]


def test_shared_comparative_groups_are_not_guessed(tmp_path):
    rows = patent(
        tmp_path,
        "<tr><td>Example</td><td>Comparative Example</td></tr>"
        "<tr><td>Item</td><td>Unit</td><td>1</td><td>2</td></tr>"
        "<tr><td>Porosity</td><td>%</td><td>40</td><td>45</td></tr>",
        "Porosity was measured by a weight method.",
    )
    assert all(r["review_status"] == "pending" for r in rows)
