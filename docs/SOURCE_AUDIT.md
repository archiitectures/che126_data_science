# Source audit and integration — 2026-10-16

The existing package, commands, raw downloads, wide dry/wet tables, source
snapshots, and staged 223-record separator collection were inspected and retained.
The new workflow uses a separate versioned master schema and explicit manifest.
Existing CSV readers retain their original strict schema.

| Source | Confirmed on real files | Implemented path | Boundary |
|---|---|---|---|
| Celgard | PP1611 is selectable PDF text with one bordered property table on page 1; page 2 is disclaimer/contact material. Z1831 reverses value/unit/label columns. | PyMuPDF table geometry, optional pdfplumber when no tables are found, legacy text fallback. Raw cells, bbox, page and context retained. | Multi-product attribution and unknown units enter review. No generic OCR. |
| Google Patents | US9911958B2 Table 1 is fragmented across nested HTML tables inside `patent-tables`; paragraph p-0080 specifies the 10-minute shrinkage protocol. US20120077113A1 has heterogeneous tables and multi-series figure sheets. | Description-only HTML parsing, span expansion, delimited text-table fallback, experimental context linking. PDF tables are retained for review when HTML fails. | Arbitrary patent PDFs are not automatically assigned experimental semantics. Generic/ambiguous example context stays in review. |
| FSRI | Pinned instrument `.tst` is UTF-16 with BOM and a named SI results section. Density is a small CSV. Public HTML plots contain JSON numeric series. Repository tree provides immutable blob paths. | Direct HFM/density acquisition and parsing; snapshot compatibility. Instrument repeats retained. Source JSON plot helper remains available. | Other apparatus (STA/MCC/Cone) are not normalized automatically; existing archived curves remain available as source evidence. |
| NIMS PoLyInfo | Authenticated database; access page prohibits scraping/mass download. | Explicitly authorized local CSV/TSV/XLSX import with restrictions and source provenance. | No NIMS network crawler. |
| EPO OPS | Official registered-credential XML API, free threshold governed by EPO policy. | OAuth client-credentials discovery and bounded result parsing; credentials stay in environment/memory. | No EPO credentials were present, so live authentication/search was not verified. XML behavior tested offline. |

These findings characterize inspected examples, not the percentage of all source
content stored in a particular format. Public accessibility does not establish
redistribution permission. Unestablished license/reuse status is recorded on each
source; this implementation does not publish datasets or alter billing.

## Verified primary examples

- Celgard PP1611: https://www.celgard.com/storage/components/pp1611_com_data_2026-01.pdf
  SHA-256 `70a180682d0aa6e29aaf8568dae24259c835e852f442baa6d5594c4f9a660064`.
  Twelve scalar records: eight normalized, four tensile values awaiting a force-unit
  interpretation. Calculated porosity remains calculated.
- Celgard Z1831: https://www.celgard.com/storage/components/z1831_com_data_2026-03.pdf
  Five normalized values/bounds and two unresolved tensile units. Direction footnotes
  TD1/MD2 are recognized. This is a membrane product, with applications preserved in
  raw context; no claim of Li-ion qualification is added.
- Patent: https://patents.google.com/patent/US9911958B2/en
  Twelve length-shrinkage values at 130/140/170 C for Example 1 and Comparative
  Examples 1–3, plus four thickness values. Shrinkage is after 10-minute exposure;
  the four reported sample values are not expanded into separate MD/TD observations.
- Graph: https://patents.google.com/patent/US20120077113A1/en, Figure 5.
  A selected segment of Comparative Example 1's TMA curve was manually isolated and
  calibrated. Y is relative length (%), not automatically converted to shrinkage.
- FSRI raw example: https://raw.githubusercontent.com/ulfsri/fsri_materials_database/a432697e4b7d40f642b5cc8f384506439ebb32df/01_Data/HDPE/HFM/HDPE_HFM_Wet_conductivity_210715_R1.tst
  Complete-file decoding reproduces all six SI results. Its snapshot and raw-file
  representations are linked, rather than counted as independent measurements.

## Access and technical references

- https://patents.google.com/robots.txt — individual patent pages allowed; search
  route disallowed. Automated discovery therefore uses EPO OPS or explicit BigQuery.
- https://www.epo.org/en/service-support/ordering/fair-use — OPS free threshold.
- https://link.epo.org/web/searching-for-patents/data/en-ops-v3.2-documentation-version-1.3.20.pdf
- https://polymer.nims.go.jp/ — authenticated access and usage restrictions.
- https://github.com/ulfsri/fsri_materials_database — raw apparatus organization.
- https://pymupdf.readthedocs.io/en/latest/page.html#Page.find_tables

## Demonstration results

`scripts/run_pipeline_demo.py` uses checked-in primary-source fixtures and the
existing pinned FSRI snapshot. It performs no network requests or paid queries.
Fresh demo: 95 accepted records, 52 review records; two runs produce byte-identical
master CSV and Parquet. Forty-six review records come from the deliberately
heterogeneous second patent; six are ambiguous Celgard tensile values.

A separate four-document live smoke test verified Celgard/FSRI discovery and
acquisition. EPO reported missing credentials and continued other sources. The
current main manifest, including these live sources and the demo documents, exports
111 accepted records and 60 review records. These are views of retained evidence,
not 111 newly measured experiments and not an automatic merge of all historical runs.

Graph proof: 38 retained pixel samples, one curve identity, five manually selected
reference points. Mean/max Y error is 0.0592/0.0739 percentage points; X error is zero
at these references. Eight ambiguous columns are flagged, and the output remains
in review. This is reference-point agreement, not a claim of total scientific
uncertainty or validation of an entire multi-series figure.
