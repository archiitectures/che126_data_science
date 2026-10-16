# Automatic pipeline implementation review — 2026-10-16

The new automatic workflow has been implemented and self-reviewed against the
supplied separator mining specification. The earlier review below is historical.

## Correctness findings fixed during implementation

- Kept statistic and evidence type separate. Typical manufacturer properties,
  calculated porosity, limits, claims and measurements cannot silently become the
  same measured-only training set.
- Reconstructed patent headers across split HTML tables and spans. Verified four
  distinct Example/Comparative Example identities and 12 temperature-resolved
  shrinkage values without duplicating them into separate MD/TD measurements.
- Linked shrinkage to its 10-minute exposure protocol and thickness to its
  micrometer method; prevented the shrinkage method from contaminating thickness.
- Retained original unit text and explicit aliases/conversion metadata. PP1611
  yields 12 extracted records, with four ambiguous force/area units queued.
- Added reversed-column PDF handling and TD1/MD2 direction-footnote parsing.
  Laminate microporous-component values use separate sample identities/forms.
- Adopted existing raw receipts, verified cache integrity, and kept unchanged
  requests offline. Local aggregation re-extracts stale parser versions without
  redownloading sources. HTTP errors and missing credentials remain visible.
- Interleaved source candidates so a large FSRI listing cannot starve patent or
  Celgard ingestion under a bounded document limit.
- Linked equivalent FSRI snapshot/raw results and matching patent-family evidence
  while preserving aliases and distinct replicates. Historical combined CSVs are
  not globbed into the master.
- Reserved cumulative BigQuery bytes before submission; uncertain failures consume
  their capped reservation. No billing linkage or paid fallback is automatic.
- Directed PDF-library diagnostics away from the CLI JSON stdout stream.
- Digitization preserves source pixels, calibration, units, curve identity and
  errors; ambiguous columns remain review evidence. Relative length is not
  relabeled shrinkage, and image-sheet indices are not invented figure numbers.

## Verification

- 83 tests pass, including the original 53; Ruff and whitespace checks pass.
- The reproducible offline demo exports 95 accepted / 52 review records. Repeated
  ingestion yields byte-identical CSV and Parquet; measured-only exports contain
  only accepted measured records.
- A bounded live collection verified Celgard and direct FSRI discovery/acquisition;
  the current main export contains 111 accepted / 60 review records. These include
  existing evidence representations and must not be described as 111 new experiments.
- The full UTF-16 FSRI raw-file demonstration reproduces six SI results and dedupes
  against its corresponding pinned snapshot.
- Six directly linked public patent image sheets were saved with caption metadata.
- Real-figure proof: 38 retained samples of one isolated segment, five manual
  reference points, mean/max Y error 0.0592/0.0739 percentage points. Eight ambiguous
  columns keep the output in review. A synthetic calibrated curve passes exact
  reference-point checks; unisolated multi-series input produces no physical points.
- Final six-page guide rendered and visually inspected; command continuation and
  page-layout defects found during authoring were corrected.

## Material boundaries

Live EPO OAuth/search cannot be claimed verified because credentials are absent;
request/XML behavior has offline coverage. NIMS is authorized local import only.
Generic patent PDF experimental semantics and non-HFM FSRI apparatus are not
normalized automatically; raw artifacts remain reviewable. The graph proof is a
manually isolated segment of a multi-series linear plot, with explicit review flags,
not an unattended universal chart reader. Legacy imports require primary-source
verification. No models, uploads or Git pushes were added.

The core remains dependency-free. Optional ingestion, PDF fallback and graph extras
supply only the tools used for this workflow. Reusable code is separated from the
CLI and demonstration, without adding a service, crawler queue or database.

---

# Correctness and scope review — 2026-10-14

Self-review completed after the initial implementation and PDF draft. Findings
below were fixed and regression-tested. This is not an independent external audit.

## Fixed findings

- `data_mining/patents.py`: nested correlated NOT EXISTS could pass a dry run yet
  fail at execution. Replaced with scalar, parameterized AND/OR predicates using
  the shape of the previously successful live query. No new paid query was run.
- `data_mining/patents.py`: a title-only filter still selected abstracts, increasing
  scans. Added explicit titles-only result projection and exclusive-end date bounds.
- `data_mining/patents.py`: US application IDs could yield broken URLs. Pad the
  application serial to seven digits; retain exact source IDs for BigQuery lookup.
- `data_mining/patents.py`: executed result provenance lacked job/cost metadata and
  JSON export overwrote files. Added job ID/bytes and opt-in overwrite.
- `data_mining/sources.py`: naive polyethylene matching included PET. Exclude that
  different polymer and keep acronym boundaries; do not broaden HDPE to all PE.
- `data_mining/sources.py`: a proposed repository metadata-link expansion produced
  404s in live checks. Removed it, along with redundant GitHub-API discovery and
  unused version metadata. Public catalog pagination and saved JSON plots are the
  tested FSRI route; GitHub API rate limits no longer block catalog discovery.
- `data_science/observations.py`: empty CSVs could evade required-header validation.
  Required columns are now checked even when there are no rows.
- `data_science/observations.py`: transition-temperature property values could be
  below absolute zero. Validate these values as well as test temperatures.
- `data_mining/celgard.py`: caller-supplied product identity could disagree with
  the document. Verify it against source text before labeling observations.
- `data_mining/celgard.py`: text from the PDF warranty/contact page polluted the
  unresolved-row report. Preserve page breaks, parse the single supported table
  page, retain its page number, and reject multiple-table layouts for review.
- `data_mining/fsri.py`: generic HFM import must not assume every material is a
  sheet. Default to bulk_reference; accept sample form only when supplied as
  reviewed metadata. Check numeric HFM results for finite/physical values.
- PDF: corrected a flowable-size bug that made the pipeline diagram overlap text;
  visually inspected all six final page layouts.

## Verification evidence

- **53 offline tests passed**, including the original 28 tests with their SQL
  assertions updated for the execution fix.
- Ruff checks passed for `src/` and `tests/`; Git whitespace checks passed.
- Dependency lock verified; wheel and source distribution built successfully.
- Live Celgard discovery: 14 PE-containing product leads. Source PDF saved with
  SHA-256 receipt. Celgard 2400: 8 supported values/bounds and 2 unresolved tensile
  rows. These are not eight temperature-specific experimental measurements.
- Live FSRI search: four PE-related material leads, excluding PET. Saved HDPE page
  exposed 10 JSON figures with axis/trace/error-bar metadata. Curves remain source
  evidence requiring review, not automatically normalized measurements.
- Existing HFM snapshot normalizes to 60 observations: 36 conductivity and 24
  volumetric heat-capacity values, retaining every original reported temperature
  and repeated setpoint. These duplicate existing evidence; do not double-count.
- Public network smoke tests used the system CA bundle with TLS verification.
  GitHub API access was rate-limited; the final catalog path does not use it.
- The optional SDK was mocked in tests; no paid BigQuery execution, billing change,
  public dataset update, Git commit or push was performed for this implementation.

## Remaining boundaries

- NIMS integration is an assisted search/import workflow, not automated retrieval.
  Its access rules prohibit scraping and mass download. Redistributable data
  requires permission: https://polymer.nims.go.jp/.
- Celgard tensile `Kg/cm2` needs source confirmation before interpretation as
  force/area. The parser deliberately does not invent a conversion.
- No general patent-table parser or generic PDF/OCR extractor. Unsupported source
  layouts and apparatus need reviewed fixtures before adding parsers.
- Material search is a lead finder, not exhaustive semantic search. Commercial
  synonyms and unlisted grade names can require additional queries.
- Coverage reports requested evidence per compatible sample/source/condition.
  They do not prove complete material characterization, interpolate temperatures,
  or treat calculated values, bounds and claims as measured coverage.
- The existing manually curated patent JSONs and legacy wide tables have not been
  re-audited value-by-value as part of this tooling review.

## Lean-code assessment

No new base runtime dependency, plugin framework, service, database, crawler queue,
automatic billing mechanism or publishing workflow. One optional PDF reader; the
PDF guide builder uses ReportLab outside the installed runtime. Existing FSRI
wide-table behavior remains separate and tested for compatibility. Tidy examples
are staged, and raw downloads/rendered intermediate files are ignored by Git.

Next additions should start from an actual unsupported source row or a documented
coverage gap, not from a speculative framework.
