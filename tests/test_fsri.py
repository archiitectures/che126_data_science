import json
from pathlib import Path

import pytest

from che126_data_science.data_mining.fsri import (
    hfm_reference_thickness_um,
    parse_hfm_results,
)

SNAPSHOT = (
    Path(__file__).resolve().parents[1]
    / "data_mining/fsri_polyethylene_hfm_extract.json"
)


def test_all_source_rows_temperatures_and_repeats_are_preserved():
    data = json.loads(SNAPSHOT.read_text())
    counts = {"conductivity": 0, "heatcapacity": 0}
    temperatures = set()
    for source in data["exports"]:
        if "results_si" not in source:
            continue
        kind = "conductivity" if "conductivity" in source["path"] else "heatcapacity"
        observations = parse_hfm_results(source["results_si"], kind)
        counts[kind] += len(observations)
        temperatures.update(x.temperature_C for x in observations)
        assert [x.table_row for x in observations] == list(
            range(1, len(observations) + 1)
        )
        if kind == "conductivity":
            assert len(observations) == 6
            assert [x.temperature_C for x in observations] == [15.01, 45.01] * 3
        else:
            assert [x.temperature_C for x in observations] == [10, 20.01, 30.01, 40.01]
        assert 3100 <= hfm_reference_thickness_um(source["header"]) <= 3400
    assert counts == {"conductivity": 36, "heatcapacity": 24}
    assert temperatures == {10, 15.01, 20.01, 30.01, 40.01, 45.01}
    first = next(x for x in data["exports"] if "conductivity" in x["path"])
    assert parse_hfm_results(first["results_si"], "conductivity")[0].value == 0.249
    assert hfm_reference_thickness_um(first["header"]) == 3210


@pytest.mark.parametrize(
    "text,kind",
    [
        ("Mean Temp\tSpc Heat\n10\t20\t30", "heatcapacity"),
        ("Mean Temp\tAverage Cond\n15\t0.2", "conductivity"),
        ("Mean Temp\tAverage Cond", "conductivity"),
        ("Mean Temp\tAverage Cond", "unsupported"),
    ],
)
def test_malformed_tables_fail_without_silent_rows(text, kind):
    with pytest.raises(ValueError):
        parse_hfm_results(text, kind)


def test_reference_rows_and_published_csv_preserve_provenance_and_units():
    import csv
    from collections import Counter

    from che126_data_science.data_mining.fsri import polyethylene_reference_rows

    snapshot = json.loads(SNAPSHOT.read_text())
    rows = polyethylene_reference_rows(snapshot)
    assert len(rows) == 60
    assert Counter(r["material"] for r in rows) == {
        "Polyethylene (HDPE)": 30,
        "Polyethylene (LDPE)": 30,
    }
    assert len({r["record_id"] for r in rows}) == 60
    for row in rows:
        assert row["sample_form"] == "bulk_sheet_reference"
        assert snapshot["source_commit"] in row["source_url"]
        assert "data row " in row["source_locator"] and "blob " in row["source_locator"]
        assert not any(
            row.get(field)
            for field in (
                "porosity_pct",
                "tensile_strength_MPa",
                "puncture_strength_N",
                "thickness_um",
                "pore_size_um",
                "electrolyte_composition",
            )
        )
        if "volumetric_heat_capacity_J_m3_K" in row:
            assert (
                abs(
                    row["specific_heat_capacity_J_kg_K"]
                    * row["reference_density_kg_m3"]
                    - row["volumetric_heat_capacity_J_m3_K"]
                )
                < 0.5
            )
            assert row["value_type"] == "measured_and_calculated"
            assert "mean-density inputs:" in row["source_locator"]
    root = SNAPSHOT.parents[1]
    with (root / "datasets/dry_separators.csv").open() as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        published = list(reader)
    with (root / "datasets/wet_separators.csv").open() as f:
        wet = csv.DictReader(f)
        assert wet.fieldnames == headers
        assert list(wet) == []
    assert len(headers) == 35
    assert len(published) == len(rows)
    numeric = {
        "temperature_C",
        "reference_thickness_um",
        "thermal_conductivity_W_m_K",
        "volumetric_heat_capacity_J_m3_K",
        "specific_heat_capacity_J_kg_K",
        "reference_density_kg_m3",
    }
    for original, saved in zip(rows, published, strict=True):
        for key in headers:
            if key in numeric and saved[key]:
                assert float(saved[key]) == original[key]
            else:
                assert saved[key] == str(original.get(key, ""))
