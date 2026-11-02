"""Offline repository assembly, current audits, figures and optional byte-level replay.

Run from any directory: .venv/bin/python scripts/assemble_dataset.py --check-replay
The existing data/processed/source_manifest.json is the explicit corpus selection.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from che126_data_science.data_mining.pipeline import Pipeline
from che126_data_science.data_science.master import atomic_json
from che126_data_science.data_science.reporting import refresh

ROOT = Path(__file__).resolve().parents[1]


def assemble(root, figures=True):
    root = Path(root).resolve()
    if not (root / "data/processed/source_manifest.json").is_file():
        raise FileNotFoundError(
            "Assembly requires an explicitly selected source manifest"
        )
    previous = Path.cwd()
    try:
        os.chdir(root)
        Pipeline("data").aggregate(out_dir="data/processed")
        for script in (
            "export_unique_points.py",
            "annotate_polymer_subtypes.py",
            "export_temperature_views.py",
        ):
            subprocess.run(
                [sys.executable, str(root / "scripts" / script)], cwd=root, check=True
            )
        refresh(root)
        subprocess.run(
            [
                sys.executable,
                str(root / "scripts/audit_dataset.py"),
                "--root",
                str(root),
                "--out",
                str(root / "datasets/quality_review.json"),
            ],
            cwd=root,
            check=True,
        )
        if figures:
            subprocess.run(
                [sys.executable, str(root / "visualizations/generate_figures.py")],
                cwd=root,
                check=True,
            )
        files = [
            p
            for p in (root / "datasets").iterdir()
            if p.suffix in {".csv", ".parquet", ".json"}
            and p.name != "assembly_manifest.json"
        ]
        if figures:
            files += [
                p
                for folder in ("figures", "tables")
                for p in (root / "visualizations" / folder).iterdir()
                if p.is_file()
            ]
            files.append(root / "visualizations/summary.json")
        hashes = {
            str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(files)
        }
        atomic_json(
            root / "datasets/assembly_manifest.json",
            {"artifacts_sha256": hashes, "offline": True, "figures_included": figures},
        )
        return hashes
    finally:
        os.chdir(previous)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--skip-figures", action="store_true")
    parser.add_argument("--check-replay", action="store_true")
    args = parser.parse_args()
    hashes = assemble(args.root, not args.skip_figures)
    if args.check_replay:
        repeated = assemble(args.root, not args.skip_figures)
        changed = sorted(
            k
            for k in hashes.keys() | repeated.keys()
            if hashes.get(k) != repeated.get(k)
        )
        if changed:
            raise SystemExit("Assembly replay changed artifacts: " + ", ".join(changed))
    print(
        json.dumps(
            {"artifacts": len(hashes), "byte_identical_replay": args.check_replay},
            indent=2,
        )
    )
