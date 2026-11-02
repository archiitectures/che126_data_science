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


def test_numbered_sample_table_keeps_layer_scope_and_explicit_temperature(tmp_path):
    source = tmp_path / "samples.html"
    source.write_text("""<title>US1234571B2</title><section itemprop="description">
    <table><tr><td>TABLE 1 Ultra Thin Microporous Membrane Separator Properties</td></tr>
    <tr><td>ID</td><td>Sample 1</td><td>Sample 2</td></tr>
    <tr><td>Description</td><td>PP/PE/PP 65% PP</td><td>PE</td></tr>
    <tr><td>Thickness (um)</td><td>12</td><td>9</td></tr>
    <tr><td>PP Pore Size (um)</td><td>0.05</td><td>—</td></tr>
    <tr><td>Thermal shrinkage at 90 deg C for 1 hour (%)</td><td>2%</td><td>3%</td></tr>
    </table></section>""")
    import json
    from pathlib import Path

    result = Pipeline(tmp_path / "data").ingest("patents", source)
    rows = json.loads(Path(result["artifact_file"]).read_text())["observations"]
    accepted = [r for r in rows if r["review_status"] == "accepted"]
    assert len(accepted) == 5
    pore = next(r for r in accepted if r["property"] == "pore_size")
    assert pore["polymer"] == "PP" and pore["sample_form"] == "separator_component"
    thickness = [r for r in accepted if r["property"] == "thickness"]
    assert {r["polymer"] for r in thickness} == {"PE", "PP/PE/PP"}
    assert all(r["temperature_C"] is None for r in thickness)
    shrink = [r for r in accepted if r["property"] == "thermal_shrinkage"]
    assert all(r["temperature_C"] == 90 and r["duration_min"] == 60 for r in shrink)


def test_numbered_sample_without_empirical_caption_stays_in_review(tmp_path):
    source = tmp_path / "generic.html"
    source.write_text("""<title>US1234572B2</title><section itemprop="description"><table>
    <tr><td>Item</td><td>Sample 1</td></tr><tr><td>Description</td><td>PP/PE/PP</td></tr>
    <tr><td>Thickness (um)</td><td>12</td></tr></table></section>""")
    import json
    from pathlib import Path

    result = Pipeline(tmp_path / "data").ingest("patents", source)
    rows = json.loads(Path(result["artifact_file"]).read_text())["observations"]
    assert all(r["review_status"] == "pending" for r in rows)


def test_reviewed_collection_scope_retains_unapproved_rows_in_review(tmp_path):
    source = tmp_path / "observations.csv"
    source.write_text(
        "sample_id,property,value,unit,polymer\na,thickness,12,um,PP\nb,thickness,20,um,PE\n"
    )
    p = Pipeline(tmp_path / "data")
    result = p.ingest("manual", source)
    import json
    from pathlib import Path

    rows = json.loads(Path(result["artifact_file"]).read_text())["observations"]
    result = p.ingest(
        "manual",
        source,
        context={"accepted_observation_ids": [rows[0]["observation_id"]]},
    )
    scoped = json.loads(Path(result["artifact_file"]).read_text())["observations"]
    assert [r["review_status"] for r in scoped] == ["accepted", "pending"]
    assert scoped[1]["quality_flag"] == "outside_reviewed_collection_scope"
    assert [r["value"] for r in scoped] == [12, 20]


def test_patent_family_is_read_from_own_family_section(tmp_path):
    source = tmp_path / "family.html"
    source.write_text("""<title>US1234573B2</title><section itemprop="description">
    <div class="description-paragraph">Thickness was measured with a micrometer.</div>
    <table><tr><td>Property</td><td>Example 1</td></tr><tr><td>Thickness (um)</td><td>12</td></tr></table></section>
    <section itemprop="family"><h1>Family</h1><h2>ID=80776704</h2></section>""")
    import json
    from pathlib import Path

    r = Pipeline(tmp_path / "data").ingest("patents", source)
    rows = json.loads(Path(r["artifact_file"]).read_text())["observations"]
    assert rows[0]["family_id"] == "80776704"


def test_directional_tensile_shorthand_does_not_accept_modulus_or_force():
    from che126_data_science.data_mining.normalization import property_name

    assert property_name("MD Tensile (MPa)") == "tensile_strength"
    assert property_name("MD Tensile modulus (MPa)") is None
    assert property_name("TD Tensile elastic modulus (MPa)") is None
    assert property_name("MD Tensile force (N)") is None


def test_pending_evidence_cannot_shadow_accepted_copy(tmp_path):
    from dataclasses import asdict

    from che126_data_science.data_science.master import EXTRACTION_VERSION, atomic_json

    p = Pipeline(tmp_path / "assembled")
    for key, flag in [("a", "needs_review"), ("b", None)]:
        doc = document(tmp_path, key)
        row = make_observation(
            doc,
            label="Thickness",
            prop="thickness",
            raw_value=12,
            raw_unit="um",
            sample_id="sample",
            evidence_group="same-physical-cell",
            quality_flag=flag,
        )
        artifact = tmp_path / (key + ".json")
        atomic_json(
            artifact,
            {"extraction_version": EXTRACTION_VERSION, "observations": [asdict(row)]},
        )
        p.manifest["documents"][key] = {
            "document": asdict(doc),
            "artifact_file": str(artifact),
            "context": {},
        }
    result = p.aggregate()
    assert result["accepted"] == 1 and result["review"] == 1


def test_split_example_groups_preserve_comparative_identity(tmp_path):
    source = tmp_path / "split.html"
    source.write_text("""<title>US1234574B2</title><section itemprop="description">
    <div class="description-paragraph">Thickness was measured using a micrometer.</div>
    <div class="description-paragraph">Porosity was measured by volume and mass.</div>
    <heading>Example 1</heading><div class="description-paragraph">A polypropylene porous membrane was extruded.</div>
    <heading>Comparative Example 1</heading><div class="description-paragraph">A polyethylene porous membrane was extruded.</div>
    <table><tr><td>Property</td><td>Example</td><td>Comparative Example</td></tr>
    <tr><td>No.</td><td>1</td><td>1</td></tr>
    <tr><td>Thickness (um)</td><td>12</td><td>10</td></tr>
    <tr><td>Porosity (%)</td><td>45</td><td>55</td></tr></table></section>""")
    import json
    from pathlib import Path

    r = Pipeline(tmp_path / "data").ingest("patents", source)
    rows = json.loads(Path(r["artifact_file"]).read_text())["observations"]
    assert len(rows) == 4 and all(x["review_status"] == "accepted" for x in rows)
    assert {x["sample_id"].split(":")[-1] for x in rows} == {
        "Example 1",
        "Comparative Example 1",
    }
    assert {x["polymer"] for x in rows if x["sample_id"].endswith(":Example 1")} == {
        "PP"
    }
    assert {
        x["polymer"] for x in rows if x["sample_id"].endswith(":Comparative Example 1")
    } == {"PE"}


def test_abbreviated_standard_deviation_is_not_absolute_thickness(tmp_path):
    doc = document(tmp_path, "placeholder")
    r = make_observation(
        doc,
        label="Thickness std. dev. (um)",
        prop="thickness",
        raw_value=0.4,
        raw_unit="um",
        sample_id="sample",
    )
    assert r.review_status == "pending"


def test_direction_values_do_not_inherit_next_property_heading(tmp_path):
    from che126_data_science.data_mining.patent_html import extract_patent

    doc = document(
        tmp_path,
        """<title>US1234599B2</title>
    <section itemprop="description"><heading>Example 1</heading>
    <p>Thermal shrinkage was measured at 130 C for 1 hour.</p>
    <table><tr><td>TABLE 1</td></tr>
    <tr><td></td><td>Example 1</td><td>Example 2</td></tr>
    <tr><td>Tensile rupture elongation (%)</td></tr>
    <tr><td>MD/TD</td><td>145/230</td><td>170/160</td></tr>
    <tr><td>Heat shrinkage ratio (%)</td></tr>
    <tr><td>MD/TD</td><td>6/4</td><td>5/6</td></tr></table></section>""",
    )
    rows, _ = extract_patent(doc, {})
    elongation = [r.value for r in rows if r.property == "elongation"]
    shrinkage = [r.value for r in rows if r.property == "thermal_shrinkage"]
    assert sorted(elongation) == [145, 160, 170, 230]
    assert sorted(shrinkage) == [4, 5, 6, 6]
