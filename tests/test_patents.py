"""Offline contract checks: real SDK parameters, injected network boundary."""

import json
import subprocess
import sys
from unittest.mock import Mock, patch

import pytest

from che126_data_science.data_mining import (
    GooglePatentsClient,
    PatentResults,
    QueryEstimate,
    export_json,
    patents,
)


@pytest.fixture
def backend():
    client = Mock()
    client.query.return_value.result.return_value = []
    client.query.return_value.total_bytes_processed = 123456
    return client


def test_full_text_search_is_parameterized_and_bounded(backend):
    term = "separator%' OR TRUE --"
    result = GooglePatentsClient(client=backend).search(
        [term, "porosity"],
        countries=["us"],
        limit=7,
        maximum_bytes_billed=1000,
    )
    sql = backend.query.call_args.args[0]
    config = backend.query.call_args.kwargs["job_config"]
    assert term not in sql
    assert "STRPOS(LOWER(txt.text), LOWER(term))" in sql  # no SQL LIKE wildcards
    assert "NOT EXISTS" in sql  # every term required
    for field in patents.TEXT_FIELDS:
        assert f"UNNEST(p.{field}_localized)" in sql
    assert "ORDER BY p.publication_date DESC, p.publication_number ASC" in sql
    params = {p.name: p for p in config.query_parameters}
    assert list(params["terms"].values) == [term, "porosity"]
    assert list(params["countries"].values) == ["US"]
    assert params["limit"].value == 7
    assert config.maximum_bytes_billed == 1000
    assert isinstance(result, PatentResults)
    assert result.query["countries"] == ("US",)
    assert backend.query.call_args.kwargs["timeout"] == 120
    backend.query.return_value.result.assert_called_once_with(timeout=120)


def test_selected_fields_and_dry_run_do_not_fetch_rows(backend):
    client = GooglePatentsClient(client=backend)
    estimate = client.search(
        ["battery"],
        fields=["title", "abstract"],
        maximum_bytes_billed=100,
        dry_run=True,
    )
    assert estimate == QueryEstimate(123456, 100)
    sql = backend.query.call_args.args[0]
    assert "UNNEST(p.claims_localized)" not in sql
    config = backend.query.call_args.kwargs["job_config"]
    assert config.dry_run and not config.use_query_cache
    backend.query.return_value.result.assert_not_called()
    assert (
        client.get_publication("US-123-A1", maximum_bytes_billed=100, dry_run=True)
        == estimate
    )
    backend.query.return_value.result.assert_not_called()


def test_publication_preserves_localization_missing_values_and_provenance(
    backend, tmp_path
):
    backend.query.return_value.result.return_value = [
        {
            "publication_number": "US-123-A1",
            "family_id": "456",
            "country_code": "US",
            "publication_date": 20200102,
            "title_localized": [
                {"language": "en", "text": "Separator"},
                {"language": "de", "text": "Membran"},
            ],
            "abstract_localized": None,
            "claims_localized": [{"language": "en", "text": "Claim text"}],
            "assignee_harmonized": [{"name": "Example"}, {"name": None}],
            "cpc": [{"code": "H01M50/40"}],
        }
    ]
    result = GooglePatentsClient(client=backend).get_publication(
        "US-123-A1",
        maximum_bytes_billed=1000,
    )
    config = backend.query.call_args.kwargs["job_config"]
    assert config.query_parameters[0].value == "US-123-A1"
    assert (
        "WHERE publication_number = @publication_number"
        in backend.query.call_args.args[0]
    )
    record = result.records[0]
    assert record.publication_date == "2020-01-02"
    assert [x.language for x in record.title] == ["en", "de"]
    assert record.abstract == record.description == ()
    assert record.claims[0].text == "Claim text"
    assert record.assignees == ("Example",)
    assert record.classifications == ("H01M50/40",)
    export_json(result, tmp_path / "patents.json")
    data = json.loads((tmp_path / "patents.json").read_text())
    assert data["source_table"] == patents.TABLE
    assert data["query"]["publication_number"] == "US-123-A1"
    assert data["retrieved_at"].endswith("+00:00")
    assert data["records"][0]["url"] == "https://patents.google.com/patent/US123A1"


@pytest.mark.parametrize("date", [None, 0, 20200000, 20200230])
def test_unknown_dates_are_not_invented(date):
    assert (
        patents._record(
            {"publication_number": "US-123-A1", "publication_date": date}
        ).publication_date
        is None
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"terms": []},
        {"terms": "battery"},
        {"terms": [" "]},
        {"fields": ["title); DROP TABLE x"]},
        {"fields": []},
        {"countries": "US"},
        {"countries": ["USA"]},
        {"limit": 0},
        {"limit": True},
        {"maximum_bytes_billed": -1},
        {"maximum_bytes_billed": True},
    ],
)
def test_bad_inputs_do_not_send_queries(backend, kwargs):
    args = {"terms": ["battery"], "maximum_bytes_billed": 100}
    args.update(kwargs)
    with pytest.raises(ValueError):
        GooglePatentsClient(client=backend).search(**args)
    backend.query.assert_not_called()


def test_empty_lookup_and_sdk_errors(backend):
    client = GooglePatentsClient(client=backend)
    assert client.get_publication("US-123-A1", maximum_bytes_billed=100).records == ()
    error = RuntimeError("quota exceeded")
    backend.query.side_effect = error
    with pytest.raises(RuntimeError) as caught:
        client.search(["battery"], maximum_bytes_billed=100)
    assert caught.value is error
    backend.query.side_effect = None
    backend.query.return_value.result.side_effect = error
    with pytest.raises(RuntimeError) as caught:
        client.get_publication("US-123-A1", maximum_bytes_billed=100)
    assert caught.value is error


def test_lazy_client_and_optional_dependency():
    with patch.object(patents, "_bigquery", return_value=Mock()) as sdk:
        client = GooglePatentsClient(project="example-project")
        sdk.assert_not_called()
        client.search(["battery"], maximum_bytes_billed=100, dry_run=True)
        sdk.return_value.Client.assert_called_once_with(project="example-project")
    # A fresh process forbids Google imports entirely: importing our public API
    # and constructing its client must still succeed.
    subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys
class BlockGoogle:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "google" or fullname.startswith("google."):
            raise ModuleNotFoundError(name=fullname)
sys.meta_path.insert(0, BlockGoogle())
from che126_data_science.data_mining import GooglePatentsClient
client = GooglePatentsClient(project="example")
try:
    client.search(["battery"], maximum_bytes_billed=100)
except ImportError as error:
    assert "uv sync --extra patents" in str(error)
else:
    raise AssertionError("Optional dependency error was not reported")
""",
        ],
        check=True,
    )


def test_missing_project_and_invalid_lookup(backend):
    with pytest.raises(ValueError, match="project"):
        GooglePatentsClient().search(["battery"], maximum_bytes_billed=100)
    with pytest.raises(ValueError):
        GooglePatentsClient(client=backend).get_publication(
            " ", maximum_bytes_billed=100
        )
    backend.query.assert_not_called()


def test_real_sdk_serialization_when_installed():
    bigquery = pytest.importorskip("google.cloud.bigquery")
    config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ArrayQueryParameter("terms", "STRING", ["battery"])],
        maximum_bytes_billed=100,
        dry_run=True,
        use_query_cache=False,
    )
    wire = config.to_api_repr()
    assert wire["dryRun"] is True
    assert wire["query"]["maximumBytesBilled"] == "100"
    assert wire["query"]["queryParameters"][0]["parameterValue"]["arrayValues"] == [
        {"value": "battery"}
    ]
