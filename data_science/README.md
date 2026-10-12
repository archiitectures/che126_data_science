# Data science: initial research notes

Research date: 2026-10-12. Based on the
[project handoff](../docs/CODEX_DATA_SCIENCE_HANDOFF.md) and the
[initial source review](../data_mining/README.md). Future library code belongs in
`src/che126_data_science/data_science/`. No cleaning, validation, modeling, or
simulation interface is implemented yet.

## Initial questions

How does shrinkage change with temperature within a material and construction?
Do machine and transverse directions respond differently? How do coatings and
multilayers change the response under comparable test conditions? Which sources
measure pore shutdown, and which measure dimensional or mechanical failure?
Are there enough matched transport and mechanical measurements to examine
tradeoffs without pooling incompatible tests?

The [Celgard 2325 datasheet](https://www.celgard.com/storage/components/2325_com_data_2026-01.pdf)
provides one temperature/duration condition with directional shrinkage, rather
than a curve. The [TA463 experiment](https://www.tainstruments.com/applications-notes/modulated-thermomechanical-analysis-mtma-of-polypropylene-battery-separator-film/)
demonstrates that thermal expansion and irreversible contraction can coexist.
Our analysis implication is to retain direction and thermal history and to avoid
assuming every response is monotonic or solely a function of temperature.

## Proposed measurement contract, to confirm with real examples

Prefer a tidy observation table: one property measurement per sample, test
condition, direction, and replicate, with stable links to sample and source
metadata. This is a proposal, not a fixed schema. It may be simpler initially to
keep manually curated tables wide, as suggested in the handoff, then reshape for
analysis. Do not mix specimen temperature, heat-treatment temperature, and a
reported transition temperature in one column without labeling their roles.

| Field group | Proposed content |
| --- | --- |
| Identity | `source_id`, `sample_id`, product, material, separator construction, coating |
| Measurement | property name, raw value/unit, normalized value/unit, uncertainty, replicate, value role (measured/typical/bound/digitized) |
| Conditions | temperature °C, temperature role, direction, duration, heating rate, load, constraint, wet/dry state, electrolyte, atmosphere, thermal history, method |
| Provenance | source type, DOI/URL/document/version, page/table/figure, extraction method, notes |

Candidate property names from the handoff include thickness (µm), porosity (%),
pore size (µm), thermal conductivity (W/(m·K)), shrinkage (%), tensile strength
and elastic modulus (MPa), electrolyte uptake (%), and shutdown/melting
temperatures (°C). Permeability and ionic resistance need explicit method,
units, and geometry before selecting canonical representations. Directional
length shrinkage and area shrinkage must remain distinct. Source-reported onset,
peak, and rupture definitions should remain explicit.

## Analysis plan when measurements exist

1. Audit source coverage, missingness, units, duplicate observations, and test
   comparability before plotting pooled data.
2. Plot each property against temperature by material/construction, separating
   directions and protocols. Display source uncertainty and data coverage.
3. Compare materials within matched conditions first. Examine outliers against
   the source before excluding them. Preserve provenance in derived tables.
4. Only after sufficient coverage, establish simple regression baselines or
   interpolation within supported ranges. More complex models require evidence
   that they improve evaluation and are justified by dataset size.
5. Group repeated measurements and related material/product families when
   splitting data; keep copied source records together. Fit preprocessing on
   training data only. Choose source-held-out or material-held-out evaluation
   according to the intended prediction task.
6. Report MAE/RMSE and R² where meaningful, with units and uncertainty when
   supported. Avoid implying that separator-level property predictions prove
   cell-level thermal-runaway safety.

## Proposed boundary with the simulation repository

Request tidy CSV/JSON outputs with run ID, sample/material ID, property, units,
temperature, direction, method/model, run parameters, seed if relevant, code
revision, and uncertainty/replicate information. Preserve atomistic versus
continuum origin and distinguish model predictions from experiments. Agree on
property definitions and spatial/time aggregation before merging measurements.
Adapters should consume documented outputs from the separate repository; they
should not launch or implement physical simulations here.

## First implementation gate

Review a small manually curated example table and one real simulation output,
then agree on units and required provenance. Implement only the schema,
validation, loaders, and plotting utilities those examples need. Use shared
functions for transformations and classes for meaningful state, avoiding copied
notebook logic and speculative abstraction. Raw/interim/processed storage and
data versioning are future decisions; no populated data folders exist yet.
