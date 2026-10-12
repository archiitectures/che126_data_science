# Data mining: initial research notes

Research date: 2026-10-12. Scope derives from the
[project handoff](../docs/CODEX_DATA_SCIENCE_HANDOFF.md). This folder holds planning
notes only. No scraper, extraction pipeline, source database, or dataset has
been implemented. Future acquisition utilities belong in
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

Sources 1 and 2 were inspected directly; 3 and 4 remain leads. No patent or
standard has been audited yet. Do not infer universal PE/PP failure temperatures
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
