# ChE126 battery separator data science

Collect, normalize and trace temperature-dependent separator properties from
patents, manufacturer datasheets, public materials measurements and reviewed
literature imports. Physical simulations and trained prediction models are outside
this repository's current scope.

## Current dataset

The independent review rebuilt the cached corpus with `separator-v24` (schema 2).
There are **8,977 accepted source observations**, **5,982 distinct scientific
value/context groups**, and **23 property categories**. Fifteen incorrectly
classified relative/dispersion values were moved to the review queue. The context
count increased because protocol, shrinkage basis, grade and replicate distinctions
are now preserved; this is not newly collected data.

- [`datasets/master_observations.csv`](datasets/master_observations.csv): accepted
  evidence, one property per source observation; Parquet has the same records.
- [`datasets/unique_points.csv`](datasets/unique_points.csv): equal values with equal
  recorded scientific context grouped across sources, with full membership in
  `unique_point_evidence.json`. This is not a count of independent experiments.
- `data/processed/review_queue.csv`: ambiguous, unsupported or invalid extractions.
- [Independent review](docs/INDEPENDENT_REVIEW.md): corrections, checks and remaining
  limitations. [Dataset audit](output/review/dataset_audit.json) records input hashes.
- [Figures and reproduction code](visualizations/README.md).

## Pipeline and source support

| Stage/source | Implementation | Supported behavior |
| --- | --- | --- |
| Discovery | `sources.py`, `discovery.py`, `patents.py` | Celgard/FSRI discovery, EPO credentials, explicitly budgeted BigQuery |
| Acquisition | `acquisition.py` | Bounded HTTPS, access checks, immutable bytes, hashes and cache receipts |
| Patent HTML | `patent_html.py`, `material_identity.py` | Supported experimental tables, explicit units/protocols and sample recipe links |
| Celgard PDF | `pdf_tables.py` | Supported table layouts, product/component scope and limits |
| FSRI | `structured.py`, `fsri.py` | HFM SI tables and density; bulk references stay labeled |
| Papers/PoLyInfo | `structured.py` | Reviewed CSV/TSV/XLSX imports; PoLyInfo requires authorization metadata |
| Validation/assembly | `master.py`, `pipeline.py` | Typed rows, review routing, context-aware deduplication, CSV/Parquet |
| Analysis | `observations.py`, `scripts/export_unique_points.py` | Coverage and distinct-context exports |

The code does not extract arbitrary separator information from every format.
Scanned PDFs, general paper XML, unsupported tables and unknown properties require
an adapter or reviewed import. The dated literature import scripts encode specific
source decisions. Graph tracing requires explicit calibration and series isolation.
Missing temperatures remain missing, and exposure temperatures are distinct from
measurement temperatures. Manufacturer specifications and calculated values retain
their record types.

## Setup with uv

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then:

```bash
git clone git@github.com:archiitectures/che126_data_science.git
cd che126_data_science
uv sync --locked --extra ingest --extra graph --group dev
uv pip install --python .venv/bin/python -r visualizations/requirements.txt
uv run python -c "import che126_data_science.data_mining; import che126_data_science.data_science"
```

Python 3.12 or newer is supported; `.python-version` selects 3.12 for development.
`uv sync` installs the local package in editable mode, so library edits are
available immediately. The imports above verify setup. Patent acquisition is documented in
[data_mining/PATENTS.md](data_mining/PATENTS.md); cleaning and coverage are documented in the collection guide. Build distributable artifacts with `uv build`.
Another project can install this package with
`uv add git+ssh://git@github.com/archiitectures/che126_data_science.git`.

## Run and verify

```sh
.venv/bin/python -m che126_data_science aggregate --data-dir data
.venv/bin/python scripts/export_unique_points.py
.venv/bin/python scripts/audit_dataset.py
.venv/bin/python visualizations/generate_figures.py
.venv/bin/pytest -q
```

Aggregation reprocesses stale extraction artifacts from cached bytes. Export the
unique view afterward to synchronize `datasets/` and `data/processed/`. Audit is
read-only with respect to data and writes its report to `output/review/`.

See the [collection guide](docs/COLLECTION_GUIDE.md), [mining guide](data_mining/README.md),
[analysis guide](data_science/README.md) and [dataset card](datasets/README.md).
The public Hugging Face repository can lag these local exports; publication is a
separate action. Existing PDFs and dated collection reports are historical snapshots.

## Keep the repository lean

Reusable code belongs in `src/`; dated experiments and curation evidence stay in
`data_mining/runs/`. Base dependencies are empty; install only the needed extras.
Raw data, caches and extraction artifacts dominate disk usage, not the Python code.
Do not delete immutable source evidence to reduce size. Avoid copying extraction
logic into new collection scripts; add supported formats at the existing adapters.
Environment files and private keys are ignored; install the provided Git hooks for
commit/push scanning. No secrets belong in tracked source or examples.
