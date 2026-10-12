# Google Patents acquisition

This client uses the Google Patents Public Datasets on BigQuery, not an
undocumented website endpoint or third-party search service. The primary table
is `patents-public-data.patents.publications`.
[Dataset schema and examples](https://github.com/google/patents-public-data).

## Setup

```bash
uv sync --extra patents --group dev
```

Create/select a Google Cloud project with BigQuery enabled and permission to
create query jobs (for example, BigQuery Job User). Install the Google Cloud CLI
and set up application-default credentials locally:

```bash
gcloud auth application-default login
```

Alternatively inject an authenticated `google.cloud.bigquery.Client`. The
package does not read credentials or initialize clients at import/construction;
SDK authentication occurs on the first operation. Keep credentials outside the
repository. See [Google's authentication guide](https://docs.cloud.google.com/bigquery/docs/authentication).

## Search, inspect, export

```python
from che126_data_science.data_mining import (
    GooglePatentsClient, PatentResults, QueryEstimate, export_json,
)

client = GooglePatentsClient(project="YOUR_PROJECT_ID")
terms = ["battery", "separator", "porosity"]
# This is a deliberately conservative example budget, not an estimate of the
# patent table's size. A broad full-text query may exceed it and be rejected.
budget = 1_000_000_000
estimate = client.search(terms, countries=["US"],
                         maximum_bytes_billed=budget, dry_run=True)
assert isinstance(estimate, QueryEstimate)
print("Estimated scan bytes:", estimate.bytes_processed)

# Run only if the estimate fits your chosen budget; do not automatically raise
# the budget to match a scan. BigQuery also enforces the cap on execution.
if estimate.bytes_processed <= budget:
    hits = client.search(terms, countries=["US"], limit=20,
                         maximum_bytes_billed=budget)
    assert isinstance(hits, PatentResults)
    export_json(hits, "patent_search.json")
    if hits.records:
        publication = client.get_publication(
            hits.records[0].publication_number,
            maximum_bytes_billed=budget,
        )
        assert isinstance(publication, PatentResults)
        export_json(publication, "patent_publication.json")
```

- `search` matches **every term**, case-insensitively, as a literal substring in
  **any selected field**. Default fields are title, abstract, claims, description.
  Use `fields=["title", "abstract"]` for a narrower search. Terms are not website
  Boolean/CPC query syntax; percent signs and underscores are literal characters.
- Countries are publication-country codes. Results sort newest first, then by
  publication number. Default limit is 20. No family deduplication is performed.
- Search returns compact metadata. `get_publication` accepts the exact
  hyphenated identifier returned by search and fetches available localized
  claims/descriptions. It also supports `dry_run=True`. Missing publications
  produce empty results; missing text is an empty tuple, not translated or guessed.
- Dates become ISO dates; zero, absent, or invalid dates remain `None`. Text
  retains source language labels. Full-text coverage varies; this is not a
  guarantee of all documents available on the Google Patents website.
- Every operation requires `maximum_bytes_billed`. `limit` limits returned rows,
  **not scan cost**. A dry-run estimate does not execute the query or fetch rows.
  Query submission and result retrieval have a configurable timeout (120 seconds
  each by default); SDK permission, quota, and query errors propagate unchanged.
  See [BigQuery cost controls](https://docs.cloud.google.com/bigquery/docs/best-practices-costs).
- JSON exports include the operation and filters, source table, UTC retrieval
  timestamp, and records. Exports are caller-selected local files; they are not
  automatically uploaded to Hugging Face.

Search examples: `["battery", "separator", "tensile"]`,
`["separator", "thermal shrinkage"]`, or `["separator", "pore size"]`.
These find candidate documents, not verified measurements. Review examples,
tables, methods, and actual measurement state before adding values to the dry
or electrolyte-soaked CSVs. Patent claims and proposed ranges are not necessarily
experimental observations. Preserve publication number and exact table/page
locator during curation.

## Verification

```bash
uv run --extra patents --group dev pytest -q
uv run --group dev ruff check .
uv build
```

Tests use an injected fake network client. With the optional extra installed,
they exercise real BigQuery parameter/configuration objects; without it, a small
parameter facade enables offline checks and the SDK serialization check skips. Live querying additionally requires a project, credentials,
network access, and a chosen scan budget.
