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
The two initial CSVs contain column headers only: **zero measured records**.
No example, estimated, or synthetic measurements have been added. The Hub viewer
and automatic dataset loading may remain unavailable until real records exist.

## Separate dry and wet datasets

- `dry_separators.csv` / `dry` subset: separators measured without electrolyte
  soaking. Leave electrolyte and soaking fields blank.
- `wet_separators.csv` / `wet` subset: separators measured while soaked in battery
  electrolyte. Record composition and soaking conditions whenever reported.

Dry/wet here describes the specimen's state during measurement, **not** whether
the separator was manufactured using a dry or wet process. Do not infer state
from manufacturing process. Sources with unclear measurement state need
clarification before entering either table. If a soaked specimen is dried before
testing, put that measurement in `dry` and describe its history in `notes`.

Both CSVs share the same 27 columns. Pair dry and wet measurements from the same
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
| `source_type` | Paper, datasheet, patent, or simulation; identify origin explicitly. |
| `source_url` | DOI link or stable source/document URL. |
| `source_locator` | Document version and page, table, figure, or simulation run. |
| `value_type` | Measured, typical, minimum, maximum, digitized, or simulated. |
| `replicate_id` | Reported replicate identifier; blank for unspecified replicates. |
| `notes` | Original units/values, uncertainty, thermal history, and caveats. |

Temperature during measurement, prior thermal conditioning, and soaking
temperature are distinct quantities. A datasheet thickness or porosity should
not inherit a temperature from an unrelated shrinkage test.

## Curation and access

Hugging Face is the preferred home for the growing property tables. The code
repository keeps these small, versioned starter templates and this dataset card.
The original research notes describe candidate sources; no mining pipeline is
implemented. Future records must retain provenance and distinguish literature,
manufacturer, digitized, and simulation-derived values.

Files can be downloaded directly from the Hub. Once observations exist, use the
`dry` and `wet` configuration names with `datasets.load_dataset`. Neither subset
is currently suitable for training, validation, or physical conclusions.

No dataset-wide license is declared yet. Source-specific reuse terms must be
recorded and reviewed as real records are curated; public hosting does not grant
a new license to third-party source documents.
