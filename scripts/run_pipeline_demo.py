"""Reproducible primary-source demo; no LLM or paid API.

Run: uv run --extra ingest --extra graph python scripts/run_pipeline_demo.py
"""

import argparse
import json
from pathlib import Path

from che126_data_science.data_mining.digitize import digitize
from che126_data_science.data_mining.pipeline import Pipeline


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/demo"))
    args = parser.parse_args()
    fixtures = Path("tests/fixtures/pipeline")
    pipeline = Pipeline(args.data_dir)
    inputs = [
        (
            "celgard",
            fixtures / "pp1611.pdf",
            {
                "source_url": "https://www.celgard.com/storage/components/pp1611_com_data_2026-01.pdf"
            },
        ),
        (
            "celgard",
            fixtures / "z1831.pdf",
            {
                "source_url": "https://www.celgard.com/storage/components/z1831_com_data_2026-03.pdf"
            },
        ),
        ("fsri", Path("data_mining/fsri_polyethylene_hfm_extract.json"), {}),
        (
            "patents",
            fixtures / "US9911958B2.html",
            {"source_url": "https://patents.google.com/patent/US9911958B2/en"},
        ),
        (
            "patents",
            fixtures / "US20120077113A1.html",
            {"source_url": "https://patents.google.com/patent/US20120077113A1/en"},
        ),
    ]
    results = [
        pipeline.ingest(source, path, context=context)
        for source, path, context in inputs
    ]
    first = pipeline.aggregate()
    paths = [
        args.data_dir / "processed" / name
        for name in ("master_observations.csv", "master_observations.parquet")
    ]
    original = [path.read_bytes() for path in paths]
    for source, path, context in inputs:
        pipeline.ingest(source, path, context=context)
    second = pipeline.aggregate()
    if first != second or original != [path.read_bytes() for path in paths]:
        raise AssertionError("Unchanged run changed master exports")
    graph = digitize(
        fixtures / "patent_tma.png",
        fixtures / "tma_calibration.json",
        args.data_dir / "processed/digitization",
    )
    print(
        json.dumps(
            {
                "documents": results,
                "master": second,
                "idempotent": True,
                "graph": graph,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
