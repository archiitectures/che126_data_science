import csv
import io
import json
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

import pytest

from che126_data_science.data_mining.celgard import parse_datasheet
from che126_data_science.data_mining.fsri import hfm_observations
from che126_data_science.data_mining.sources import (
    discover_celgard,
    discover_fsri,
    matches_material,
    polyinfo_plan,
    read_url,
    save_download,
)
from che126_data_science.data_science.observations import (
    Observation,
    coverage,
    read_observations,
    write_observations,
)

ROOT = Path(__file__).resolve().parents[1]


def observation(**changes):
    values = {
        "record_id": "r1",
        "sample_id": "sample1",
        "material": "PP",
        "property": "porosity",
        "value": 41,
        "unit": "%",
        "source_url": "https://example.org/data",
        "source_locator": "table 1 row 1",
        "sample_form": "separator",
        "temperature_C": 25,
        "temperature_role": "measurement",
    }
    return Observation(**(values | changes))


@pytest.mark.parametrize(
    "changes",
    [
        {"value": float("nan")},
        {"value": float("inf")},
        {"value": 101},
        {"unit": "fraction"},
        {"state": "wet"},
        {"temperature_C": -274},
        {"temperature_C": None},
        {"temperature_role": "processing"},
        {"source_locator": ""},
        {"property": "fictional"},
    ],
)
def test_reject_invalid_measurements(changes):
    with pytest.raises(ValueError):
        observation(**changes)


def test_csv_roundtrip_duplicates_and_unit_conversion(tmp_path):
    raw = tmp_path / "raw.csv"
    row = asdict(observation(property="thickness", value=0.025, unit="um"))
    row.update(unit="mm")
    with raw.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=row)
        writer.writeheader()
        writer.writerows([row, row, row | {"record_id": "replicate2"}])
    rows = read_observations(raw)
    assert len(rows) == 2
    assert rows[0].value == 25
    assert rows[0].raw_unit == "mm"
    output = tmp_path / "clean.csv"
    write_observations(rows, output)
    assert read_observations(output) == rows
    with pytest.raises(FileExistsError):
        write_observations(rows, output)
    with raw.open("a", newline="") as stream:
        csv.DictWriter(stream, fieldnames=row).writerow(row | {"value": "0.030"})
    with pytest.raises(ValueError, match="Conflicting record_id"):
        read_observations(raw)


def test_coverage_never_pools_conditions_or_imputes_temperatures():
    rows = [
        observation(),
        observation(
            record_id="r2",
            property="thickness",
            unit="um",
            value=25,
            temperature_C=None,
            temperature_role="unknown",
        ),
        observation(record_id="r3", temperature_role="exposure"),
        observation(record_id="r4", sample_id="other", value_type="claim"),
    ]
    report = coverage(rows, ["porosity", "thickness"], [25, 60])
    assert report["unknown_temperature_count"] == 1
    group = next(
        g
        for g in report["groups"]
        if g["sample_id"] == "sample1" and g["temperature_role"] == "measurement"
    )
    assert [c["status"] for c in group["cells"]] == [
        "reported",
        "missing",
        "missing",
        "missing",
    ]
    assert all(
        c["status"] == "missing"
        for g in report["groups"]
        if g["sample_id"] == "other"
        for c in g["cells"]
    )
    near = coverage(
        [observation(temperature_C=25.01)], ["porosity"], [25], tolerance=0.02
    )
    assert near["groups"][0]["cells"][0]["reported_temperatures_C"] == [25.01]


def test_celgard_real_table_preserves_bounds_exposure_and_unresolved_units():
    text = (ROOT / "tests/fixtures/celgard_2400.txt").read_text()
    result = parse_datasheet(
        text,
        product="2400",
        material="PP",
        source_url="https://www.celgard.com/storage/components/2400_com_data_2026-01.pdf",
    )
    rows = result["observations"]
    assert len(rows) == 8
    assert {r.value_type for r in rows} == {
        "typical",
        "calculated",
        "maximum",
        "minimum",
    }
    puncture = [r for r in rows if r.property == "puncture_force"]
    assert puncture[0].value == pytest.approx(4.4129925)
    assert all(
        r.temperature_C is None for r in rows if r.property != "thermal_shrinkage"
    )
    assert all(
        r.temperature_role == "exposure" and r.temperature_C == 105
        for r in rows
        if r.property == "thermal_shrinkage"
    )
    assert len(result["unresolved"]) == 2  # Kg/cm2 cannot silently become kgf/cm2
    with pytest.raises(ValueError, match="layout"):
        parse_datasheet(
            "changed layout",
            product="2400",
            material="PP",
            source_url="https://example.org",
        )


def test_celgard_discovery_and_material_boundaries():
    html = '<div class="ds-item"><div class="ds-info"><div>Celgard 2325</div><p>PP/PE/PP trilayer</p></div><a href="/storage/components/2325.pdf">Download</a></div>'
    docs = discover_celgard("polyethylene", html=html)
    assert len(docs) == 1
    assert docs[0].url == "https://www.celgard.com/storage/components/2325.pdf"
    assert not matches_material("properties supplied", "PE")
    assert not matches_material("polyethylene terephthalate PET", "polyethylene")
    assert not matches_material("LDPE", "HDPE")
    assert discover_celgard("PTFE", html=html) == []
    with pytest.raises(ValueError, match="layout"):
        discover_celgard("PE", html="broken")


def test_fsri_pagination_and_filtering():
    pages = [
        b'<a href="/materialdetail/high-density-polyethylene-hdpe">HDPE</a><a href="/search?search%5Bsearch_text%5D=polyethylene&amp;page=2">Next</a>',
        b'<a href="/materialdetail/low-density-polyethylene-ldpe">LDPE</a><a href="/materialdetail/polyethylene-terephthalate-pet">PET</a>',
    ]
    with patch(
        "che126_data_science.data_mining.sources.read_url", side_effect=pages
    ) as read:
        docs = discover_fsri("polyethylene")
    assert len(docs) == 2
    assert read.call_count == 2


def test_hfm_normalizes_every_original_result():
    snapshot = json.loads(
        (ROOT / "data_mining/fsri_polyethylene_hfm_extract.json").read_text()
    )
    rows = hfm_observations(snapshot)
    assert len(rows) == 60
    assert len({r.record_id for r in rows}) == 60
    assert {r.material for r in rows} == {"HDPE", "LDPE"}
    assert {r.temperature_C for r in rows} == {10, 15.01, 20.01, 30.01, 40.01, 45.01}
    assert all(r.sample_form == "bulk_reference" and r.state == "unknown" for r in rows)
    assert len([r for r in rows if r.property == "volumetric_heat_capacity"]) == 24


def test_polyinfo_makes_no_requests():
    with patch("che126_data_science.data_mining.sources.read_url") as read:
        plan = polyinfo_plan("polyethylene", ["porosity"], [25, 100])
    read.assert_not_called()
    assert "HDPE" in plan["material_terms"]


def test_download_hash_receipt_and_no_overwrite(tmp_path):
    with patch(
        "che126_data_science.data_mining.sources.read_url", return_value=b"original"
    ):
        receipt = save_download("https://example.org/a.pdf", tmp_path)
        assert Path(receipt["path"]).read_bytes() == b"original"
        save_download("https://example.org/a.pdf", tmp_path)
        assert len(list(tmp_path.glob("*.json"))) == 2
        Path(receipt["path"]).write_bytes(b"corrupt")
        with pytest.raises(ValueError, match="hash"):
            save_download("https://example.org/a.pdf", tmp_path)


def test_download_limit():
    response = io.BytesIO(b"012345")
    response.url = "https://example.org"
    with (
        patch("che126_data_science.data_mining.sources.urlopen", return_value=response),
        pytest.raises(ValueError, match="exceeds"),
    ):
        read_url("https://example.org", max_bytes=5)
    with pytest.raises(ValueError, match="HTTPS"):
        read_url("http://example.org")


def test_fsri_embedded_json_preserves_axes_and_rejects_javascript():
    from che126_data_science.data_mining.fsri import extract_public_curves

    html = 'Plotly.newPlot("id", [{"x":[10,20],"y":[1,2],"name":"Wet","error_y":{"array":[0.1,0.2]}}], {"xaxis":{"title":{"text":"Temperature (C)"}},"yaxis":{"title":{"text":"Heat capacity"}}}, {})'
    curve = extract_public_curves(html)[0]
    assert curve["traces"][0]["x"] == [10, 20]
    assert curve["traces"][0]["error_y"]["array"] == [0.1, 0.2]
    assert curve["xaxis"]["title"]["text"] == "Temperature (C)"
    with pytest.raises(ValueError, match="Unsupported"):
        extract_public_curves('Plotly.newPlot("id", malicious(), {})')


def test_empty_csv_still_requires_schema(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("record_id,value\n")
    with pytest.raises(ValueError, match="Missing required"):
        read_observations(path)


def test_transition_temperature_cannot_be_below_absolute_zero():
    with pytest.raises(ValueError, match="absolute zero"):
        observation(property="melting_temperature", unit="C", value=-300)


def test_celgard_product_identity_must_match_source():
    text = (ROOT / "tests/fixtures/celgard_2400.txt").read_text()
    with pytest.raises(ValueError, match="identity"):
        parse_datasheet(
            text, product="2325", material="PE/PP", source_url="https://example.org"
        )


def test_celgard_excludes_other_pages_and_keeps_page_locator():
    text = (ROOT / "tests/fixtures/celgard_2400.txt").read_text()
    result = parse_datasheet(
        "Cover\f" + text + "\fWarranty and contact information",
        product="2400",
        material="PP",
        source_url="https://example.org",
    )
    assert len(result["observations"]) == 8
    assert len(result["unresolved"]) == 2
    assert all("PDF page 2;" in r.source_locator for r in result["observations"])
