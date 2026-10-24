import json
from pathlib import Path

import pytest

from che126_data_science.data_mining.normalization import (
    canonical_unit_text,
    property_name,
)
from che126_data_science.data_mining.pipeline import Pipeline


def test_recurring_properties_and_transition_temperature_are_distinct(tmp_path):
    pytest.importorskip("bs4")
    source = tmp_path / "US1234567B2.html"
    source.write_text("""<title>US1234567B2</title><section itemprop="description">
      <div class="description-paragraph" id="p1">Shutdown response time was measured as the time for electrical shutdown of each separator.</div>
      <div class="description-paragraph" id="p2">Tortuosity was determined using the electrolyte-filled separator impedance.</div>
      <div class="description-paragraph" id="p3">Electric resistance was measured at 25 °C using the separator impedance.</div>
      <div class="description-paragraph" id="p4">Shutdown temperature was determined using an impedance test while heating.</div>
      <table><tr><td>Property</td><td>Example 1</td><td>Example 2</td></tr>
      <tr><td>Shutdown response time (sec)</td><td>12</td><td>18</td></tr>
      <tr><td>Tortuosity</td><td>1.2</td><td>1.4</td></tr>
      <tr><td>Electric resistance (Ω)</td><td>0.72</td><td>0.83</td></tr>
      <tr><td>Shutdown Temp. (° C.)</td><td>132</td><td>135</td></tr></table></section>""")
    result = Pipeline(tmp_path / "data").ingest("patents", source)
    rows = json.loads(Path(result["artifact_file"]).read_text())["observations"]
    accepted = [r for r in rows if r["review_status"] == "accepted"]
    assert len(accepted) == 8
    units = {r["property"]: r["unit"] for r in accepted}
    assert units == {
        "shutdown_response_time": "s",
        "tortuosity": "1",
        "electrical_resistance": "ohm",
        "shutdown_temperature": "C",
    }
    assert all(
        r["temperature_C"] == 25
        for r in accepted
        if r["property"] == "electrical_resistance"
    )
    assert all(
        r["temperature_C"] is None
        for r in accepted
        if r["property"] != "electrical_resistance"
    )


def test_units_and_uptake_speed_are_not_conflated():
    assert canonical_unit_text("° C.") == "C"
    assert canonical_unit_text("Ω") == "ohm"
    assert property_name("Electrolyte uptake (%)") == "electrolyte_uptake"
    assert property_name("Electrolyte absorption speed") is None
    assert property_name("Shutdown speed (sec)") == "shutdown_response_time"
    assert property_name("Shutdown temperature difference (°C)") is None
    assert property_name("Tortuosity ratio") is None
    assert property_name("Air permeability increase (sec/100cc)") is None
    assert property_name("Electrolyte contact angle (°)") == "contact_angle"


def test_decimal_numbered_protocol_heading_and_contact_angle(tmp_path):
    pytest.importorskip("bs4")
    source = tmp_path / "US1234569B2.html"
    source.write_text("""<title>US1234569B2</title><section itemprop="description">
      <heading id="h1">1. Contact Angle</heading>
      <div class="description-paragraph" id="p1">The separator contact angle was measured using a goniometer.</div>
      <table><tr><td>Property</td><td>Example 1</td><td>Example 2</td></tr>
      <tr><td>Contact angle (°)</td><td>75.8</td><td>60.2</td></tr></table></section>""")
    result = Pipeline(tmp_path / "data").ingest("patents", source)
    rows = json.loads(Path(result["artifact_file"]).read_text())["observations"]
    assert len(rows) == 2 and all(r["review_status"] == "accepted" for r in rows)
    assert all(r["property"] == "contact_angle" and r["unit"] == "deg" for r in rows)


def test_multiline_example_rows_preserve_comparatives_and_source_coordinates(tmp_path):
    pytest.importorskip("bs4")
    source = tmp_path / "US1234568B2.html"
    source.write_text("""<title>US1234568B2</title><section itemprop="description">
      <div class="description-paragraph" id="p1">Porosity was measured using specimen volume and mass.</div>
      <div class="description-paragraph" id="p2">Tensile strength was tested at 23 °C using ASTM D882.</div>
      <table><tr><td>TABLE 1</td></tr>
      <tr><td></td><td>Porosity</td><td>Tensile strength</td></tr>
      <tr><td></td><td>(%)</td><td>MD (MPa)</td></tr>
      <tr><td>Example 1</td><td>45</td><td>120</td></tr>
      <tr><td>Comparative</td><td>40</td><td>110</td></tr>
      <tr><td>Example 1</td><td></td><td></td></tr></table></section>""")
    result = Pipeline(tmp_path / "data").ingest("patents", source)
    rows = json.loads(Path(result["artifact_file"]).read_text())["observations"]
    accepted = [r for r in rows if r["review_status"] == "accepted"]
    assert len(accepted) == 4
    comp = [r for r in accepted if r["sample_id"].endswith(":Comparative Example 1")]
    assert len(comp) == 2 and {r["source_row"] for r in comp} == {"5"}
    tensile = [r for r in accepted if r["property"] == "tensile_strength"]
    assert all(
        r["temperature_C"] == 23
        and r["direction"] == "MD"
        and r["source_column"] == "3"
        for r in tensile
    )


def test_explicit_table_material_does_not_infer_unlisted_polymers():
    from che126_data_science.data_mining.patent_html import _table_polymers

    result = _table_polymers(
        [["Description", "PP/PE/PP", "ceramic-coated membrane"]], 2, 1
    )
    assert result[0][0] == "PP/PE/PP"
    assert 1 not in result


def test_aggregation_rejects_mutated_raw_source(tmp_path):
    source = tmp_path / "input.csv"
    source.write_text("property,value,unit\nthickness,12,um\n")
    pipeline = Pipeline(tmp_path / "data")
    pipeline.ingest("manual", source, context={"column_mapping": {}})
    entry = next(iter(pipeline.manifest["documents"].values()))
    Path(entry["document"]["path"]).write_text("corrupted")
    with pytest.raises(ValueError, match="Source file hash mismatch"):
        pipeline.aggregate()


def test_directional_pairs_require_explicit_md_td_label(tmp_path):
    pytest.importorskip("bs4")
    source = tmp_path / "US1234570B2.html"
    source.write_text("""<title>US1234570B2</title><section itemprop="description">
      <div class="description-paragraph" id="p1">Thermal shrinkage was measured after heating the separator at 105 °C for 1 hour.</div>
      <div class="description-paragraph" id="p2">Elongation was measured by a tensile tester.</div>
      <table><tr><td>Property</td><td>Example 1</td></tr>
      <tr><td>Thermal shrinkage (%) MD/TD</td><td>2.5/3.6</td></tr>
      <tr><td>Elongation (%)</td><td>150/170</td></tr></table></section>""")
    result = Pipeline(tmp_path / "data").ingest("patents", source)
    rows = json.loads(Path(result["artifact_file"]).read_text())["observations"]
    accepted = [r for r in rows if r["review_status"] == "accepted"]
    assert {(r["direction"], r["value"]) for r in accepted} == {
        ("MD", 2.5),
        ("TD", 3.6),
    }
    assert all(r["temperature_C"] == 105 and r["duration_min"] == 60 for r in accepted)
    assert all("2.5/3.6" in r["notes"] for r in accepted)
    assert (
        next(r for r in rows if r["property"] == "elongation")["review_status"]
        == "pending"
    )


def test_three_label_columns_keep_split_example_headers(tmp_path):
    pytest.importorskip("bs4")
    source = tmp_path / "US1234571B2.html"
    source.write_text("""<title>US1234571B2</title><section itemprop="description">
    <div class="description-paragraph" id="p1">Porosity was measured using specimen volume and mass.</div>
    <table><tr><td></td><td></td><td></td><td>EXAMPLE</td><td>EXAMPLE</td></tr>
    <tr><td></td><td></td><td></td><td>1</td><td>2</td></tr>
    <tr><td>Separator</td><td>Porosity (%)</td><td>Porosity (%)</td><td>40</td><td>45</td></tr>
    </table></section>""")
    result = Pipeline(tmp_path / "data").ingest("patents", source)
    rows = json.loads(Path(result["artifact_file"]).read_text())["observations"]
    assert len(rows) == 2
    assert {r["sample_id"] for r in rows} == {
        "US1234571B2:Example 1",
        "US1234571B2:Example 2",
    }
    assert all(r["review_status"] == "accepted" for r in rows)
    assert {r["source_column"] for r in rows} == {"4", "5"}


def test_example_headers_align_across_separate_unit_columns(tmp_path):
    pytest.importorskip("bs4")
    source = tmp_path / "US1234572B2.html"
    source.write_text("""<title>US1234572B2</title><section itemprop="description">
    <div class="description-paragraph" id="p1">Porosity was measured using specimen volume and mass.</div>
    <table><tr><td>Microporous membrane properties</td><td>Example 1</td><td>Example 2</td></tr>
    <tr><td>Porosity</td><td>%</td><td>40</td><td>45</td></tr>
    <tr><td>Substrate membrane used</td><td>Example 5</td><td>Example 6</td></tr>
    <tr><td>Porosity</td><td>%</td><td>42</td><td>46</td></tr>
    </table></section>""")
    result = Pipeline(tmp_path / "data").ingest("patents", source)
    rows = json.loads(Path(result["artifact_file"]).read_text())["observations"]
    assert len(rows) == 4
    assert all(r["review_status"] == "accepted" for r in rows)
    assert {r["sample_id"] for r in rows} == {
        "US1234572B2:Example 1",
        "US1234572B2:Example 2",
    }
    assert {r["source_column"] for r in rows} == {"3", "4"}


def test_short_value_rows_do_not_take_last_example_headers(tmp_path):
    pytest.importorskip("bs4")
    source = tmp_path / "US1234573B2.html"
    source.write_text("""<title>US1234573B2</title><section itemprop="description">
    <div class="description-paragraph" id="p1">Porosity was measured using specimen volume and mass.</div>
    <table><tr><td>Property</td><td>Example 1</td><td>Example 2</td><td>Example 3</td><td>Example 4</td></tr>
    <tr><td>Porosity (%)</td><td>40</td><td>45</td></tr>
    </table></section>""")
    result = Pipeline(tmp_path / "data").ingest("patents", source)
    rows = json.loads(Path(result["artifact_file"]).read_text())["observations"]
    assert len(rows) == 2
    assert all(r["quality_flag"] == "unresolved_example_header" for r in rows)
    assert all(r["review_status"] == "pending" for r in rows)
