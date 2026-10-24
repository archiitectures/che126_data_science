"""Independent review regressions: semantic values, inputs and deduplication."""

from dataclasses import replace

import pytest

from che126_data_science.data_mining.acquisition import DocumentStore
from che126_data_science.data_mining.pipeline import Pipeline
from che126_data_science.data_mining.structured import extract_manual
from che126_data_science.data_science.master import (
    SCIENTIFIC_FIELDS,
    fingerprint,
    make_observation,
)


def document(tmp_path, content):
    path = tmp_path / "input.csv"
    path.write_text(content)
    return DocumentStore(tmp_path / "data").fetch("manual", path)


@pytest.mark.parametrize(
    "label",
    [
        "standard deviation of puncture strength (N)",
        "Increase in puncture strength (gf)",
    ],
)
def test_relative_puncture_values_require_review(tmp_path, label):
    doc = document(tmp_path, "placeholder")
    row = make_observation(
        doc,
        label=label,
        prop="puncture_force",
        raw_value="2",
        raw_unit="N",
        sample_id="example 1",
    )
    assert row.review_status == "pending"
    assert row.quality_flag == "derived_property_definition_requires_review"
    assert row.original_value == "2"


def test_structured_duplicate_headers_are_rejected(tmp_path):
    doc = document(
        tmp_path, "sample_id,property,value,value,unit\nx,thickness,10,99,um\n"
    )
    with pytest.raises(ValueError, match="duplicate headers"):
        extract_manual(doc, {})


@pytest.mark.parametrize("row", ["x,thickness,10,um,extra", "x,thickness,10"])
def test_bad_csv_width_is_retained_in_review(tmp_path, row):
    doc = document(tmp_path, "sample_id,property,value,unit\n" + row + "\n")
    rows, _ = extract_manual(doc, {})
    assert len(rows) == 1 and rows[0].review_status == "pending"


def test_mapped_duplicate_fields_are_rejected(tmp_path):
    doc = document(
        tmp_path, "sample_id,property,value,unit,other\nx,thickness,10,um,90\n"
    )
    rows, _ = extract_manual(doc, {"columns": {"other": "value"}})
    assert rows[0].review_status == "pending"


def test_context_key_distinguishes_protocol_basis_and_replicate(tmp_path):
    doc = document(tmp_path, "placeholder")
    base = make_observation(
        doc,
        label="shrinkage",
        prop="thermal_shrinkage",
        raw_value="2",
        raw_unit="%",
        sample_id="example 1",
    )
    key = lambda row: fingerprint(
        {name: getattr(row, name) for name in SCIENTIFIC_FIELDS}
    )
    for field, value in [
        ("method", "ASTM"),
        ("measurement_context", "constrained"),
        ("shrinkage_basis", "area"),
        ("replicate_id", "R2"),
        ("material_grade", "UHMWPE"),
    ]:
        assert key(base) != key(replace(base, **{field: value}))


def test_shrinkage_basis_not_attached_to_other_properties(tmp_path):
    from pathlib import Path

    source = Path(__file__).parent / "fixtures/pipeline/US9911958B2.html"
    p = Pipeline(tmp_path / "data")
    result = p.ingest("patents", source)
    import json

    rows = json.loads(Path(result["artifact_file"]).read_text())["observations"]
    assert all(
        r["shrinkage_basis"] is None
        for r in rows
        if r["property"] != "thermal_shrinkage"
    )
