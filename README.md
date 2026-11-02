## Current project snapshot — 2026-11-02

The assembled dataset contains **10,676 distinct value/context points**, **13,379 accepted evidence observations**, and **37 properties**. **5,121 contexts have numeric temperatures**; 5,555 lack supported numeric conditions. Of 7,950 measured separator/component contexts, 2,571 have numeric temperatures. Bulk references remain separately identified.

This pass added 25 MD-reference contexts and 40 temperature-resolved separator observations (including 32 calibrated figure estimates). Source review corrected 105 observations and held 65 ambiguous observations for review. All withdrawn evidence remains traceable. The total temperature count fell after removing incorrect inherited conditions.

Run `.venv/bin/python scripts/assemble_dataset.py --check-replay` to rebuild from the existing local source archive. Validation: 167 tests pass; 42 generated artifacts replay byte-for-byte. A fresh clone requires the source archive for a full rebuild. Arbitrary PDF/figure interpretation still requires reviewed calibration and attribution.

See [the comprehensive project guide](docs/COMPREHENSIVE_PROJECT_REPORT.md), [dataset](https://huggingface.co/datasets/archiitecture/che126), and [figures](visualizations/README.md). Earlier dated sections below are historical snapshots.

## Earlier thermal collection and temperature recovery — 2026-10-30

Current local exports: **10,582 distinct contexts**, **13,258 evidence observations**, **5,110 with numeric temperature (+2,419)**. Added 2,200 FSRI bulk-reference contexts and 23 paper contexts; recovered conditions for 196 existing contexts. Full data remain in `datasets/unique_points.csv`; `temperature_resolved_points.csv` is the explicit-temperature subset. **5,472 still lack numeric test conditions**, including 676 temperature-response properties. Bulk references and separator performance remain distinguished. See the [current report](datasets/thermal_temperature_report.md) and `datasets/temperature_gap_audit.csv` for evidence, limits and next actions. Earlier sections below are historical.

## Earlier collection snapshot — 2026-10-26

Current local exports contain **8,320 distinct contexts** and
**10,996 accepted observations**, using `separator-v32` / schema 2.
The pass admitted 2,338 new measurement contexts;
the 3,000-additional-point target was not met.
See the [latest collection report](datasets/collection_latest_report.md)
for material and temperature/property coverage, PDF attribution and validation.
Earlier dated sections below describe earlier snapshots.

# ChE126 battery separator data science

Collect, normalize and trace temperature-dependent separator properties from
patents, manufacturer datasheets, public materials measurements and reviewed
literature imports. Physical simulations and trained prediction models are outside
this repository's current scope.

## Dataset files and review history

The 2026-10-23 independent review rebuilt the cached corpus with `separator-v24` (schema 2).
That snapshot contained **8,977 accepted source observations**, **5,982 distinct scientific
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
