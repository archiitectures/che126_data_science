# Three additional PE separators — 2026-10-14

Added ENTEK **9EPH, 12EPH and 16EPH**: three new separator products, with
**24 validated scalar property records** (eight per product).

Source: [official ENTEK 2021 lithium separator portfolio, page 2, EPH table](https://entek.com/wp-content/uploads/2021/05/Lithium-Prod-Portfolio-21-04-23.pdf).
These are historical manufacturer typical/nominal values, not current product
specification guarantees or independent specimen measurements. All three are
biaxially oriented PE separators, largely composed of UHMWPE. The wet manufacturing
process does not mean that measurements used electrolyte-soaked specimens.

| Property | 9EPH | 12EPH | 16EPH |
|---|---:|---:|---:|
| Nominal thickness, um | 9 | 12 | 16 |
| Basis weight, g/m2 | 4.6 | 6.2 | 8.1 |
| Nominal porosity, % | 48 | 48 | 48 |
| Air permeability time for 100 ml, s | 75 | 95 | 125 |
| Tensile elongation MD, % | 68 | 68 | 81 |
| Tensile elongation TD, % | 249 | 289 | 284 |
| Shrinkage MD, %, 120 C / 1 hour exposure | 9.5 | 7.5 | 9 |
| Shrinkage TD, %, 120 C / 1 hour exposure | 4 | 2 | 3.5 |

The six shrinkage values have a known exposure temperature, not a known
measurement temperature. The other 18 values have no stated temperature.
No 25 C values or continuous temperature dependence were inferred.

## Outputs

- `separator_observations.csv`: the 24 new validated records.
- `combined_separator_observations.csv`: previous reviewed pass plus this pass;
  **28 separator products, 223 scalar records**. This is a consolidated view,
  not another 223 independent additions. Do not concatenate both run outputs
  with this combined file.
- `coverage.json`: missing-property/temperature report.
- `review.json`: nine withheld force/strength values with printed units and bounds.
- `receipts.json`: preserved source-document URLs, timestamps, hashes and raw paths.
- `extract_reviewed.py`: reproducible transcription/import, using the shared
  validator and coverage tools. Run from repository root; refuses output overwrite.
- `summary.json`, `billing_status.json`: counts and cloud status.

Text extraction was checked against a rendered image of the complete page 2
EPH table. The newer 2024 brochure was also inspected, but it does not provide
this EPH table; it was not used to assert that these older values are current.
The 2021 and 2024 PDFs remain preserved under the hash paths in the receipts.

Added two explicit canonical properties to the schema: `basis_weight` (g/m2)
and `air_permeability_time` (s). The latter retains 100 ml volume in conditions;
we do not assume an unstated Gurley instrument or JIS test method. Puncture
reported in `g` and tensile bounds reported in `kg/cm2` remain in review rather
than silently interpreting mass symbols as force units.

## Google status and verification

Read-only gcloud check returned `billingEnabled: false`, with an empty
`billingAccountName`, for `che126-separators-20261012`. No billing configuration
changed and no Google query was executed. Cloud spend for this pass: **$0**.
The previous automatic-review block on re-linking remains unresolved; the user's
question about whether linkage already existed was answered by inspecting it.

53 tests pass; Ruff and Git whitespace checks pass. New product IDs do not overlap
the prior reviewed collection; CSV round-trip validation passes. Public dry/wet
CSV tables and Hugging Face were not changed; the new data is staged locally.
