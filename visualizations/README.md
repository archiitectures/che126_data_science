## Current figures — 2026-10-30

Figures use 10,582 contexts / 5,110 numeric temperatures. Figure 02 uses 5 °C display bins because native curves contain 928 distinct recorded temperatures; exact values remain in the data and `tables/exact_temperatures.csv`. Bulk-reference ramp samples share curve IDs and are not independent experiments.

# Dataset visualizations

Code, figures and underlying count tables for `datasets/unique_points.csv`.
Each CSV row counts once: a distinct normalized property/value/context, which does
not establish an independent experiment. Figures use categorical count bars
rather than continuous bins so exact temperature setpoints remain visible.

## Generate

From the repository root:

```sh
uv pip install --python .venv/bin/python -r visualizations/requirements.txt
.venv/bin/python visualizations/generate_figures.py
```

The script also runs from another working directory. Optional `--input PATH` and
`--output-dir PATH` arguments select another distinct-points CSV and figure folder.
Tables and `summary.json` are written beside the figure folder. The summary records
the input SHA-256 and counts so generated artifacts can be tied to a data snapshot.

## Figures

1. [Separator types](figures/01_separator_types.png): PE, PP, PE/PP, PP/PE/PP,
   other identified polymer families, types not yet linked and bulk references.
2. [Exact temperatures](figures/02_exact_temperatures.png): counts at every numeric
   setpoint, stacked by measurement/exposure/unknown role; missing temperatures are
   reported in the title. Bulk references are included and decimals are preserved.
3. [Properties by separator](figures/03_properties_by_separator.png): property
   totals stratified by separator type, with bulk references separately colored.
4. [Property × temperature coverage](figures/04_property_temperature_coverage.png):
   separator/component records only, including types not yet linked. Counts combine
   measurement and exposure conditions; dots mark empty cells. Color is logarithmic.
5. [Collection metadata](figures/05_collection_metadata.png): extraction method,
   record type and sample scope from each point's representative observation.
6. [Material identity gaps](figures/06_material_identity_gaps.png): specific reasons
   why a material type has not been linked, taken from the current identity audit.

Every figure is exported as PNG and editable SVG; corresponding counts live in
`tables/`. Unknown temperatures are never assigned to room temperature. Melting and
shutdown temperature property values are not treated as test conditions. The
high-temperature records can describe composite fiber systems rather than pure
PE/PP. PE includes coated PE; components are grouped by their recorded polymer, and bulk references are kept
outside separator categories. `manual_structured_import` describes extraction,
not the original document type; those records include patents and research papers.
Material categories are discovered from the CSV so newly identified polymer
families appear explicitly. "Type not linked" refers to the per-point
`material_identity_status` and `material_identity_reason`; it does not establish
that a patent failed to disclose its material.
