# Data validation and analysis

The reusable implementation is in `src/che126_data_science/data_science/`.
`master.py` defines schema 2, validation, normalization, scientific context fields,
stable observation IDs and typed exports. `observations.py` retains the legacy tidy
CSV validator and requested property/temperature coverage calculation.

Use `datasets/master_observations.parquet` for full evidence and
`datasets/unique_points.parquet` for equal-value/context groups. The corresponding
CSVs have identical content. One row is one property; property categories are values
of `property`, not wide columns. All group members are retained in
`datasets/unique_point_evidence.json`.

Deduplication includes method, measurement context, shrinkage basis, grade,
replicate/curve identity, uncertainty and the other scientific fields in
`master.SCIENTIFIC_FIELDS`. It excludes source location and sample identifiers in
the cross-source context view. Equal contexts can still be different experiments;
patent-family independence is not established. Use source/family-aware evaluation
splits only after confirming lineage; do not randomly split repeated source evidence.

Missing numeric temperature is not room temperature. Separate measurement from
exposure conditions; a melting/shutdown property value is not a test temperature.
Filter `sample_form` to distinguish separator/components from bulk references, and
`record_type` to distinguish measured, calculated and specification limits.
`electrolyte_state` concerns measurement state, not manufacturing route.

```sh
.venv/bin/python scripts/export_unique_points.py
.venv/bin/python scripts/audit_dataset.py
.venv/bin/python visualizations/generate_figures.py
```

The audit checks schema, source hashes, units/conversions, export parity and group
membership; source-cell comparisons do not independently certify every scientific
interpretation. See [review findings](../docs/INDEPENDENT_REVIEW.md) before modeling.
Regression models, interpolation and simulation interfaces are not implemented.
