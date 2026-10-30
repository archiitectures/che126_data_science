"""Reviewed metadata revisions preserve values and reject stale source evidence."""

import hashlib
from dataclasses import replace

import pytest

from che126_data_science.data_mining.acquisition import RawDocument
from che126_data_science.data_mining.reviewed_conditions import (
    apply_reviewed_conditions,
)
from che126_data_science.data_science.master import make_observation


def test_condition_revision_is_source_bound_and_repeatable(tmp_path):
    path = tmp_path / "source.html"
    path.write_text("<p>Puncture was tested in an atmosphere of 25 °C.</p>")
    doc = RawDocument(
        source_id="source",
        source="patents",
        url="https://example.org",
        path=str(path),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        retrieved_at="2026-10-26",
    )
    row = make_observation(
        doc,
        label="Puncture force",
        prop="puncture_force",
        raw_value="2",
        raw_unit="N",
        sample_id="Example 1",
    )
    revision = {
        "metadata": {"temperature_C": 25.0, "temperature_role": "measurement"},
        "source_sha256": doc.sha256,
        "quote": "tested in an atmosphere of 25 °C",
    }
    new = apply_reviewed_conditions([row], doc, {row.observation_id: revision})[0]
    assert new.temperature_C == 25 and new.value == row.value
    assert new.observation_id != row.observation_id
    assert (
        apply_reviewed_conditions([row], doc, {row.observation_id: revision})[0] == new
    )
    assert row.observation_id in new.notes
    for bad in [
        {**revision, "source_sha256": "stale"},
        {**revision, "quote": "tested at 90 °C"},
        {**revision, "metadata": {**revision["metadata"], "value": 99}},
    ]:
        with pytest.raises(ValueError):
            apply_reviewed_conditions([row], doc, {row.observation_id: bad})
    with pytest.raises(ValueError):
        apply_reviewed_conditions([row], doc, {"missing-id": revision})
    with pytest.raises(ValueError):
        apply_reviewed_conditions(
            [replace(row, temperature_C=20, temperature_role="measurement")],
            doc,
            {row.observation_id: revision},
        )


def test_semilog_trace_and_area_specific_resistance(tmp_path):
    from PIL import Image, ImageDraw

    from che126_data_science.data_mining.digitize import digitize

    image = Image.new("RGB", (100, 100), "white")
    ImageDraw.Draw(image).line((20, 40, 80, 40), fill="black", width=1)
    path = tmp_path / "curve.png"
    image.save(path)
    config = {
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "crop": [20, 37, 80, 44],
        "x_reference": [[20, 0], [80, 60]],
        "y_reference": [[80, 1], [20, 1000]],
        "x_unit": "C",
        "y_unit": "ohm cm2",
        "plot_type": "semilog_y",
        "single_series": True,
        "series_label": "Example 1",
        "sample_step_px": 1,
    }
    result = digitize(path, config, tmp_path / "trace")
    assert result["status"] == "accepted"
    import csv

    rows = list(csv.DictReader((tmp_path / "trace/curve_points.csv").open()))
    assert all(float(r["y"]) == pytest.approx(100) for r in rows)
    assert all(float(r["uncertainty_y"]) > 0 for r in rows)
    doc = RawDocument(
        source_id="curve",
        source="manual",
        url="https://example.org",
        path=str(path),
        sha256=config["source_sha256"],
        retrieved_at="2026-10-26",
    )
    row = make_observation(
        doc,
        label="Area specific resistance",
        prop="area_specific_resistance",
        raw_value="100",
        raw_unit="ohm cm2",
        sample_id="Example 1",
    )
    assert row.review_status == "accepted" and row.unit == "ohm m2"
    assert row.value == pytest.approx(0.01)
    with pytest.raises(KeyError):
        from che126_data_science.data_science.observations import CONVERSIONS

        CONVERSIONS["ohm cm2", "ohm"]


def test_figure_import_retains_page_figure_and_conductivity_units(tmp_path):
    from che126_data_science.data_mining.structured import extract_manual

    path = tmp_path / "values.csv"
    path.write_text(
        "sample_id,property,value,unit,source_page,source_figure,temperature_C,temperature_role,record_type\nsample,ionic_conductivity,0.00107,S/cm,6,3f,25,measurement,measured\n"
    )
    doc = RawDocument(
        source_id="labels",
        source="manual",
        url="https://example.org",
        path=str(path),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        retrieved_at="2026-10-26",
    )
    rows, _ = extract_manual(doc, {})
    assert len(rows) == 1 and rows[0].review_status == "accepted"
    assert rows[0].source_page == 6 and rows[0].source_figure == "3f"
    assert rows[0].value == pytest.approx(0.107) and rows[0].unit == "S/m"


def test_external_primary_condition_evidence_is_bound_to_import(tmp_path):
    """Manual imports can recover conditions only from the same cited source."""
    import hashlib

    source = tmp_path / "import.csv"
    source.write_text("sample,value\nPE,2\n")
    primary = tmp_path / "paper.xml"
    primary.write_text("<article><p>Impedance was measured at 25 °C.</p></article>")
    doc = RawDocument(
        "import", "manual", str(source), hashlib.sha256(source.read_bytes()).hexdigest()
    )
    row = make_observation(
        doc,
        label="Resistance",
        prop="electrical_resistance",
        raw_value=2,
        raw_unit="ohm",
        sample_id="PE",
        source_url="https://example.org/paper",
    )
    evidence = {
        "path": str(primary),
        "sha256": hashlib.sha256(primary.read_bytes()).hexdigest(),
        "source_url": row.source_url,
    }
    revision = {
        "source_sha256": doc.sha256,
        "quote": "Impedance was measured at 25 °C.",
        "metadata": {"temperature_C": 25.0, "temperature_role": "measurement"},
        "evidence_document": evidence,
    }
    corrected = apply_reviewed_conditions([row], doc, {row.observation_id: revision})[0]
    assert corrected.temperature_C == 25 and corrected.value == 2
    for bad in [
        {**evidence, "sha256": "wrong"},
        {**evidence, "source_url": "https://example.org/other"},
    ]:
        with pytest.raises(ValueError, match="External condition evidence"):
            apply_reviewed_conditions(
                [row], doc, {row.observation_id: {**revision, "evidence_document": bad}}
            )
