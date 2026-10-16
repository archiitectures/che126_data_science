# PE / PP collection pass — 2026-10-14

Public-source collection and validation completed. Google dry runs completed;
execution is awaiting explicit billing-link approval after automatic review
rejected the temporary linkage. No billable Google query ran in this pass.

## Validated scalar records

| Category | This pass | New vs previous local examples |
|---|---:|---:|
| PE-containing PP/PE/PP separator films | 111 | 111 |
| PP separator films | 88 | 80 |
| Bulk-reference HFM thermal aggregates | 26 | 14 |

The 199 separator scalar records cover 25 products. They comprise 124 typical
values, 25 calculated porosities, 26 maxima and 24 minima. These are manufacturer
properties/specifications, not 199 independent experimental measurements.
Properties: 25 thickness, 25 Gurley time, 25 porosity, 76 shrinkage values/bounds,
and 48 puncture-force values/bounds. Eight Celgard 2400 records were already
collected in the prior example and are not new.

Shrinkage conditions are 105 C or 120 C exposure for one hour. The other 123
separator records have unspecified measurement temperature. PE products are
trilayer composites, including one ceramic-coated product, not pure PE films.
Product construction is retained in notes. Electrolyte state remains unknown.

The 26 HFM aggregates cover HDPE, LDPE, PP and PE foam at reported temperatures
10, 15, 20, 30, 40 and 45 C. Twelve HDPE/LDPE aggregates overlap existing raw HFM
evidence; do not double-count them. Six PP and eight PE-foam aggregates are new
relative to the existing collection. Aggregates are labeled calculated and kept
separate from individual source measurements.

## Files

- `separator_observations.csv`: reviewed separator scalar records.
- `bulk_thermal_aggregates.csv`: source HFM plotted aggregates, including error-bar
  values in notes; bulk references, not film separator measurements.
- `coverage.json`: explicit requested-grid gaps at 25, 60, 90, 105 and 120 C.
- `summary.json`: counts and current Google status.
- `discovery.json`, `source_reports.json`: source cards, acquisition receipts,
  parser limitations and unresolved rows. Raw bytes remain locally in `data/raw`.
- `*_curves.json`: 45 archived FSRI figures, with trace labels, axes and error bars.
  These include time-dependent fire tests and temperature-dependent decomposition.
  Temperature trajectories reach 748.9 C for PEX; they are not equilibrium
  separator-property measurements or thousands of independent specimens.
- `celgard_observations.csv`: initial automatic extraction, retained for audit.
  Prefer the reviewed `separator_observations.csv` for downstream use.
- `laminate_component_review.csv`: 16 records withheld because 4560/5550 table
  values describe the microporous component, while the products also include
  nonwoven backing. Do not treat component thickness as total laminate thickness.
- `collect_public.py`, `clean_public.py`: commands used for this pass, run from
  repository root. Intended as an audit trail; existing outputs refuse overwrite.
- `google_estimates.json`: two title-only patent searches, each estimated at
  43,845,555,045 bytes. Prepared execution caps are 50,000,000,000 bytes each.

## Manual review and limitations

Q18G1SY uses lowercase 'calculated' and a different degree-symbol/spacing format.
Five additional values were manually transcribed from page 1 of the preserved
PDF: porosity 53%; MD shrinkage typical/max 2.5/8%; TD shrinkage typical/max 0/1.5%,
after one hour at 120 C. Source locators and manual-review notes identify these.

Tensile `Kg/cm2` rows remain unresolved; no force-unit assumption was made.
Z1831 has a reversed-column PDF layout and lists general membrane applications;
it was archived but not imported. The combined 3419S/3420 sheet is multi-product,
NiCd-specific and has ambiguous shrinkage labeling; it was also held for review.
Wettability, shelf life and moisture rows remain source evidence outside this
pass's supported property schema. NIMS was not scraped or automatically accessed.

## Google budget

Official US on-demand rate checked for this pass: $6.25/TiB:
https://cloud.google.com/bigquery/pricing.
Two estimates total approximately $0.4985 before free-tier/trial credits.
Two proposed 50-billion-byte execution caps total approximately $0.5685, below
the authorized $2 run budget. No paid full-text lookup is planned.

The project was verified billing-disabled before the pass. Automatic approval
review rejected re-linking account 017AD5-6FFC2C-4A60B8 without explicit permission
for this run and flagged cleanup-failure risk. Pending plan: temporarily link,
execute exactly the two capped searches, disable billing, verify disabled state.
No billing linkage command executed. No dataset upload or Git push was performed.
