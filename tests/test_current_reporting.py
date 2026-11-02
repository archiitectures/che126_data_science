"""Current audits keep unknown conditions unknown and exclude bulk from separator grids."""

import csv

from che126_data_science.data_science.reporting import gap_status, refresh


def test_temperature_event_and_standard_are_not_numeric_test_conditions():
    assert (
        gap_status({"property": "melting_temperature", "method": "DSC at 130 C"})
        == "temperature_is_response_value_not_test_condition"
    )
    assert (
        gap_status({"property": "tensile_strength", "method": "ASTM D882"})
        == "standard_cited_without_explicit_test_temperature"
    )


def test_coverage_is_current_repeatable_and_scope_specific(tmp_path):
    columns = ["unique_point_id", "observation_id", "sample_id", "property", "polymer", "source_url", "source_file", "source_sha256", "source_table", "source_row", "source_column", "material_identity_status", "material_identity_evidence", "material_identity_reason", "manufacturer", "product", "sample_form", "temperature_C", "temperature_role", "method"]
    base = dict.fromkeys(columns, "")
    rows = [
        {
            **base,
            "unique_point_id": "known",
            "property": "thickness",
            "polymer": "PE",
            "sample_form": "separator",
            "temperature_C": "25",
            "temperature_role": "measurement",
        },
        {
            **base,
            "unique_point_id": "unknown",
            "property": "thickness",
            "polymer": "PE",
            "sample_form": "separator",
            "method": "ASTM D374",
        },
        {
            **base,
            "unique_point_id": "bulk",
            "property": "thickness",
            "polymer": "PE",
            "sample_form": "bulk_reference",
            "temperature_C": "90",
            "temperature_role": "measurement",
        },
    ]
    data = tmp_path / "datasets"
    data.mkdir()
    with (data / "unique_points.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    summary = refresh(tmp_path)
    assert summary["numeric_temperature_points"] == 2
    grid = list(csv.DictReader((data / "separator_type_property_coverage.csv").open()))
    assert len(grid) == 1 and grid[0]["distinct_points"] == "2"
    assert grid[0]["temperatures_C"] == "25"
    before = {p.name: p.read_bytes() for p in data.iterdir()}
    refresh(tmp_path)
    assert all(
        (data / name).read_bytes() == payload for name, payload in before.items()
    )
