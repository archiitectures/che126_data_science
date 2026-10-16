# Collection toward 1,000 separator measurements — 2026-10-16

Outcome: target not met. The master grew from 111 to 463 accepted observation rows (net +352). This total includes manufacturer specifications, calculations and bulk references; it is not a count of independent experiments.

## Acquisition performed

- Ran the standard collection command for polyethylene, polypropylene, PVDF, PTFE, polyimide, cellulose and PAN.
- Processed 27 Celgard source documents and 45 FSRI files. Cached documents were reused where available; public FSRI acquisition succeeded after enabling network execution.
- EPO OPS credentials were absent. Followed public separator-related reference links from known patent pages with the existing ingest adapter, bounded at 100 patent documents. No Google search/XHR crawling was used. One exact title was queued once to reduce grant/application duplication, but this is not verified patent-family deduplication.
- Preserved raw sources, extraction artifacts, run progress and 644 unprocessed reference candidates under `data/runs/2026-10-16_patents/`.
- Merged immutable patent-run documents into the main manifest and regenerated CSV/Parquet exports without additional downloads.
- No paid API queries, billing changes or publishing.

## Accepted coverage

| Category | Rows |
| --- | ---: |
| All accepted observations | 463 |
| Separator or component observations | 286 |
| Measured separator observations | 62 |
| Measured separator observations with explicit temperature | 17 |
| Bulk reference observations | 177 |
| Pending review | 4224 |

Across all source categories, eleven properties are represented. Separator observations cover shrinkage, porosity, puncture force, thickness, Gurley time, air-permeability time, pore size and elongation. Thermal conductivity, volumetric heat capacity and density are currently bulk references. Property coverage is not complete at each temperature. Measured separator temperatures are 105.0, 130.0, 140.0, 170.0 °C and currently concern shrinkage exposure tests.

Manufacturer separator classifications include PP and PP/PE/PP. The 62 measured patent rows do not yet have resolved polymer identities; do not assign them automatically to PE/PP groups or wet/dry states. Missing PVDF/PTFE/polyimide/PAN measurements are not evidence that no such source data exist.

## Remaining work

The largest bottlenecks are reusable patent header and protocol resolution: 2,191 rows have unresolved example headers and 1,771 have unresolved test protocols. Additional unit/value ambiguities and unsupported documents also remain. Bulk reference rows and arbitrary pixel samples must not be used to meet the separator target. Accepted observations still need source/experiment-level interpretation before modeling, especially where family identity, polymer and temperature are unknown.

Tensile strength, shutdown/melting/meltdown behavior, electrolyte uptake and ionic conductivity remain missing from the accepted separator view. The exact property/type/temperature matrix is in `coverage.csv`; `summary.json` includes further gap lists. These gaps require extraction improvements and additional source coverage, rather than accepting unresolved records to reach a numeric quota.

## Files and reproducibility

- `collect_patents.py`: bounded source-reference acquisition through Pipeline.ingest.
- `patent_progress.jsonl`: per-document results.
- `merge_patents.py`: local merge into the main master.
- `report_coverage.py`: coverage calculation.
- `summary.json`, `coverage.csv`, `merge_summary.json`: final outputs.
- Main exports: `data/processed/master_observations.csv`, `.parquet`, and `review_queue.csv`.
- Standard batch results: `data/collection_1000_pass1.json` and `data/collection_1000_fsri.json`.

Validation: unique accepted observation IDs, finite numeric values, source provenance, consistent temperature roles, and matching CSV/Parquet row counts passed.
