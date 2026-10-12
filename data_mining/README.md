# Data mining: initial research notes

Research date: 2026-10-12. Scope derives from the
[project handoff](../docs/CODEX_DATA_SCIENCE_HANDOFF.md). This folder holds research and usage notes. The package now includes a
Google Patents BigQuery client; see [setup and examples](PATENTS.md). Property
extraction and bulk harvesting remain deferred. The dry CSV now includes 60 explicitly labeled FSRI polyethylene bulk-sheet
thermal reference observations; the wet CSV is empty. See the [dataset card](../datasets/README.md). Hugging Face is the
preferred data host at https://huggingface.co/datasets/archiitecture/che126.
Keep dry and electrolyte-soaked measurements separate, focusing first on
porosity, strength, and size with reported measurement temperatures.
Reusable acquisition utilities belong in
`src/che126_data_science/data_mining/`.

## What we want to collect later

Temperature-dependent measurements for PE, PP, multilayer PP/PE/PP, and coated
separators. Start with thermal shrinkage, porosity/pore structure, mechanical
strength, shutdown, and loss of integrity. Thermal conductivity, transport,
electrolyte uptake, and electrical/ionic measurements may follow where sources
provide enough test context. Papers and supplements, manufacturer datasheets,
patents, testing documents, and public materials databases are candidate sources.

## Sources checked and candidate leads

1. **Celgard 2325 manufacturer datasheet (2026 version).**
   [Technical data, page 1](https://www.celgard.com/storage/components/2325_com_data_2026-01.pdf).
   This PP/PE/PP product reports 25 µm thickness and calculated porosity of 39%.
   At 105 °C for one hour, typical transverse shrinkage is 0%, while machine
   direction shrinkage is 3% typical and 5% maximum. These are product-level
   descriptors and one thermal test condition, not a temperature curve or
   independent replicate observations. The PE layer supplies shutdown behavior;
   PP outer layers provide melt integrity. No numeric shutdown threshold is
   given on that page.
2. **TA Instruments application note TA463, Celgard 2400 PP film.**
   [Modulated thermomechanical analysis](https://www.tainstruments.com/applications-notes/modulated-thermomechanical-analysis-mtma-of-polypropylene-battery-separator-film/).
   The experimental table records direction-sensitive measurements under
   0.02 N load, a 1 °C/min ramp, and nitrogen purge. It separates reversible
   expansion from irreversible relaxation/contraction. Useful evidence that
   temperature alone is insufficient to describe a measurement. Application
   notes should retain their source type, separately from peer-reviewed papers.
3. **Moghim et al. (2022), heat-treated PP separators.**
   [Publisher article, DOI 10.1002/pen.26084](https://4spepublications.onlinelibrary.wiley.com/doi/full/10.1002/pen.26084).
   Search-result/abstract lead for thermal treatment, mechanics, and ionic
   conductivity. Full methods and any reusable tables still need inspection.
4. **Thermal shrinkage and microscopic shutdown mechanism of PP (2018).**
   [Publisher record](https://www.sciencedirect.com/science/article/pii/S0376738817313820).
   Search-result/abstract lead for in-situ ultra-small-angle X-ray scattering and
   pore shutdown. Verify full-text access, temperature protocol, and data
   availability before extracting observations.

Sources 1 and 2 were inspected directly; 3 and 4 remain leads. Individual patents and standards still need manual review. Do not infer universal PE/PP failure temperatures
from a product-specific test or treat manufacturer typical/max/min values as
sample-level replicates.

## Future manual curation checklist

- Record a stable source identifier, source type, DOI/patent/document URL,
  access date, document version, and exact page/table/figure.
- Preserve raw value and unit alongside any normalized value. Distinguish
  measured, digitized, estimated, and simulated results; record uncertainty.
- Record product/sample identity, construction/coating, thickness, and
  measurement direction (MD, TD, through-plane, or unspecified).
- Capture temperature, hold duration, heating rate, load/constraint, atmosphere,
  electrolyte/wet or dry state, thermal history, and measurement method.
- Separate linear from area shrinkage and document the calculation/sign
  convention. Keep typical values, bounds, and replicates explicitly distinct.
- Keep porosity measurement method, permeability method, and ionic measurement
  units/geometries explicit. A Gurley time is not an intrinsic permeability.
- Missing means unreported, not zero. Track contradictory or duplicate sources
  and whether a paper reuses a commercial datasheet value.

## Decisions still open

Choose a small first material set and temperature window after reviewing source
coverage. Agree on manual table format and provenance conventions before
building extraction tools. The handoff's suggested schema is a starting point;
the [data science notes](../data_science/README.md) outline the unresolved choices.


## FSRI Materials and Products Database

Inspected 2026-10-12: [public website](https://materials.fsri.org/),
[GitHub repository](https://github.com/ulfsri/fsri_materials_database),
[experimental methods](https://materials.fsri.org/experimentalmethodology), and
[analysis methods](https://materials.fsri.org/analysismethodology).

The database supports fire investigation/modeling. Its HDPE, LDPE, and PP entries
are relevant polymer background, but the inspected samples are commercial sheets
approximately 3.2–3.3 mm thick, not porous battery separator films. Metadata
includes sample source and density; available properties include thermal
conductivity, heat capacity, melting/decomposition behavior, mass loss, and
combustion measurements. The inspected entries do not provide separator
porosity, tensile strength, puncture strength, or pore-size measurements.
Specimen dimensions are sample geometry, not separator pore size.

**FSRI's “Wet” means unconditioned ambient-moisture material.** “Dry” samples are
oven-conditioned at 105 °C for at least 48 hours and stored in a desiccator.
These labels must not map automatically to our electrolyte-soaked/dry separator
CSV categories. FSRI thermal data can inform background research, but should
remain outside those tables unless specimen identity and relevance are verified.

Repository access map:

- `global.json`: property descriptions and repository layout.
- `01_Data/<material>/material.json`: material identity, aliases, source,
  density, and relative links to processed property tables/graphs.
- `01_Data/<material>/`: apparatus-organized raw measurements and metadata;
  relevant apparatus include HFM, STA, MCC, FTIR, and cone calorimetry.
- `03_Charts/`: output location for generated visualizations/tables; only its
  README is currently committed. The processing scripts generate reduced CSVs
  under `01_Data/` and charts under `03_Charts/`. Metadata links describe the
  website outputs, not necessarily files checked into GitHub.
  `02_Scripts/` contains FSRI processing code. Reuse the source data rather than
  importing their complete plotting/processing stack into this package.
- `04_Documentation/` and `CITATION.cff`: supporting documentation/citation.

Example inspected metadata:
[HDPE](https://github.com/ulfsri/fsri_materials_database/blob/main/01_Data/HDPE/material.json),
[LDPE](https://github.com/ulfsri/fsri_materials_database/blob/main/01_Data/LDPE/material.json),
and [PP](https://github.com/ulfsri/fsri_materials_database/blob/main/01_Data/PP/material.json).
The PP entry's short description says PVC despite its material name, longer
description, and source identifying PP; retain this inconsistency as a source
quality note rather than silently treating that field as authoritative.

The pinned polyethylene HFM source-table excerpts are now saved in
`fsri_polyethylene_hfm_extract.json`. A small dependency-free parser in the
package generates reference rows for all reported HFM temperatures, including
repeated setpoints. See the dataset card for coverage and mass-specific heat
normalization. No general FSRI network connector is implemented. Before later
reuse, select an actual apparatus/file example, preserve temperature, heating
rate, atmosphere, conditioning and replicate information, record the source
commit, and verify applicable reuse terms before republishing data.
