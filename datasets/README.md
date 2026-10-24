---
pretty_name: ChE126 Battery Separator Properties
language:
- en
tags:
- chemistry
- materials-science
- battery-separators
- temperature
- porosity
- mechanical-properties
configs:
- config_name: default
  default: true
  data_files: unique_points.parquet
- config_name: observations
  data_files: master_observations.parquet
- config_name: dry
  data_files: dry_separators.csv
- config_name: wet
  data_files: wet_separators.csv
---

# ChE126 battery separator properties

Public dataset: https://huggingface.co/datasets/archiitecture/che126

Code and research notes: https://github.com/archiitectures/che126_data_science

## Current reviewed export

The local dataset contains **8,977 accepted observations** and **5,982 distinct
scientific value/context groups**, across **23 properties**, after the independent
review (`separator-v24`, schema 2). The review moved 15 relative/dispersion values
out of accepted absolute-property records and corrected context grouping. More
context groups do not mean more measurements were collected.

Use `master_observations.csv`/`.parquet` for all accepted evidence and
`unique_points.csv`/`.parquet` for the grouped view. These are tidy tables, one
property per row. `unique_point_evidence.json` preserves all supporting observation
IDs. Method, measurement context, shrinkage basis, material grade, replicate/curve
identity and uncertainty now participate in grouping. Equal recorded contexts can
still represent separate experiments; patent families have not been fully linked.

The source citations include 275 patent publication URLs, 13 literature URLs,
28 Celgard datasheets and 40 FSRI file URLs. There are 349 import/source files:
one curated file can contain several primary sources. These are distinct counting
units, and patent publication count is not patent-family count.

See [independent review](../docs/INDEPENDENT_REVIEW.md) and
[audit results](quality_review.json). The local exports have not been republished
to Hugging Face as part of this review. Missing values remain unknown; bulk
references and calculated/specification records must be filtered appropriately.
For structured imports, `original_value`/`original_unit` describe the imported CSV
cell; primary-document values and hashes can additionally reside in `notes` and
dated curation evidence. A CSV hash alone does not verify the original paper.

The legacy dry/wet tables and their 35-column dictionary below are a separate older
format, not the schema of the master/unique tables. Earlier reports are snapshots.

## Current material identity audit — 2026-10-23

The stored sources have been reprocessed to link separator material recipes to
individual samples, including explicit recipe inheritance, layered composition
tables and reviewed source passages. Current counts and remaining gaps are in the
[material identity report](material_identity_report.md). Earlier collection counts below describe the
snapshot before this identity reconciliation.

Use [`unique_points.csv`](unique_points.csv) for distinct normalized property/context points
and `master_observations.csv` for the full accepted source observations. Corrected
material labels can split or merge distinct contexts; they do not represent newly
collected measurements. The reconciliation checks preserve original values,
units, temperatures, sample labels, directions and protocols.

The CSVs add `material_identity_status`, `material_identity_evidence` and
`material_identity_reason`. A missing `polymer` is accompanied by a specific
linking/evidence gap; it does not by itself establish that the source omitted its
material. The [per-point identity audit](material_identity.csv) and the report's observation lineage
make these assignments traceable. Polymer families outside PE/PP, including
identified fiber composites, remain explicit categories. Current figures and their
reproduction code live in [visualizations](../visualizations/README.md).

## Historical collection snapshot — 2026-10-23 balanced pass

The completed bounded pass contains **3,961 distinct normalized value/context
points** from **8,992 accepted source observations**, net +1,802 contexts from the
2,159-point baseline. Validation confirms all baseline contexts were preserved,
complete evidence links, CSV/Parquet round-trip consistency, and byte-equal dataset
exports. The 2,000-additional-context target was not met. The increase comprises
587 contexts recovered from cached sources/reviewed cached imports and 1,215 from
new sources. Distinct contexts are not independent experiments.

There are 23 property categories and 998 separator points with numeric
measurement/exposure temperatures, up from 488. Across separator records, 20
setpoints span 23–300 °C. Identified PE, PP, PE/PP, and PP/PE/PP records cover 14
setpoints from 23–180 °C; the 250 and 300 °C records have unresolved polymer
identity and do not demonstrate high-temperature performance for identified
polyolefin types. Temperature marginals improved, but occupied cells in the fixed
baseline property × temperature × role grid increased only from 19 to 20. Full
cross-property temperature coverage remains sparse.

The parser version for this pass is `separator-v19`. Property categories are values
in the tidy `property` field, not literal wide columns. New source formats include
patent HTML tables, primary Europe PMC XML, and a reviewed primary author-hosted PDF.
One new specific-heat-capacity category has a single observation. One separator
volumetric heat-capacity value is explicitly calculated as density × specific heat;
it is not an independent experiment. An unnumbered “room temperature” is not
assigned a numeric temperature, and no interpolation is performed.

See the [balanced collection report](collection_balanced_report.md), [run report](../data_mining/runs/2026-10-23_balanced/collection_report.md), and [run README](../data_mining/runs/2026-10-23_balanced/README.md) for property and temperature growth tables, methodology, and limitations. The 2026-10-19 [expansion report](collection_expansion_report.md) and earlier reports remain available as historical snapshots. Pending review records are excluded; source restrictions remain recorded and no dataset-wide license is asserted.
## Separate dry and wet datasets

- `dry_separators.csv` / `dry` subset: measurements without battery electrolyte
  soaking, including explicitly labeled bulk-sheet reference rows. Leave
  electrolyte and soaking fields blank. Select `sample_form != bulk_sheet_reference`
  to exclude these reference observations from separator-specific analysis.
- `wet_separators.csv` / `wet` subset: separators measured while soaked in battery
  electrolyte. Record composition and soaking conditions whenever reported.

Dry/wet here describes the specimen's state during measurement, **not** whether
the separator was manufactured using a dry or wet process. Do not infer state
from manufacturing process. Sources with unclear measurement state need
clarification before entering either table. If a soaked specimen is dried before
testing, put that measurement in `dry` and describe its history in `notes`.

Both CSVs share the same 35 columns (the original 27 plus eight thermal/reference fields). Pair dry and wet measurements from the same
material or specimen using a stable `sample_id`; every row has its own `record_id`.
Hugging Face configurations keep the subsets separate. A library's automatically
assigned `train` split is a storage convention, not an agreed evaluation split.

## Row and missing-value conventions

One row describes a source-reported observation under a specific measurement
condition and direction. Multiple properties may share a row only when source,
specimen, temperature, direction, and protocol apply to all those values. Use
separate rows for different temperatures, directions, tests, or replicates;
leave unrelated property cells blank rather than copying values into new tests.

An empty cell means unreported or not applicable, never zero. Store numeric
values without unit strings. `porosity_pct` uses 0–100 percent, not a 0–1 fraction.
Do not guess room temperature. Preserve original values/units, conversion notes,
uncertainties, and unusual protocols in `notes` until dedicated fields are needed.
Only enter strength in a canonical column when its definition and unit match;
for example, tensile force in N is not tensile stress in MPa.

## Column dictionary

| Column | Meaning |
| --- | --- |
| `record_id` | Unique observation identifier across both files. |
| `sample_id` | Stable specimen/material identifier for linking conditions. |
| `material` | Polymer/material composition, such as PE or PP. |
| `separator_type` | Construction, multilayer arrangement, or coating. |
| `product_name` | Manufacturer/product designation when known. |
| `temperature_C` | Temperature during the reported property measurement, °C. |
| `conditioning_temperature_C` | Prior heat-treatment temperature, °C, if distinct. |
| `conditioning_duration_h` | Duration of that prior heat treatment, hours. |
| `porosity_pct` | Reported void fraction, percent; retain method/context. |
| `tensile_strength_MPa` | Ultimate tensile stress, MPa; exclude yield stress. |
| `puncture_strength_N` | Force at puncture, N; exclude pressure or stress. |
| `thickness_um` | Separator thickness, µm, under the recorded condition. |
| `pore_size_um` | Reported pore size, µm; identify mean/median/max in notes. |
| `measurement_direction` | MD, TD, through-plane, or source-specific direction. |
| `porosity_method` | Porosity measurement method and relevant conditions. |
| `strength_method` | Strength test method, geometry, rate, and loading details. |
| `size_method` | Thickness/pore-size method, load, and size statistic. |
| `electrolyte_composition` | Salt, concentration, solvents/ratios, and additives. |
| `soaking_time_h` | Electrolyte soaking duration, hours; wet observations only. |
| `soaking_temperature_C` | Electrolyte soaking temperature, °C; wet only. |
| `source_id` | Stable source identifier, shared by observations from that source. |
| `source_type` | Paper, datasheet, patent, simulation, or `public_materials_database`; identify origin explicitly. |
| `source_url` | DOI link or stable source/document URL. |
| `source_locator` | Document version and page, table, figure, or simulation run. |
| `value_type` | Measured, typical, minimum, maximum, digitized, simulated, or `measured_and_calculated`; notes identify calculated fields. |
| `replicate_id` | Reported replicate identifier; blank for unspecified replicates. |
| `notes` | Original units/values, uncertainty, thermal history, and caveats. |
| `sample_form` | Explicit specimen category; `bulk_sheet_reference` for these FSRI observations. |
| `source_condition` | Source's original conditioning terminology and its meaning. |
| `reference_thickness_um` | Instrument file-header specimen thickness, µm; temperature unspecified. It is not a thermal thickness curve. |
| `thermal_conductivity_W_m_K` | Reported HFM Average Cond, W/(m K). |
| `volumetric_heat_capacity_J_m3_K` | Measured HFM heat capacity per unit volume, J/(m³ K). |
| `specific_heat_capacity_J_kg_K` | Calculated mass-specific heat capacity, J/(kg K); retain conversion in notes. |
| `reference_density_kg_m3` | Arithmetic mean of the source's three density replicates used for conversion, kg/m³; not a temperature-dependent density measurement. |
| `thermal_method` | Thermal-property apparatus, test, and relevant protocol. |

Temperature during measurement, prior thermal conditioning, and soaking
temperature are distinct quantities. A datasheet thickness or porosity should
not inherit a temperature from an unrelated shrinkage test.

## Curation and access

Hugging Face is the preferred home for the growing property tables. The code
repository keeps small versioned tables, this dataset card, and acquisition
utilities. The FSRI result-table excerpts are pinned to a source commit for
reproducibility. Future records must retain provenance and distinguish literature,
manufacturer, digitized, and simulation-derived values.

Once these files are published on the Hub, use the `dry` and `wet` configuration
names with `datasets.load_dataset`. The wet subset is empty. FSRI bulk-sheet
references alone do not establish separator behavior.

No dataset-wide license is declared yet. Source-specific reuse terms must be
recorded and reviewed as real records are curated; public hosting does not grant
a new license to third-party source documents.


## FSRI polyethylene coverage and provenance

Source: UL Research Institutes, Fire Safety Research Institute, Materials and
Products (MaP) Database. [Website](https://materials.fsri.org/),
[experimental methods](https://materials.fsri.org/experimentalmethodology), and
[repository citation](https://github.com/ulfsri/fsri_materials_database/blob/a432697e4b7d40f642b5cc8f384506439ebb32df/CITATION.cff).
Source commit: `a432697e4b7d40f642b5cc8f384506439ebb32df`.

| Material | Conductivity observations | Heat-capacity observations | Total |
| --- | ---: | ---: | ---: |
| HDPE | 18 | 12 | 30 |
| LDPE | 18 | 12 | 30 |

All numeric rows in the 12 HFM SI result tables are included: conductivity at
**15.01 and 45.01 °C**, and heat capacity at **10.00, 20.01, 30.01 and 40.01 °C**.
Reported temperatures are not rounded to nominal setpoints. Each conductivity
file has six results, alternating between its two temperatures three times.
These repeated setpoints are retained separately and must not be counted as six
independent specimen replicates. Each heat-capacity file has four reported
results; its five programmed setpoints include an initial step without a
reported heat-capacity result, so no fifth value is invented.

Coverage is the HFM thermal-property series. STA/MCC powder decomposition and
combustion time series are not imported as separator measurements. Each row
links to its exact source file at the pinned commit, records its blob SHA and SI
result-table data-row number, and identifies the source replicate.

FSRI calls these samples “Wet” because they were unconditioned with ambient
moisture. They are included in our dry table as **bulk-sheet references without
battery electrolyte**, by project decision. The wet CSV is reserved for actual
battery-electrolyte-soaked measurements. This does not imply that FSRI performed
oven drying on these specimens.

Instrument header thicknesses (3170–3380 µm) are recorded only in
`reference_thickness_um`. The source does not establish a temperature-dependent
thickness measurement, so `thickness_um` stays blank along with separator
porosity, strength, and pore size.

The raw heat-capacity unit is J/(m³ K). To provide J/(kg K), divide by the mean
of the three source density records: HDPE `(974 + 970 + 970) / 3` and LDPE
`(925 + 930 + 927) / 3` kg/m³. This follows the mean-density normalization in
FSRI's [HFM processing script](https://github.com/ulfsri/fsri_materials_database/blob/a432697e4b7d40f642b5cc8f384506439ebb32df/02_Scripts/plot_HFM_data.py).
Calculated specific heat is rounded to 0.001 J/(kg K); this rounding does not
represent an uncertainty estimate. The original volumetric measurement and
density inputs are preserved. `value_type=measured_and_calculated` identifies
these rows. LDPE density file column labels say HDPE_WET despite their LDPE
paths; the inconsistency is recorded in affected row notes.

The [source excerpts](../data_mining/fsri_polyethylene_hfm_extract.json) retain
complete SI result tables, file-header excerpts, and all six density CSVs.
`che126_data_science.data_mining.fsri.polyethylene_reference_rows(snapshot)`
reproduces the reference records without network access or third-party runtime
dependencies. Original UTF-16 file blob hashes were verified during acquisition.
