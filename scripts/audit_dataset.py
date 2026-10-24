"""Offline, read-only audit of accepted exports and their stored source evidence.

Checks every row's schema, units, raw-file hash, CSV/Parquet parity and context
membership. Source-cell checks cover patent HTML, Celgard PDF tables and structured
imports; they establish transcription, not full scientific interpretation.
"""

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

import pyarrow.parquet as pq

from che126_data_science.data_mining.normalization import NUMBER, values
from che126_data_science.data_science.master import (
    SCIENTIFIC_FIELDS,
    MasterObservation,
    atomic_json,
    fingerprint,
)
from che126_data_science.data_science.observations import CONVERSIONS

ROOT = Path(__file__).resolve().parents[1]


def audit(root, out):
    data = root / "datasets"
    rows = pq.read_table(data / "master_observations.parquet").to_pylist()
    points = pq.read_table(data / "unique_points.parquet").to_pylist()
    failures, checks = [], {}

    def check(name, passed):
        checks[name] = bool(passed)
        if not passed:
            failures.append(name)

    check(
        "unique_observation_ids", len({r["observation_id"] for r in rows}) == len(rows)
    )
    check(
        "unique_point_ids", len({r["unique_point_id"] for r in points}) == len(points)
    )
    validation_errors = []
    for r in rows:
        try:
            MasterObservation(**r)
            value = float(r["original_value"])
            raw_unit = r["original_unit"]
            from che126_data_science.data_mining.normalization import (
                canonical_unit_text,
            )

            raw_unit = canonical_unit_text(raw_unit)
            scale, offset = (
                (1, 0) if raw_unit == r["unit"] else CONVERSIONS[(raw_unit, r["unit"])]
            )
            if not math.isclose(
                value * scale + offset, r["value"], rel_tol=1e-12, abs_tol=1e-12
            ):
                raise ValueError("conversion mismatch")
        except (ValueError, KeyError, TypeError) as exc:
            validation_errors.append({"id": r["observation_id"], "error": str(exc)})
    check("schema_and_conversions", not validation_errors)
    files = {(r["source_file"], r["source_sha256"]) for r in rows}
    bad_files = [
        p
        for p, h in files
        if not (root / p).is_file()
        or hashlib.sha256((root / p).read_bytes()).hexdigest() != h
    ]
    check("all_source_hashes", not bad_files)
    for stem, records in [("master_observations", rows), ("unique_points", points)]:
        with (data / (stem + ".csv")).open(newline="") as f:
            csv_rows = list(csv.DictReader(f))
        expected = [
            {k: "" if v is None else str(v) for k, v in r.items()} for r in records
        ]
        check(stem + "_csv_parquet_equal", csv_rows == expected)
    for name in [
        "master_observations.csv",
        "master_observations.parquet",
        "unique_points.csv",
        "unique_points.parquet",
        "unique_point_evidence.json",
        "unique_points_summary.json",
    ]:
        check(
            "mirror_" + name,
            (data / name).read_bytes() == (root / "data/processed" / name).read_bytes(),
        )
    grouped = defaultdict(list)
    for r in rows:
        grouped[fingerprint({k: r[k] for k in SCIENTIFIC_FIELDS})].append(
            r["observation_id"]
        )
    check(
        "context_key_matches_export",
        set(grouped) == {r["unique_point_id"] for r in points},
    )
    evidence = json.loads((data / "unique_point_evidence.json").read_text())
    check(
        "complete_evidence_membership",
        {
            e["unique_point_id"]: sorted(e["supporting_observation_ids"])
            for e in evidence
        }
        == {k: sorted(v) for k, v in grouped.items()},
    )
    check(
        "representatives_belong_to_groups",
        all(
            p["observation_id"] in grouped.get(p["unique_point_id"], [])
            and p["supporting_observations"]
            == len(grouped.get(p["unique_point_id"], []))
            for p in points
        ),
    )
    manifest = json.loads((root / "data/processed/source_manifest.json").read_text())
    artifacts = {}
    for entry in manifest["documents"].values():
        sha = entry["document"]["sha256"]
        if sha not in {h for _, h in files} or sha in artifacts:
            continue
        artifacts[sha] = json.loads((root / entry["artifact_file"]).read_text())[
            "artifacts"
        ]
    cells_checked = Counter()
    mismatches = []
    for r in rows:
        if r["source_type"] not in {"patents", "celgard", "manual"}:
            continue
        cells = []
        for a in artifacts.get(r["source_sha256"], []):
            if a.get("kind") == "table" and str(a.get("table")) == r["source_table"]:
                try:
                    cells.append(
                        a["cells"][int(r["source_row"]) - 1][
                            int(r["source_column"]) - 1
                        ]
                    )
                except (IndexError, TypeError, ValueError):
                    pass
            elif a.get("kind") == "structured_rows":
                try:
                    cells.append(str(a["rows"][int(r["source_row"]) - 2]["value"]))
                except (IndexError, KeyError, TypeError, ValueError):
                    pass
        ok = False
        for cell in cells:
            if cell is None:
                continue
            parsed = [v for v, _ in values(str(cell), r["original_property_label"])]
            pair = re.fullmatch(
                rf"\s*({NUMBER})\s*/\s*({NUMBER})\s*", str(cell).replace("−", "-")
            )
            if pair:
                parsed.extend(pair.groups())
            for v in parsed:
                try:
                    ok = ok or float(v) == float(r["original_value"])
                except ValueError:
                    pass
        cells_checked[r["source_type"]] += 1
        if not ok:
            mismatches.append(
                {
                    "observation_id": r["observation_id"],
                    "source_url": r["source_url"],
                    "property": r["property"],
                    "cells": cells,
                }
            )
    check("stored_table_cells_match_values", not mismatches)
    # Identical normalized contexts are intentionally collapsed. A shared number
    # alone does not establish duplicate experiments or patent family membership.
    urls = {r["source_url"] for r in rows if r["source_url"]}
    counts = Counter()
    for url in urls:
        host = urlparse(url).hostname
        kind = (
            "patent_publications"
            if host == "patents.google.com"
            else "celgard_datasheets"
            if host == "www.celgard.com"
            else "fsri_files"
            if host == "raw.githubusercontent.com"
            else "literature_urls"
        )
        counts[kind] += 1
    semantic_gaps = {
        k: sum(r[k] is None for r in points)
        for k in ["polymer", "temperature_C", "method", "shrinkage_basis"]
    }
    summary = {
        "accepted_observations": len(rows),
        "distinct_contexts": len(points),
        "source_files": len(files),
        "source_urls": len(urls),
        "sources_by_url_kind": dict(counts),
        "manifest_entries_perused": len(manifest["documents"]),
        "properties": len({r["property"] for r in points}),
        "unknown_fields_in_contexts": semantic_gaps,
        "checks": checks,
        "failed_checks": failures,
        "source_cell_checks": dict(cells_checked),
        "validation_errors": validation_errors,
        "source_cell_mismatches": mismatches,
        "bad_source_files": bad_files,
        "input_sha256": hashlib.sha256(
            (data / "master_observations.csv").read_bytes()
        ).hexdigest(),
        "limitations": "Cell checks use preserved extraction artifacts. Source hashes prove byte identity, not truth. Manual CSV checks verify imports, not the upstream paper. Patent families and independent experiments are not certified. Missing metadata and unsupported formats require review.",
    }
    atomic_json(out, summary)
    print(
        json.dumps(
            {
                k: v
                for k, v in summary.items()
                if k
                not in {
                    "checks",
                    "validation_errors",
                    "source_cell_mismatches",
                    "bad_source_files",
                }
            },
            indent=2,
        )
    )
    return not failures


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--out", type=Path, default=ROOT / "output/review/dataset_audit.json"
    )
    args = parser.parse_args()
    raise SystemExit(0 if audit(args.root, args.out) else 1)
