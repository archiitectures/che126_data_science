# Current workflow status

The active extractor is **separator-v24**, master schema **2**. Start with the
[root README](../README.md) and [independent review](INDEPENDENT_REVIEW.md).
Current exports contain 8,977 accepted observations and 5,982 scientific context
groups. Run `scripts/audit_dataset.py` after aggregation/export. The sections below
retain dated development history; their old counts and version labels describe
those snapshots. Current literature support remains reviewed structured import,
not a universal paper/PDF parser.

## Current material identity snapshot — 2026-10-23

Read the [current identity report](../datasets/material_identity_report.md) and
`datasets/material_identity.csv` for the latest material counts, evidence and
remaining gaps. The accepted master and distinct CSV/Parquet exports are synchronized
under `datasets/` and `data/processed/`. The identity resolver is integrated into
patent ingestion; dated replay and validation artifacts live in
`data_mining/runs/2026-10-23_identity_reconciliation/`.

Master schema 2 adds `material_identity_status`, `material_identity_evidence` and
`material_identity_reason`. Existing raw observations remain readable through
nullable defaults. Source recipe links can change distinct context IDs/counts;
the observation lineage preserves the mapping to the original measurements.
Earlier collection reports and PDFs retain their historical snapshots.

## Polymer identity and temperature recovery (2026-10-19)

Extraction version `separator-v10` recovers explicit numeric measurement temperatures
from the linked property protocol, rather than limiting temperatures to shrinkage.
It does not impute room temperature from ASTM/JIS citations, unqualified ambient
wording, or manufacturing conditions. Tolerance/range temperatures remain
unassigned by the scalar parser.

Complete PE/PP composition columns must total 100% before automatic identity
assignment. Optional `sample_annotations` in the ingestion context supply reviewed
identity metadata keyed by exact sample header or `TABLE n:sample header`. Each
annotation requires exact immutable-source snippets and paragraph locators (`id`
or a unique `num:` locator). These are reviewed recipe-to-example links, not a
classifier based on general patent claims. Sample headers are replaced at later
headers, preserve split comparative prefixes, and reset at explicit table boundaries.
Ambiguous unnumbered examples remain pending.

The counts and source limitations for that historical pass are in
`data_mining/runs/2026-10-19_identity_temperature/README.md` and
`data/processed/collection_breakdown.json`. The property/temperature CSVs under
`data/processed/` and `datasets/` describe the complete current export.
Run `scripts/export_unique_points.py` after aggregation to synchronize accepted
master and distinct CSV/Parquet files into `datasets/`. Coverage reports and the
dataset card can be refreshed with the dated run's reporting scripts. The
16-page PDF handbook remains the earlier 1,004-point snapshot; its architecture
walkthrough is useful, but current collection counts supersede its totals.

111 tests cover the pipeline and regressions. No cloud billing or paid queries
were used in this follow-up. Preserve source evidence and all review rows.

## Earlier collection view (2026-10-19, before identity recovery)

That historical master had 2,086 accepted source records. Run `python scripts/export_unique_points.py` after aggregation to regenerate the conservative distinct-value/context view, its typed Parquet/CSV exports, and evidence links. The current view contains 1,004 points (835 separator/components, 169 bulk references); only 124 are measured separator points with explicit temperatures. The exporter deliberately collapses equal contexts across sources, including potentially different experiments; it is not an independence certificate.

That pass used extraction version `separator-v6`; 104 tests pass. The collection report at `data_mining/runs/2026-10-16_1000_target/README.md` details source formats, method counts, 13 properties, categories and 14 reported temperatures. The 16-page newcomer guide is `output/pdf/code_review_handbook.pdf`. Preserve the full master and `unique_point_evidence.json` when using the deduplicated view.

## Automation corrections (2026-10-16)

Extraction version `separator-v4` rebuilds stale artifacts from cached raw files during aggregation. Repeated bounded `collect` runs now skip processed documents and advance to remaining candidates. Use `--refresh` to deliberately revisit processed documents; failed downloads remain retryable. Review entries are preserved, including unresolved bounded patent cells and individual malformed spreadsheet rows. Source failures no longer prevent unaffected collection or folder inputs from completing.

Patent tables support explicit example columns, separate unit columns, and explicit example-per-row layouts. Unique property protocols are recognized beyond shrinkage and thickness. Ambiguous temperatures or conflicting protocols remain in review. These rules do not replace authorization for PoLyInfo, graph calibration, or semantic review of unsupported PDF layouts.

# Automatic source-to-master workflow — 2026-10-16

The new pipeline extends the existing commands described below. Start with
`uv sync --locked --extra patents --extra pdf --extra ingest --extra graph --group dev`.
Use `--extra pdf-fallback` only when the optional pdfplumber fallback is needed.
The base package still has no mandatory runtime dependencies. Python 3.12+ and
CPU execution are supported.

## Reproduce the verified demonstration

```bash
uv run python scripts/run_pipeline_demo.py
```

This reads included source fixtures, ingests five documents, rebuilds the master,
checks byte-identical CSV/Parquet after a repeated run, and traces a saved calibrated
patent-curve segment. Outputs are under `data/demo/processed/`. It uses no LLM,
network connection, billing configuration, or paid API. See
[SOURCE_AUDIT.md](SOURCE_AUDIT.md) for exact source findings and counts.

## Collect automatically

```bash
uv run python -m che126_data_science collect \
  --sources fsri celgard patents --materials polyethylene polypropylene \
  --max-documents 50 --patent-limit 25 --data-dir data
uv run python -m che126_data_science aggregate --data-dir data
```

Default patent discovery is EPO OPS. Supply `EPO_OPS_KEY` and `EPO_OPS_SECRET`
through the environment after registering with EPO; do not commit credentials.
Missing credentials or a source failure is reported in the manifest and batch
result while other sources continue. There is no silent paid fallback. Default
online batches use at most 50 documents and 25 patent candidates, interleaved
across sources. FSRI defaults to the cached `main` tree; use `--fsri-revision SHA`
for a chosen immutable revision. Actual raw file URLs always use the resolved SHA.

Existing BigQuery remains available as an explicit alternative:

```bash
uv run python -m che126_data_science collect --sources patents \
  --patent-provider bigquery --project che126-separators-20261012 \
  --budget-usd 2 --usd-per-tib 6.25 --max-documents 10
```

Verify the current US analysis rate before use. The cumulative per-run byte ledger
reserves each query's capped bytes before submission; uncertain failures consume
the reservation. All search queries are estimated first. The $300 trial credit is
not treated as a run budget. No billing linkage or paid query was performed while
implementing this workflow. The old `patents` CLI still estimates by default.

## Ingest one document or a folder

```bash
uv run python -m che126_data_science ingest --source patents \
  --input https://patents.google.com/patent/US9911958B2/en
uv run python -m che126_data_science ingest --source celgard --input path/to/pdfs
uv run python -m che126_data_science ingest --source fsri --input path/to/instrument.tst
```

Optional `--context metadata.json` supplies known product/polymer identity, source
URL, restrictions, explicit column mappings, or family metadata. Local files and
HTTPS URLs are copied into an immutable SHA-256 cache. Existing acquisition
receipts are adopted when possible. Files, extracted cells/text/geometry and
normalization results remain auditable through the source manifest.

Unchanged remote URLs and discovery results reuse cache without network requests.
`--refresh` explicitly revalidates resources, using ETag/Last-Modified if supplied.
Transient HTTP/network errors have bounded retries and serial rate limiting.
Source byte limits and HTTP timeouts apply. Authentication, restrictions and quota
errors are reported. Cached-file corruption fails loudly. Parser-version changes
trigger local re-extraction on aggregate; aggregation does not re-download sources.

## Master exports and review

`aggregate` reads only its selected source manifest, never an unrestricted glob of
historical CSVs. Outputs under `data/processed/`:

- `master_observations.csv` and matching typed `master_observations.parquet`.
- `review_queue.csv` with original values/units and reasons for unresolved records.
- `source_manifest.json` linking raw documents, extraction versions/artifacts,
  source restrictions, duplicates and batch failures.
- `qc_summary.json` with accepted/review counts, source/type counts and missing
  temperature count.

The new `MasterObservation` schema is separate from the legacy `Observation` CSV.
It adds explicit source hashes/cell locators, product construction, structured test
conditions, statistic, record type, provenance and uncertainty. Nulls remain null.
Original units are retained; aliases/conversions are documented. Typical values
are not automatically labeled measured. Claimed ranges, spec limits, calculated
values and digitized estimates remain distinct. Use:

```bash
uv run python -m che126_data_science aggregate --data-dir data \
  --out-dir data/processed/measured --measured-only
```

Only accepted `record_type=measured` rows enter this export. Filter bulk-reference
sample forms separately when training a separator-film model. Duplicate fingerprints,
verified identical family/example evidence and snapshot/raw representations are
linked in the manifest; distinct replicates remain distinct. Historical legacy
CSV imports enter review until their primary-source metadata is reverified.

## Authorized structured imports

```bash
uv run python -m che126_data_science manual-import --source polyinfo \
  --input permitted_export.xlsx --context permission_and_columns.json
```

NIMS accepts local files only, with `authorized: true` and explicit `restrictions`
in the context JSON. Required canonical columns are `sample_id,property,value,unit`;
optional columns follow the master model. Use a `columns` dictionary from supplied
headers to canonical names. XLSX can specify `sheet`. Add original source citation,
record type, conditioning, temperature role and test details when known. Missing
metadata is not inferred from a wet manufacturing process or assumed ambient state.

## Figure extraction and digitization

```bash
uv run python -m che126_data_science figures --data-dir data
uv run python -m che126_data_science digitize \
  --input tests/fixtures/pipeline/patent_tma.png \
  --calibration tests/fixtures/pipeline/tma_calibration.json \
  --out-dir data/processed/digitization
```

`figures` preserves linked patent image sheets and a caption manifest. Sheets may
contain several numbered figures; the program does not invent a sheet-to-figure
mapping. Calibration specifies the actual figure number, crop, image hash, two
reference points per linear axis, units, curve color/isolation mask, reference
points and error tolerances. Save this once and rerun deterministically.

The digitizer exports `curve_points.csv`, `figure_crop.png`, calibration,
`figures_manifest.csv` and `digitization_qc.json`. All samples share a curve ID.
It removes configured horizontal grid lines, flags disconnected/thick columns and
jumps, and retains gaps. Multi-series figures require explicit isolation; log axes,
uncalibrated plots and failed tolerances go to review. Digitized data is never
silently merged into the master. Prefer original numeric series whenever available.

## Extending and validating

Adapters are registered by source name and return master records plus raw artifacts.
Add fixtures before widening a parser. Reuse normalization aliases and the shared
validator; add a property/unit only from actual source evidence. Re-extraction
behavior is versioned in `EXTRACTION_VERSION`. Do not change a parser without bumping
that version when old cached outputs would otherwise survive.

Run `.venv/bin/python -m pytest -q`, `.venv/bin/ruff check src tests`, and
`git diff --check`. Live EPO authentication remains unverified until credentials
are provided. Generic patent PDF semantics and other FSRI apparatus remain review
work rather than automatic measurements.

---

## Legacy commands and research notes

# Collection and cleaning guide

Run commands from the repository root. Python 3.12+; base runtime uses only the
standard library. `uv sync --locked --extra patents --extra pdf --group dev`
installs the optional BigQuery SDK, pypdf, and test/lint tools. On this Mac, if
Python cannot locate its CA bundle, set `SSL_CERT_FILE=/etc/ssl/cert.pem` for public
HTTPS calls. Never disable certificate verification.

## Source capabilities

| Source | Implemented | Boundary |
|---|---|---|
| Google Patents public BigQuery table | Parameterized search, date window, titles-only projection, capped estimate/execute, full-text lookup | Finds documents, not validated property observations; no universal table extractor |
| FSRI Materials and Products DB | Material catalog search with pagination; saved-page JSON curves with axes/error bars; all rows of pinned HFM snapshots | Bulk references differ from separator films; curve classification and other apparatus need review |
| Celgard | Current product/PDF discovery, hashed raw downloads, known Basic Film Properties extraction | Unsupported rows reported; tensile `Kg/cm2` is deliberately unresolved; no OCR |
| NIMS PoLyInfo | Assisted search plan; common strict CSV importer for permitted records | Authenticated access; no scraping, bulk download or implied redistribution permission |

Official references: [NIMS access and restrictions](https://polymer.nims.go.jp/),
[Celgard product data](https://www.celgard.com/product-data),
[FSRI public catalog](https://materials.fsri.org/search),
[FSRI repository and apparatus descriptions](https://github.com/ulfsri/fsri_materials_database).

## Start with discovery

```bash
uv run python -m che126_data_science discover celgard polyethylene
uv run python -m che126_data_science discover fsri polypropylene
uv run python -m che126_data_science discover polyinfo PVDF \
  --properties porosity tensile_strength thermal_conductivity \
  --temperatures -20 25 60 90 120
```

Family searches expand common aliases; grade searches such as HDPE stay specific.
Searches produce leads, not exhaustive proof that a database lacks a material.
PE-containing trilayers and composites are candidates, not pure PE. PET is not
matched as polyethylene. FSRI catalog searches use one canonical family term and
filter result names; commercial synonyms absent from result names may be missed.
Only PoLyInfo's assisted plan uses the discovery property/temperature arguments;
Celgard/FSRI discovery first finds materials, then extraction/coverage evaluates
available properties and temperatures. No query manufactures temperature coverage.

## Preserve sources, extract, review

```bash
uv run python -m che126_data_science fetch \
  https://www.celgard.com/storage/components/2400_com_data_2026-01.pdf data/raw
# Use the returned SHA-256-named PDF path:
uv run python -m che126_data_science celgard-extract data/raw/HASH.pdf \
  data/interim/celgard.csv --product 2400 --material PP \
  --url https://www.celgard.com/storage/components/2400_com_data_2026-01.pdf \
  > data/interim/celgard_review.json
```

`fetch` saves immutable bytes plus a timestamp, source URL and SHA-256 receipt.
Downloads have a 20 MB cap and a 30-second socket timeout. Errors propagate;
there are no hidden retries, background jobs or automatic uploads. Review every
unresolved row, the product identity, conditions and original PDF before merging.
Typical values and minimum/maximum specifications remain different records.
Celgard calculated porosity is labeled calculated; unknown temperature stays blank.
The tensile unit requires explicit source confirmation before converting to MPa.

FSRI public pages contain JSON plots. Fetch a discovered material-detail URL, then:

```bash
uv run python -m che126_data_science fsri-curves data/raw/HASH.bin > curves.json
uv run python -m che126_data_science fsri-hfm \
  data_mining/fsri_polyethylene_hfm_extract.json data/interim/fsri.csv
```

Use the actual filename returned by `fetch`; an extensionless page is `.bin`.
`fsri-curves` preserves all traces, axis labels and error bars without evaluating
JavaScript. It does not infer that every x-axis is temperature: some plots use
time, heat flux, or wavelength. Aggregate plotted values are not raw specimen
replicates. Keep the acquisition receipt beside the curve output. HFM snapshot
imports require a full Git commit and source blob/path for every excerpt. Each
result row is retained, including repeated setpoints. Generic HFM imports use
`bulk_reference` unless a reviewed entry explicitly supplies `sample_form`.

## Clean one value per record

Copy `datasets/observation_template.csv` and enter permitted, reviewed observations.
Required fields: record_id, sample_id, material, property, value, unit, source_url,
source_locator, sample_form. Optional fields describe state, temperature and its
role, direction, method, conditions, value_type, replicate, raw values and notes.
Use conditions for electrolyte identity/concentration, exposure duration,
humidity, loading rate and other protocol details; these affect comparability.

Supported properties/units live in `data_science/observations.py::UNITS`: geometry,
porosity, tensile strength, elongation, puncture force, shrinkage, heat capacities,
conductivity, density, transition temperatures, electrolyte uptake and Gurley time.
Add new properties deliberately with units and tests. Normalized puncture per
20 micrometers is NOT plain puncture force. Do not import it under that property.

```bash
uv run python -m che126_data_science clean reviewed.csv cleaned.csv
uv run python -m che126_data_science coverage cleaned.csv \
  --properties porosity thickness tensile_strength puncture_force thermal_shrinkage \
  --temperatures -20 25 60 90 120 > coverage.json
```

Finite numeric values, physical temperature, percentage porosity, units, enums,
row widths and provenance are validated. Only explicit conversions are allowed;
raw values/units survive. Exact duplicate IDs collapse; conflicting IDs fail.
Replicates with different IDs survive. Output CSVs refuse overwrite.

Temperature roles are `measurement`, `exposure`, `unknown`. Processing temperature
belongs in notes, never temperature_C. A melting temperature is a property value,
not automatically the temperature at which another property was measured. States
are `dry`, `electrolyte_wet`, `unknown`. FSRI's label Wet is ambient conditioning,
not electrolyte soaking. Do not assert dry state without evidence.

## Coverage is evidence, not interpolation

Coverage groups by material, sample, source URL, form, state, temperature role,
direction and conditions. It reports exact record IDs, methods and actual
reported temperatures. It never fills missing temperatures or pools different
samples/sources. Bounds, claims and calculated values do not fill measured/typical
coverage. Inspect value_type in the tidy table when using derived properties.
`--tolerance 0.02` allows explicit nearby-temperature matching; the default is zero.
An empty input produces zero groups, not a claim of completeness. A fully populated
requested grid still is not a claim of complete physical characterization.

## Patent costs and reproducibility

```bash
uv run python -m che126_data_science patents polyethylene separator \
  --project che126-separators-20261012 --maximum-bytes-billed 1000000000 \
  --start 2025-01-01 --end 2026-01-01
```

Default CLI operation is a dry-run estimate, searching title only. `--execute`
submits a paid-capable query with the same hard maximum; billing must already be
configured separately. Publication end is exclusive; publication year is NOT a
measurement-temperature condition. LIMIT controls returned rows, not scanned
bytes. Full-text lookup can scan much more data. The library preserves its prior
full-field search default; explicitly set `fields=['title']`, `titles_only=True`
for the cheaper discovery projection. Job ID and processed/billed bytes are saved
for executed results. No billing changes are made by this package.

## Code map and maintenance

- `data_mining/patents.py`: BigQuery boundary and provenance; optional SDK import.
- `data_mining/sources.py`: material matching, public discovery, bounded downloads,
  PoLyInfo assisted plan. No source plugin framework.
- `data_mining/fsri.py`: legacy published-table builder, generic HFM observations,
  source JSON curves. Legacy output remains reproducible.
- `data_mining/celgard.py`: optional PDF text extraction; supported rows only.
- `data_science/observations.py`: the shared tidy contract and coverage functions.
- `__main__.py`: thin CLI; Python functions remain usable from notebooks.
- `tests/`: offline contracts and real-source fixtures; no paid/network tests.
- `datasets/`: existing wide published tables plus a blank tidy import template.
- `data_mining/examples/`: staged demonstrations; FSRI rows duplicate existing
  evidence and must not be counted as new measurements.

Run `.venv/bin/python -m pytest -q`, `.venv/bin/ruff check src tests`, and
`git diff --check`. Do not build models until material/temperature coverage and
measurement comparability are adequate. Do not publish NIMS content without
permission or automatically merge candidate evidence into the public dataset.
# Latest collection update — 2026-10-19

The dated follow-up report at
`data_mining/runs/2026-10-19_expansion/README.md` is the current collection
snapshot. It contains 2,159 distinct value/context points from 5,019 accepted
source observations, across 22 properties (20 separator properties). The
increase from 1,142 is +1,017 contexts: 612 recovered from cached documents,
378 from new sources/imports, and 27 from reviewed sample-identity
disambiguation. Counts do not mean independent experiments.

New recurring categories are contact angle, electrical resistance, shutdown
response time, and tortuosity. They fit the existing tidy schema as property
rows. There are 488 separator points with numeric measurement/exposure
conditions over 15 temperatures from 23 to 180 °C; no subambient separator
measurements were found. Polymer remains unresolved for 1,228 separator points.
The current `datasets/` and `data/processed/` exports and `validation.json`
contain the synchronized data and evidence checks. Preserve these limits when
using the historical newcomer PDF, whose counts are from an earlier snapshot.
