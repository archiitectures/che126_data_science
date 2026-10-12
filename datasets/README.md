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
- config_name: dry
  data_files: dry_separators.csv
- config_name: wet
  data_files: wet_separators.csv
---

# ChE126 battery separator properties

Public dataset: https://huggingface.co/datasets/archiitecture/che126

Code and research notes: https://github.com/archiitectures/che126_data_science

This senior-year chemical engineering capstone tabulates battery separator
**porosity, strength, and size**, with temperature recorded whenever available.
The dry CSV contains **60 FSRI bulk-polyethylene reference observations**
(30 HDPE and 30 LDPE), including thermal conductivity and heat capacity. These
are clearly labeled bulk-sheet references, not battery separator measurements.
The electrolyte-soaked wet CSV still contains **zero records**. No separator
porosity, strength, or pore-size values have been inferred from FSRI thermal data.

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
