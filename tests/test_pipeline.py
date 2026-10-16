"""Real-source regressions and deterministic offline pipeline contracts."""

import csv
import hashlib
import io
import json
from pathlib import Path
from unittest.mock import Mock
from urllib.error import HTTPError

import pytest

from che126_data_science.data_mining.acquisition import (
    DocumentStore,
    HTTPClient,
    robots_allowed,
)
from che126_data_science.data_mining.discovery import BigQueryBudget, EPOClient
from che126_data_science.data_mining.normalization import conditions, values
from che126_data_science.data_mining.pipeline import Pipeline

FIXTURES = Path(__file__).parent / "fixtures/pipeline"
ROOT = Path(__file__).parents[1]


def pipeline(tmp_path):
    pytest.importorskip("pyarrow")
    return Pipeline(tmp_path / "data")


def artifact(result):
    return json.loads(Path(result["artifact_file"]).read_text())


def test_pp1611_all_twelve_values_and_paired_statistics(tmp_path):
    pytest.importorskip("pymupdf")
    p = pipeline(tmp_path)
    result = p.ingest("celgard", FIXTURES / "pp1611.pdf")
    assert (result["accepted"], result["review"]) == (8, 4)
    rows = artifact(result)["observations"]
    tensile = [r for r in rows if r["property"] == "tensile_strength"]
    assert sorted(float(r["original_value"]) for r in tensile) == [110, 125, 1560, 1680]
    assert all(r["review_status"] == "pending" and r["unit"] is None for r in tensile)
    assert {r["original_unit"] for r in tensile} == {"Kg/cm2"}
    shrink = [r for r in rows if r["property"] == "thermal_shrinkage"]
    assert sorted((r["direction"], r["statistic"], r["value"]) for r in shrink) == [
        ("MD", "maximum", 2.2),
        ("MD", "typical", 1.0),
        ("TD", "typical", 0),
    ]
    assert all(
        r["temperature_C"] == 105
        and r["temperature_role"] == "exposure"
        and r["duration_min"] == 60
        for r in shrink
    )
    assert all(r["temperature_C"] is None for r in rows if r not in shrink)
    assert all(
        r["electrolyte_state"] == "not_reported"
        and r["source_page"] == 1
        and len(r["source_sha256"]) == 64
        for r in rows
    )
    assert (
        next(r for r in rows if r["property"] == "porosity")["record_type"]
        == "calculated"
    )
    puncture = [r for r in rows if r["property"] == "puncture_force"]
    assert next(r for r in puncture if r["statistic"] == "minimum")[
        "value"
    ] == pytest.approx(200 * 0.00980665)


def test_second_celgard_layout_geometry(tmp_path):
    pytest.importorskip("pymupdf")
    result = pipeline(tmp_path).ingest("celgard", FIXTURES / "z1831.pdf")
    rows = artifact(result)["observations"]
    assert rows
    assert next(r for r in rows if r["property"] == "thickness")["value"] == 18
    assert next(r for r in rows if r["property"] == "porosity")["value"] == 77
    assert all(r["source_page"] == 1 for r in rows)


def test_verified_patent_headers_and_test_context(tmp_path):
    pytest.importorskip("bs4")
    result = pipeline(tmp_path).ingest("patents", FIXTURES / "US9911958B2.html")
    rows = artifact(result)["observations"]
    shrink = [r for r in rows if r["property"] == "thermal_shrinkage"]
    assert len(shrink) == 12
    expected = {
        130: [2.5, 25, 8.5, 12.5],
        140: [5, 72.5, 57.5, 62.5],
        170: [5, 80, 57.5, 68],
    }
    samples = [
        "Example 1",
        "Comparative Example 1",
        "Comparative Example 2",
        "Comparative Example 3",
    ]
    for temp, vs in expected.items():
        for sample, value in zip(samples, vs, strict=True):
            row = next(
                r
                for r in shrink
                if r["sample_id"].endswith(":" + sample) and r["temperature_C"] == temp
            )
            assert row["value"] == value and row["duration_min"] == 10
            assert row["temperature_role"] == "exposure"
            assert (
                row["record_type"] == "measured" and row["direction"] == "unspecified"
            )
            assert row["shrinkage_basis"] == "length"
    assert len([r for r in rows if r["property"] == "thickness"]) == 4
    assert all(r["property"] not in {"discharge_capacity", "hot_box"} for r in rows)


def test_text_table_and_ambiguous_protocol_queue(tmp_path):
    pytest.importorskip("bs4")
    html = tmp_path / "text.html"
    html.write_text(
        '<title>US1234567B2</title><section itemprop="description"><pre>Property  Example 1  Control 1\nThickness (um)  12  9</pre></section>'
    )
    result = pipeline(tmp_path).ingest("patents", html)
    rows = artifact(result)["observations"]
    assert len(rows) == 2 and all(r["value"] in {9, 12} for r in rows)
    assert all(r["extraction_method"] == "patent_text_table" for r in rows)


def test_pinned_fsri_repeats_density_and_provenance(tmp_path):
    result = pipeline(tmp_path).ingest(
        "fsri", ROOT / "data_mining/fsri_polyethylene_hfm_extract.json"
    )
    rows = artifact(result)["observations"]
    assert len(rows) == 66  # 60 thermal observations + six density replicates
    assert len({r["observation_id"] for r in rows}) == 66
    assert len([r for r in rows if r["property"] == "volumetric_heat_capacity"]) == 24
    assert all(r["sample_form"] == "bulk_reference" for r in rows)
    assert all(r["electrolyte_state"] == "not_reported" for r in rows)
    assert all(r["temperature_C"] is None for r in rows if r["property"] == "density")


def test_utf16_complete_hfm_file(tmp_path):
    path = tmp_path / "PP_HFM_Wet_conductivity_R1.tst"
    path.write_bytes(
        (
            "Instrument header\nResults Table -- SI Units\nMean Temp\tUpper Cond\tLower Cond\tAverage Cond\n15\t0.2\t0.2\t0.2\n15\t0.21\t0.21\t0.21\n"
        ).encode("utf-16")
    )
    result = pipeline(tmp_path).ingest("fsri", path)
    rows = artifact(result)["observations"]
    assert len(rows) == 2 and rows[0]["replicate_id"] == "R1"
    assert {r["value"] for r in rows} == {0.2, 0.21}


def test_idempotent_rebuild_and_changed_source(tmp_path):
    p = pipeline(tmp_path)
    path = tmp_path / "manual.csv"
    path.write_text(
        "sample_id,property,value,unit,record_type\na,thickness,12,um,measured\n"
    )
    first = p.ingest("manual", path)
    p.aggregate()
    files = [
        p.root / "processed" / name
        for name in ["master_observations.csv", "master_observations.parquet"]
    ]
    previous = [x.read_bytes() for x in files]
    second = p.ingest("manual", path)
    p.aggregate()
    assert first == second
    assert previous == [x.read_bytes() for x in files]
    assert len(p.manifest["documents"]) == 1
    path.write_text(
        "sample_id,property,value,unit,record_type\na,thickness,16,um,measured\n"
    )
    changed = p.ingest("manual", path)
    assert changed["artifact_file"] != first["artifact_file"]
    assert p.aggregate()["accepted"] == 1
    rows = list(csv.DictReader(files[0].open()))
    assert float(rows[0]["value"]) == 16


def test_measured_only_and_parquet_types(tmp_path):
    import pyarrow.parquet as pq

    p = pipeline(tmp_path)
    path = tmp_path / "values.csv"
    path.write_text(
        "sample_id,property,value,unit,record_type,statistic\na,thickness,12,um,measured,reported\nb,thickness,15,um,spec_limit,maximum\n"
    )
    p.ingest("manual", path)
    assert p.aggregate(measured_only=True)["accepted"] == 1
    table = pq.read_table(p.root / "processed/master_observations.parquet")
    assert table["value"].to_pylist() == [12]
    assert table["temperature_C"].to_pylist() == [None]


def test_manual_permission_and_unreported_temperature(tmp_path):
    p = pipeline(tmp_path)
    path = tmp_path / "nims.tsv"
    path.write_text("sample_id\tproperty\tvalue\tunit\nx\tthickness\t0.02\tmm\n")
    with pytest.raises(PermissionError):
        p.ingest("polyinfo", path)
    r = p.ingest(
        "polyinfo",
        path,
        context={
            "authorized": True,
            "restrictions": "Personal research only; do not redistribute",
        },
    )
    row = artifact(r)["observations"][0]
    assert row["value"] == 20 and row["temperature_C"] is None
    assert row["source_restrictions"].startswith("Personal")
    with pytest.raises(PermissionError):
        p.ingest(
            "polyinfo",
            "https://polymer.nims.go.jp/data.csv",
            context={"authorized": True, "restrictions": "test"},
        )


def test_robots_longest_rule_and_query_disallowed():
    rules = "User-agent: *\nDisallow: /*\nAllow: /$\nAllow: /patent/\n"
    assert robots_allowed(rules, "https://patents.google.com/patent/US9911958B2/en")
    assert not robots_allowed(rules, "https://patents.google.com/?q=separator")
    assert robots_allowed(rules, "https://patents.google.com/")


def response(data=b"body", url="https://api.github.com/test", headers=None):
    r = io.BytesIO(data)
    r.url = url
    r.headers = headers or {}
    return r


def test_http_retry_limits_and_no_retry_auth():
    opener = Mock(
        side_effect=[
            HTTPError(
                "https://api.github.com/test", 429, "slow", {"Retry-After": "1"}, None
            ),
            response(),
        ]
    )
    sleep = Mock()
    http = HTTPClient(opener=opener, sleep=sleep, interval=0)
    assert http.request("https://api.github.com/test")[0] == b"body"
    assert opener.call_count == 2
    opener.reset_mock(side_effect=True)
    opener.side_effect = HTTPError("https://api.github.com/test", 401, "auth", {}, None)
    with pytest.raises(HTTPError):
        http.request("https://api.github.com/test")
    assert opener.call_count == 1


def test_document_cache_offline_refresh_and_integrity(tmp_path):
    http = Mock()
    http.request.return_value = (
        b"original",
        {"ETag": "v1"},
        "https://example.org/a.csv",
    )
    store = DocumentStore(tmp_path, http=http)
    a = store.fetch("manual", "https://example.org/a.csv")
    store.fetch("manual", "https://example.org/a.csv")
    assert http.request.call_count == 1
    http.request.side_effect = HTTPError(
        "https://example.org/a.csv", 304, "same", {}, None
    )
    assert store.fetch("manual", "https://example.org/a.csv", refresh=True) == a
    assert http.request.call_args.kwargs["headers"]["If-None-Match"] == "v1"
    Path(a.path).write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="hash"):
        store.fetch("manual", "https://example.org/a.csv")


def test_epo_credentials_and_xml_result():
    with pytest.raises(ValueError, match="EPO_OPS_KEY"):
        EPOClient(key="", secret="").search(["PE"])
    http = Mock()
    http.request.side_effect = [
        (b'{"access_token":"secret","expires_in":1000}', {}, ""),
        (
            b'<root xmlns:e="http://www.epo.org/exchange"><e:exchange-document country="US" doc-number="9911958" kind="B2" family-id="f"/></root>',
            {},
            "",
        ),
    ]
    result = EPOClient(key="key", secret="secret", http=http).search(["PE"])
    assert result[0]["publication_number"] == "US9911958B2"
    assert result[0]["family_id"] == "f"


def test_budget_is_cumulative_and_uncertain_failures_consume_reservation():
    client = Mock()
    client.search.side_effect = [
        Mock(bytes_processed=20_000_000),
        Mock(bytes_billed=20_000_000, job_id="a"),
        Mock(bytes_processed=20_000_000),
        RuntimeError("timeout"),
    ]
    budget = BigQueryBudget(client, usd="0.001", usd_per_tib="6.25")
    budget.search(["PE"])
    with pytest.raises(RuntimeError):
        budget.search(["PP"])
    assert budget.spent_bytes > 40_000_000
    assert budget.summary()["jobs"][-1]["status"] == "uncertain_failure"
    client.search.side_effect = None
    client.search.return_value = Mock(bytes_processed=10**12)
    with pytest.raises(ValueError, match="estimate"):
        budget.search(["PE"])


@pytest.mark.parametrize(
    "text,expected",
    [
        (
            "105°C / 1 Hour",
            {"temperature_C": 105, "temperature_role": "exposure", "duration_min": 60},
        ),
        (
            "378.15 K / 600 seconds",
            {"temperature_C": 105, "temperature_role": "exposure", "duration_min": 10},
        ),
    ],
)
def test_temperature_and_duration(text, expected):
    assert conditions(text) == expected


def test_unlabelled_pairs_do_not_become_typical_and_maximum():
    assert values("1 / 2", "ambiguous") == [("1 / 2", "reported")]


def test_family_dedup_keeps_alias_provenance(tmp_path):
    p = pipeline(tmp_path)
    source = FIXTURES / "US9911958B2.html"
    p.ingest(
        "patents",
        source,
        context={"publication_number": "US1111111B2", "family_id": "verified-family"},
    )
    p.ingest(
        "patents",
        source,
        context={"publication_number": "US2222222A1", "family_id": "verified-family"},
    )
    assert p.aggregate()["accepted"] == 16
    assert len(p.manifest["duplicates"]) == 16
    assert all(
        a["also_reported_as"] != a["observation_id"] for a in p.manifest["duplicates"]
    )


def test_missing_family_does_not_merge_publications(tmp_path):
    p = pipeline(tmp_path)
    for number in ["US1111111B2", "US2222222A1"]:
        p.ingest(
            "patents",
            FIXTURES / "US9911958B2.html",
            context={"publication_number": number},
        )
    assert p.aggregate()["accepted"] == 32


def test_collect_cached_discovery_does_not_require_second_network_call(
    tmp_path, monkeypatch
):
    p = pipeline(tmp_path)
    search = Mock(return_value=[])
    monkeypatch.setattr(EPOClient, "search", search)
    p.collect(sources=["patents"], max_documents=1)
    p.collect(sources=["patents"], max_documents=1)
    assert search.call_count == 1


def test_invalid_physical_value_goes_to_review_without_losing_good_rows(tmp_path):
    p = pipeline(tmp_path)
    path = tmp_path / "mixed.csv"
    path.write_text(
        "sample_id,property,value,unit\na,porosity,49,%\nb,porosity,101,%\n"
    )
    result = p.ingest("manual", path)
    assert result["accepted"] == 1 and result["review"] == 1
    assert artifact(result)["observations"][1]["quality_flag"] == "validation_failed"


def test_xlsx_permissioned_import_with_explicit_mapping(tmp_path):
    from openpyxl import Workbook

    p = pipeline(tmp_path)
    path = tmp_path / "values.xlsx"
    book = Workbook()
    sheet = book.active
    sheet.append(["Specimen", "Property", "Number", "Units"])
    sheet.append(["PE1", "thickness", 25, "um"])
    book.save(path)
    result = p.ingest(
        "polyinfo",
        path,
        context={
            "authorized": True,
            "restrictions": "private use",
            "columns": {
                "Specimen": "sample_id",
                "Property": "property",
                "Number": "value",
                "Units": "unit",
            },
        },
    )
    assert artifact(result)["observations"][0]["value"] == 25


def test_legacy_rows_require_primary_source_review(tmp_path):
    p = pipeline(tmp_path)
    result = p.ingest(
        "manual", ROOT / "data_mining/examples/celgard_2400_observations.csv"
    )
    assert result["accepted"] == 0 and result["review"] == 8
    assert all(
        r["source_url"].startswith("https://www.celgard.com")
        for r in artifact(result)["observations"]
    )


def test_rate_is_not_absolute_temperature():
    assert conditions("heating rate 10 K/min") == {"heating_rate_C_min": 10}
    assert (
        conditions("heating rate 10 C/min; exposure 120 C for 60 min")["temperature_C"]
        == 120
    )


def test_source_hash_calibration_and_real_curve_qc(tmp_path):
    pytest.importorskip("numpy")
    from che126_data_science.data_mining.digitize import digitize

    result = digitize(
        FIXTURES / "patent_tma.png",
        FIXTURES / "tma_calibration.json",
        tmp_path / "graph",
    )
    assert result["points"] >= 30
    assert result["metrics"]["max_error_y"] < 2
    assert result["metrics"]["reference_count"] == 5
    assert result["curve_count"] == 1
    assert result["status"] == "review"  # ambiguous columns remain explicitly flagged
    points = list(csv.DictReader((tmp_path / "graph/curve_points.csv").open()))
    assert len({r["curve_id"] for r in points}) == 1
    config = json.loads((FIXTURES / "tma_calibration.json").read_text())
    config["source_sha256"] = "wrong"
    with pytest.raises(ValueError, match="hash"):
        digitize(FIXTURES / "patent_tma.png", config, tmp_path / "bad")


def test_synthetic_linear_calibration_and_multiseries_review(tmp_path):
    import numpy as np
    from PIL import Image

    from che126_data_science.data_mining.digitize import digitize

    path = tmp_path / "curve.png"
    pixels = np.full((100, 100, 3), 255, dtype=np.uint8)
    for x in range(10, 90):
        pixels[99 - x, x] = 0
    Image.fromarray(pixels).save(path)
    config = {
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "crop": [10, 10, 90, 90],
        "x_reference": [[0, 0], [99, 99]],
        "y_reference": [[99, 0], [0, 99]],
        "x_unit": "C",
        "y_unit": "%",
        "plot_type": "linear",
        "single_series": True,
        "series_label": "test",
        "sample_step_px": 1,
        "reference_points": [[20, 20], [40, 40], [60, 60]],
        "tolerances": {"max_error_y": 0.01, "max_error_x": 0.01},
    }
    result = digitize(path, config, tmp_path / "good")
    assert result["status"] == "accepted" and result["metrics"]["max_error_y"] == 0
    config["series_count"] = 2
    result = digitize(path, config, tmp_path / "review")
    assert result["status"] == "review" and result["points"] == 0


def test_cli_outputs_clean_json_and_preserves_old_commands(tmp_path):
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "che126_data_science",
            "ingest",
            "--source",
            "celgard",
            "--input",
            str(FIXTURES / "pp1611.pdf"),
            "--data-dir",
            str(tmp_path / "cli"),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout)["outputs"]["accepted"] == 8
    result = subprocess.run(
        [sys.executable, "-m", "che126_data_science", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert all(
        command in result.stdout
        for command in [
            "patents",
            "fsri-hfm",
            "clean",
            "ingest",
            "collect",
            "aggregate",
            "digitize",
        ]
    )


def test_empty_exports_have_stable_parquet_schema(tmp_path):
    import pyarrow.parquet as pq

    p = pipeline(tmp_path)
    assert p.aggregate()["accepted"] == 0
    table = pq.read_table(p.root / "processed/master_observations.parquet")
    assert table.num_rows == 0 and str(table.schema.field("value").type) == "double"


def test_snapshot_and_raw_hfm_are_linked_not_counted_twice(tmp_path):
    p = pipeline(tmp_path)
    p.ingest("fsri", ROOT / "data_mining/fsri_polyethylene_hfm_extract.json")
    snapshot = json.loads(
        (ROOT / "data_mining/fsri_polyethylene_hfm_extract.json").read_text()
    )
    entry = next(e for e in snapshot["exports"] if "results_si" in e)
    path = tmp_path / Path(entry["path"]).name
    path.write_bytes(
        ("Results Table -- SI Units\n" + entry["results_si"]).encode("utf-16")
    )
    p.ingest("fsri", path)
    assert p.aggregate()["accepted"] == 66
    assert len(p.manifest["duplicates"]) == 6


def test_aggregate_reextracts_stale_artifacts_without_network(tmp_path):
    p = pipeline(tmp_path)
    path = tmp_path / "manual.csv"
    path.write_text("sample_id,property,value,unit\na,thickness,12,um\n")
    result = p.ingest("manual", path)
    saved = artifact(result)
    saved["extraction_version"] = "old-parser"
    Path(result["artifact_file"]).write_text(json.dumps(saved))
    p.store.http.request = Mock(side_effect=AssertionError("network during rebuild"))
    # Remove the stale cache at the current key to simulate a versioned rebuild.
    entry = next(iter(p.manifest["documents"].values()))
    old = Path(entry["artifact_file"])
    old.rename(old.with_suffix(".old.json"))
    entry["artifact_file"] = str(old.with_suffix(".old.json"))
    p._save()
    assert p.aggregate()["accepted"] == 1
    p.store.http.request.assert_not_called()
