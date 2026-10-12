# ChE126: battery separator data science

Senior-year chemical engineering capstone studying how lithium-ion battery
separator properties change with temperature, with an EV-battery focus.
This repository owns the data science layer. Atomistic and continuum simulations
belong in a separate repository; their outputs will eventually be upstream data.

The initial research question is: **How do separator construction and test
conditions affect temperature-dependent shrinkage, transport, and mechanical
integrity?** The handoff frames a possible failure pathway from thermal or
mechanical stress through pore collapse or shrinkage, loss of isolation, internal
shorting, and possible thermal runaway. Pore shutdown and loss of mechanical
integrity must be tracked as distinct outcomes.

## Current scope

This is an installable, dependency-free package skeleton and initial research
notes. Data mining infrastructure, validation, loaders, preprocessing, datasets,
notebooks, predictive models, and simulation adapters are deferred.

```text
che126_data_science/
├── data_mining/README.md          # Source leads and future curation notes
├── data_science/README.md         # Analysis questions and proposed data contract
├── docs/CODEX_DATA_SCIENCE_HANDOFF.md
├── src/che126_data_science/
│   ├── __init__.py
│   ├── data_mining/__init__.py    # Future reusable acquisition code
│   └── data_science/__init__.py   # Future reusable analysis code
├── pyproject.toml
└── uv.lock
```

Start with [data mining notes](data_mining/README.md),
[data science notes](data_science/README.md), and the
[original project handoff](docs/CODEX_DATA_SCIENCE_HANDOFF.md).
The Markdown handoff is the supplied project background.

## Setup with uv

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then:

```bash
git clone git@github.com:archiitectures/che126_data_science.git
cd che126_data_science
uv sync --locked
uv run python -c "import che126_data_science.data_mining; import che126_data_science.data_science"
```

Python 3.12 or newer is supported; `.python-version` selects 3.12 for development.
`uv sync` installs the local package in editable mode, so library edits are
available immediately. The imports above verify setup; the namespaces do not
yet expose analysis functions. Build distributable artifacts with `uv build`.
Another project can install this package with
`uv add git+ssh://git@github.com/archiitectures/che126_data_science.git`.

## Keep it light and modular

- Put reusable logic in small, focused modules under `src/che126_data_science/`.
  Notebooks should call the package rather than copy its implementation.
- Prefer functions for transformations and analysis. Use classes when they own
  meaningful state or shared behavior; avoid frameworks and empty abstractions.
- Add dependencies only when a concrete task needs them, using `uv add`;
  development tools belong in `uv add --dev`. Commit `uv.lock` with changes.
- Preserve original values, units, test conditions, and source provenance.
  Never silently overwrite raw data. Keep future raw, interim, and processed
  data separate; establish storage/versioning before committing datasets.
- Use lightweight Python configuration and deterministic operations where
  practical. Add focused pytest checks when preprocessing or modeling utilities
  exist, especially for unit conversion, validation, and leakage prevention.
- Keep simulation implementations in the simulation repository. Define adapters
  here only once actual upstream output examples are available.

## Next agreed phase

When data collection is authorized, manually inspect a small set of sources,
agree on measurement granularity and units, and then implement the minimum
schema, validation, and loaders needed for those examples. Follow with property
versus temperature analysis. Modeling comes after data coverage and provenance
are adequate. Research notes are starting hypotheses and source leads, not a
validated property database.
