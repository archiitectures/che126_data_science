# Automation and correctness review — 2026-10-16

## Implementation follow-up

The six findings below were addressed in extraction version `separator-v4`:

- Ambiguous temperature ranges/multiple conditions stay pending with no invented scalar temperature.
- Structured imports isolate invalid rows and preserve their raw fields alongside valid neighbors.
- Bounded collection skips already extracted source/context/version combinations across processes. `--refresh` explicitly revisits them; queued review documents are not repeatedly extracted with unchanged rules. Fetch failures remain retryable on the next run.
- Patent parsing uses example-column structure, preserves bounded/unresolved cells, handles separate unit columns and explicit example-per-row tables, and retains original cell coordinates.
- Unique explicit property protocols can be associated beyond shrinkage/thickness; conflicting protocols remain pending. Missing HTML descriptions now expose PDF fallback metadata.
- Operational SDK, XML, archive and document errors are isolated; unexpected programming errors still propagate. Folder ingestion continues after a bad file.

Efficiency changes: deque candidate queues, single artifact read during ordinary aggregation, and lazy one-time legacy receipt indexing. Existing CLI and download compatibility interfaces remain intact; broader acquisition/validation consolidation and graph memory optimization are deferred to avoid unrelated behavior changes.

Validation: **98 tests passed**, lint passed. A fresh real-source demo retains **95 accepted / 62 review** (ten additional patent cells are now preserved), with byte-identical repeat exports. These changes do not make arbitrary PDFs or graphs fully automatic. EPO live authentication and external availability were not exercised; no paid query or billing change was made.

The original findings below describe the pre-fix state and their reproductions.

Verdict at review time: the current pipeline is useful for supported source formats, but does not yet meet unattended heterogeneous extraction requirements. Passing fixture tests are not evidence of general source coverage. This review changes no runtime code or curated data.

## Findings, in priority order

1. **P1: ambiguous temperatures become accepted scalar observations.** `data_mining/normalization.py:69` selects the first temperature match without detecting ranges or multiple conditions. Reproduced `conditions('Shrinkage at 100–150 °C for 1 hour')` returning 150 °C. A synthetic patent with that label produces an accepted 5% shrinkage observation at 150 °C. Require a unique scalar condition; retain ranges/multiple conditions for review unless a table explicitly maps each value to a temperature. Do not split one reported measurement into invented temperature points.

2. **P1: one malformed structured row discards valid neighboring measurements.** `data_mining/structured.py:185` validates the entire import in one loop; `data_mining/pipeline.py:153` replaces the document's output on failure. The second construction in `make_observation` still rejects invalid metadata even after setting pending status. Reproduced two thickness rows, one valid and one with temperature=25/role=unknown: ingestion returned zero accepted and one document review entry. The original bytes survive, but per-row output and structured artifacts are lost. Isolate errors per row and retain raw invalid metadata in review evidence.

3. **P1: bounded collection does not advance across runs.** `data_mining/pipeline.py:463` starts at the beginning of discovery every time and counts already cached/processed documents against the cap. Reproduced three candidates, max_documents=1, two calls: both select candidate 0 and report two remaining. Consult persisted completion/version state or persist a cursor; refresh/retry must be explicit. Completed sources must not indefinitely starve later candidates.

4. **P2: patent value-column detection drops qualified values.** `data_mining/patent_html.py:143` finds the first bare numeric cell rather than using table structure. Reproduced a thickness row containing `≤20`, `21`: the first value disappears and the second loses its example identity. A row containing only bounded values is skipped. Resolve header/data columns first, then parse scalar, bound, range or unresolved cells while preserving every source coordinate.

5. **P2: most patent properties cannot pass automatic protocol resolution.** `data_mining/patent_html.py:175` provides protocol context only for shrinkage and micrometer thickness. Every other property receives `unresolved_test_protocol`, regardless of nearby method text. Reproduced an explicit porosity method and numeric table: pending review. The second real patent fixture produces zero accepted / 46 review rows. Add reusable property/method association rules, including local table context and transposed/multi-header layouts; avoid source-ID-specific patches. Unknown associations must remain reviewable.

6. **P2: common provider failures abort collection instead of preserving other sources.** `data_mining/pipeline.py:451` and `:472` catch a restricted exception set. Verified installed `google.api_core.exceptions.Forbidden` is not in that set; malformed XML and some PDF/parser failures likewise escape. An SDK error during discovery prevents previously discovered Celgard/FSRI candidates from being ingested. Normalize expected provider/parser errors at adapter boundaries and record them independently. Folder ingestion in `pipeline_cli.py:124` also lacks per-file failure isolation. Do not broadly hide programming errors.

## Actual unattended coverage

| Source/view | Current behavior |
| --- | --- |
| Celgard PDFs | Two fixture layouts work without per-file context; extraction mainly expects three columns. Unknown layouts, products and units need review. |
| FSRI | Automated discovery and import for HFM `.tst` SI tables and density CSVs. STA/MCC/Cone data are outside the implemented discovery filter. |
| Patent HTML | Example columns with limited recognized labels/protocols; not general experimental-table extraction. Polymer identity is supplied from context rather than resolved per example. |
| Patent PDF | Table geometry preserved for review, not normalized automatically. Missing HTML description raises before the PDF metadata fallback is returned. |
| Patent discovery | EPO requires one-time credentials; current live authentication was not tested in this review. BigQuery is an explicit alternative with a spending cap. Neither provider paginates beyond the configured search window. |
| PoLyInfo | Authorized local structured import only. Source authorization/mapping is an intentional boundary, not a missing scraping feature. |
| CSV/TSV/XLSX | Canonical columns or explicit mapping; one selected sheet, no general workbook interpretation. |
| Graphs | Saved per-image calibration and curve isolation required. Repeat tracing is automatic; new figures are not. Digitized points are separate artifacts, not automatically integrated into the master. |

## Efficiency and scope

The source package is approximately 4,200 lines across the mining/science modules inspected, with no base runtime dependencies and lazy optional imports. There is no reason to introduce a framework or rewrite the project.

- Fix repeated collection work first: it wastes batch slots even when downloads are cached.
- Replace candidate-list `pop(0)` with deque/iterator round-robin; currently quadratic in each source bucket and materializes all candidates before applying the limit.
- `aggregate` reads every artifact once to check versions, then again to construct rows. Reuse loaded artifacts within a run. Whole-master CSV/Parquet exports are acceptable at current scale; no database is justified yet.
- `DocumentStore.fetch` scans all legacy receipt JSONs on every new remote cache miss. Index legacy receipts once per store or perform an explicit one-time migration.
- Legacy and new acquisition/CLI paths coexist (`sources.read_url/save_download` and `acquisition.HTTPClient/DocumentStore`). Their retry, caching and access behaviors differ. Consolidate behind compatibility wrappers after regression tests; do not simply delete public commands.
- The new master constructs a legacy Observation to reuse validation. Extract shared validation functions when changing validation next; avoid maintaining two independent scientific rule sets.
- Graph tracing converts the full image into floating-point RGB arrays even when the crop is small. Crop first and use bounded-width integer color differences if larger figures become a bottleneck. This is lower priority than extraction correctness.

## Validation and limits

- Existing suite: **83 passed**.
- Ruff on src/tests/demo and `git diff --check`: passed.
- Fresh offline primary-source demo in `tmp/review-demo`: **95 accepted / 52 review**, repeat exports identical.
- Graph demo: 38 retained points, eight ambiguous columns, status review.
- Additional temporary synthetic reproductions confirmed findings 1–5; installed SDK exception inheritance confirmed finding 6.
- No new live downloads, EPO authentication, paid Google queries, publishing or billing changes. This review cannot certify current external availability or arbitrary unseen documents.

Fix findings 1–4 with regression tests first; then broaden reusable table/protocol support and isolate provider failures. Use held-out real documents in multiple layouts to measure extraction coverage. A review queue is necessary for genuine ambiguity, but it should not compensate for systematic parser gaps.
