# Independent pipeline and dataset review — 2026-10-23

**Result: useful, traceable research data with important limits; not a universally
validated separator database.** This review examined discovery, acquisition,
normalization, patent/material extraction, Celgard/FSRI adapters, structured imports,
aggregation, distinct-context exports, graph tracing, tests and documentation.
It did not assume the previous review's passing tests proved scientific correctness.
All work used cached sources; no paid query, new acquisition or publication occurred.

## Findings and corrections

| Priority | Finding | Resolution |
| --- | --- | --- |
| High | Eight patent rows labeled standard deviation of puncture strength and seven labeled increase in puncture strength were accepted as absolute puncture force. | `master.make_observation` now routes these derived definitions to review. All 15 original records remain preserved; cached corpus rebuilt with separator-v24. |
| High | The distinct-context key omitted method, measurement context, shrinkage basis, grade and replicate information. Before correction, 801 groups mixed method values, 540 mixed measurement-context values and 133 mixed shrinkage-basis values (counts overlap). | Shared `master.SCIENTIFIC_FIELDS` now defines scientific equality for export and family/evidence grouping. Source location is excluded; independent experiments are still not certified. |
| Medium | Patent extraction attached the document's shrinkage basis to 1,096 observations of other properties. It also consulted the generic shrinkage paragraph rather than the selected property protocol. | Basis is now restricted to thermal shrinkage and taken from the linked property context. Existing numeric measurements are preserved. |
| High | Structured CSV imports allowed duplicate headers/mapped names to overwrite values, and extra/missing cells could be discarded. | Duplicate headers fail visibly; malformed rows/mapping collisions go to review. XLSX empty cells remain permitted. |
| Medium | Aggregation could silently discard conflicting same-ID scientific records before export's conflict check. Family/evidence keys omitted important conditions. | Conflicting same-ID scientific fields now fail; family/evidence keys reuse the full scientific context. |
| Medium | READMEs described extraction as deferred and validation as unimplemented; the dataset card mixed legacy wide-table columns with the current tidy schema. | Root/mining/analysis READMEs rewritten; dataset card and collection guide identify current behavior, historical sections and supported-format limits. |
| Low | Two lint errors in PDF handbook generation. | Removed unused import and corrected import ordering. |

## Dataset result and checks

| Quantity | Before | Reviewed export |
| --- | ---: | ---: |
| Accepted observations | 8,992 | 8,977 |
| Distinct value/context groups | 4,394 | 5,982 |
| Property categories | 23 | 23 |

The context increase is a grouping correction, not new data. The full accepted
master has no repeated observation IDs; the distinct export has no repeated context
IDs. Full evidence membership reconciles to every accepted observation. Equal
numbers alone are neither proof of duplication nor proof of independent experiments.

The audit verified all 349 accepted source-file hashes, schema/physical bounds,
canonical units and numeric conversions, CSV/Parquet equality, synchronized copies,
context-key membership and representative membership. Recorded source-cell values
match for all 7,250 accepted patent rows, 224 Celgard rows and 1,326 structured-import
rows. FSRI's 177 rows were rebuilt from the cached SI/density adapters. Entire-corpus
replay processed 1,882 manifest entries and produced 36,584 pending review rows.
Manifest entries can repeat a source with different ingestion context.

The source-cell check compares preserved extraction tables and import cells; it is
not independent human verification of every source interpretation. Hashes establish
file identity, not factual truth. The 1,326 structured rows are checked against their
import files, while primary-paper evidence lives in notes and dated curation records.
The original-value fields in a manual import may already contain conversions from
the upstream publication; primary printed values may be in notes. Do not treat the
CSV's file hash as the paper's hash.

The citation URLs resolve to 275 distinct patent publications, 13 literature URLs,
28 Celgard datasheets and 40 FSRI files (356 URLs). There are 349 input files because
curated files can combine several primary sources, some source URLs overlap imports,
and an FSRI snapshot has no URL on its own record. Previous counts of 268 patents
counted only the patent adapter and missed manually imported patent publications.
These are contributing sources; they do not count every search result screened.

## Remaining scientific and automation limits

1. **Patent-family independence is unverified.** Every accepted record currently
   lacks a family ID. Equal-value grouping does not establish that differently
   labeled publications report different experiments. Keep source lineage and do
   not advertise this dataset as free of all experimental duplication.
2. **Metadata remains incomplete.** Of 5,982 contexts, 1,255 have no linked polymer,
   4,395 no numeric test temperature, and 423 no method field. These are explicit
   gaps; no room-temperature defaults or material guesses were added. Counts differ
   from earlier reports because protocol grouping is now finer.
3. **Supported formats are finite.** Generic paper XML, arbitrary PDF layouts,
   scanned tables, unknown property definitions and uncalibrated graphs are not
   automatically understood. Literature imports rely on source-specific curation
   scripts. PoLyInfo is authorized local import only. This pipeline cannot claim
   to extract “any” separator data or fully characterize every material/temperature.
4. **Acceptance is not a scientific certification.** Patent material inheritance
   and protocol matching are deterministic heuristics with regression coverage;
   rare layouts and ambiguous recipes still require review. Manufacturers' typical
   values, limits, calculated quantities and bulk references must remain distinct
   from measured separator properties.
5. **Primary provenance for manual imports needs stronger structure.** Upstream
   hashes/coordinates in notes are auditable but not uniformly machine enforced by
   the generic importer. A future targeted change should add a primary-evidence
   contract and require it before promoting externally curated records. This review
   does not claim every imported literature interpretation was independently checked.
6. **Exports are individually atomic, not a multi-file transaction.** Serial usage
   is the supported workflow. Concurrent writers can race over the shared temporary
   filename and manifest; do not run overlapping ingestion/export jobs in one data
   directory. A lock/staged snapshot is appropriate if concurrency is introduced.

## Lean code and efficiency

The reusable mining/master code was about 4,900 lines at review start, with lazy
optional dependencies and no mandatory runtime dependencies. The primary disk cost
is stored evidence and repeated extraction snapshots: `data/` was about 6.5 GB,
versus 620 KB for `src/` (including generated files). These are different forms of
bloat. Immutable evidence was preserved; destructive cache cleanup was not performed.

The review consolidated scientific equality into one shared field list rather than
adding another pipeline. Remaining scaling costs are full-manifest serialization
per ingestion, repeated parsing during extractor-version changes, and polynomial
header scans within large patent tables. The review replay checkpointed every 50
artifacts. Dated scripts should remain audit history, not be copied as new runtime
frameworks. Archive superseded extraction caches separately if storage matters;
retain source hashes, raw bytes and current manifest/artifacts for reproduction.

Legacy acquisition/text extractors coexist with the new pipeline for compatibility.
Avoid broad cleanup until their CLI callers are migrated. No new runtime dependency
was added. Unsupported inputs should produce visible review records, not guessed
values or hidden paid fallbacks.

The legacy PDF handbook builder embeds historical narrative/counts and should not
be used to describe a new collection snapshot without updating that narrative.
The current Markdown review and dataset card supersede those PDFs.

## Reproduction and evidence

```sh
.venv/bin/pytest -q
.venv/bin/ruff check src tests scripts visualizations/generate_figures.py
.venv/bin/python scripts/audit_dataset.py
.venv/bin/python visualizations/generate_figures.py
```

There are **146 passing tests** (138 baseline plus eight review regressions).
Evidence is under `output/review/`: before exports/manifest, replay log, moved rows,
current audit, test results, export summary and refreshed figures log. The previous
identity/collection reports and PDFs are historical snapshots. Current README
figures and coverage tables use the reviewed export; no Hugging Face upload occurred.
All 12 mirrored accepted/export files are byte-identical after a repeated export;
Ruff and Git whitespace checks pass.
