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

The package now supports a manifest-driven automatic source-to-master workflow,
EPO patent discovery, existing Google BigQuery searches, public FSRI and Celgard discovery,
NIMS PoLyInfo assisted search, raw-document preservation, strict observation CSV
cleaning, typed CSV/Parquet master exports, review queues, calibrated curve tracing,
and temperature/property coverage reports. The base install has no
runtime dependencies; BigQuery and PDF text extraction use optional extras.

Run `uv run python scripts/run_pipeline_demo.py` after installing the `ingest` and
`graph` extras for a repeatable offline demonstration.

Start with the [collection guide](docs/COLLECTION_GUIDE.md) or the
[illustrated codebase PDF](output/pdf/codebase_guide.pdf). The existing published
wide tables remain unchanged: 60 bulk-polyethylene reference rows in the dry
CSV and an empty electrolyte-wet CSV. New tidy examples are staged separately
in `data_mining/examples/`; they are not additional independent measurements.

Property data will live in the public
[Hugging Face dataset](https://huggingface.co/datasets/archiitecture/che126), with
separate **dry** and **wet (electrolyte-soaked)** subsets. Initial tables focus on
porosity, tensile/puncture strength, thickness, and pore size, with measurement
temperature whenever reported. See the [dataset card](datasets/README.md) for
column definitions, reference-data coverage, and source provenance. Wet/dry describes
measurement state, independently of manufacturing process.

```text
che126_data_science/
├── data_mining/README.md          # Source leads and future curation notes
├── data_science/README.md         # Analysis questions and proposed data contract
├── docs/CODEX_DATA_SCIENCE_HANDOFF.md
├── datasets/
│   ├── README.md                  # Hugging Face card and column dictionary
│   ├── dry_separators.csv          # Dry data and labeled bulk-sheet references
│   └── wet_separators.csv          # Empty electrolyte-soaked measurement table
├── src/che126_data_science/
│   ├── __init__.py
│   ├── data_mining/patents.py     # Patent search, retrieval, and JSON export
│   ├── data_mining/sources.py     # Public discovery and hashed downloads
│   ├── data_mining/fsri.py        # HFM and public curve parsing
│   ├── data_mining/celgard.py     # Conservative datasheet extraction
│   ├── data_science/observations.py # Tidy validation and coverage
│   └── __main__.py               # Command-line workflow
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
available immediately. The imports above verify setup. Patent acquisition is documented in
[data_mining/PATENTS.md](data_mining/PATENTS.md); cleaning and coverage are documented in the collection guide. Build distributable artifacts with `uv build`.
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

## Next research phase

Inspect coverage gaps before collecting more sources. Requested temperatures do
not guarantee measurements exist at those conditions. Keep source/sample/form,
electrolyte state, direction, methods and conditioning distinct. Add parsers only
when real source examples justify them, then test against those fixtures. Modeling
comes after adequate coverage and provenance, not before.
