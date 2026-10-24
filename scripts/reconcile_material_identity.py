"""Reevaluate cached patent identities, snapshot inputs, and optionally rebuild."""

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup

from che126_data_science.data_mining.acquisition import RawDocument
from che126_data_science.data_mining.material_identity import (
    PatentIdentities,
    normalize_sample,
)
from che126_data_science.data_mining.patent_html import _verified_sample_context
from che126_data_science.data_mining.pipeline import Pipeline
from che126_data_science.data_science.master import (
    EXTRACTION_VERSION,
    atomic_json,
    fingerprint,
)

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "data_mining/runs/2026-10-23_identity_reconciliation"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    RUN.mkdir(parents=True, exist_ok=True)
    snapshot = RUN / "before"
    if not snapshot.exists():
        snapshot.mkdir()
        for name in [
            "master_observations.csv",
            "master_observations.parquet",
            "unique_points.csv",
            "unique_points.parquet",
            "source_manifest.json",
            "unique_point_evidence.json",
            "unique_points_summary.json",
        ]:
            shutil.copyfile(ROOT / "data/processed" / name, snapshot / name)
    original = json.loads((snapshot / "source_manifest.json").read_text())
    reviewed_path = (
        ROOT / "data_mining/runs/2026-10-23_identity_probe/reviewed_evidence.json"
    )
    reviewed = json.loads(reviewed_path.read_text())
    manual = {}
    for key, value in reviewed.items():
        number, sample = key.split(":", 1)
        manual.setdefault(number, {})[sample] = {
            "metadata": {"polymer": value["candidate_polymer"]},
            "evidence": value["evidence"],
        }
    additions = RUN / "reviewed_additions.json"
    if additions.exists():
        for number, annotations in json.loads(additions.read_text()).items():
            manual.setdefault(number, {}).update(annotations)
    baseline = list(
        csv.DictReader((snapshot / "master_observations.csv").open(newline=""))
    )
    samples = {}
    for row in baseline:
        if row["source_type"] == "patents":
            samples.setdefault(row["source_id"], {})[
                row["sample_id"].split(":", 1)[-1]
            ] = row
    plans, contexts = [], {}
    for key, entry in original["documents"].items():
        doc = entry["document"]
        if doc["source_id"] not in samples:
            continue
        path = ROOT / doc["path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != doc["sha256"]:
            raise ValueError(f"Source hash mismatch: {path}")
        soup = BeautifulSoup(path.read_bytes(), "lxml")
        number = (doc.get("url") or "").split("/patent/")[-1].split("/")[0]
        context = dict(entry["context"])
        annotations = dict(context.get("sample_annotations", {}))
        for sample, annotation in manual.get(number, {}).items():
            annotations.setdefault(sample, annotation)
        if annotations:
            context["sample_annotations"] = annotations
        checked = _verified_sample_context(soup, context)
        resolver = PatentIdentities(soup)
        for sample, row in samples[doc["source_id"]].items():
            result = resolver.resolve(sample)
            reviewed_meta = checked.get(sample, ({}, ""))[0]
            proposal = (
                reviewed_meta.get("polymer") or context.get("polymer") or result.polymer
            )
            # Existing identity is preserved; this report also surfaces disagreement.
            plans.append(
                {
                    "source_id": doc["source_id"],
                    "source_url": doc.get("url"),
                    "sample": sample,
                    "current_polymer": row["polymer"],
                    "proposed_polymer": proposal or "",
                    "status": "reviewed_sample_link"
                    if reviewed_meta
                    else result.status,
                    "reason": result.reason,
                    "evidence": json.dumps(
                        result.evidence
                        if not reviewed_meta
                        else annotations[sample]["evidence"]
                    ),
                    "disagreement_with_existing": bool(
                        row["polymer"] and proposal and row["polymer"] != proposal
                    ),
                    "normalized_sample": normalize_sample(sample) or "",
                }
            )
        contexts[key] = context
    with (RUN / "sample_plan.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(plans[0]))
        writer.writeheader()
        writer.writerows(plans)
    counts = Counter(
        (bool(p["current_polymer"]), p["proposed_polymer"] or p["status"])
        for p in plans
    )
    atomic_json(
        RUN / "plan_summary.json",
        {"samples": len(plans), "counts": {str(k): v for k, v in counts.items()}},
    )
    print(
        json.dumps(
            {"samples": len(plans), "counts": {str(k): v for k, v in counts.items()}},
            indent=2,
        ),
        flush=True,
    )
    if not args.apply:
        return
    pipeline = Pipeline(ROOT / "data")
    # Raw sources and extraction artifacts are immutable. Checkpoint the large
    # manifest every 50 updates instead of rewriting it for every cached source;
    # interrupted batches replay safely from the original snapshot and cache.
    save_manifest = pipeline._save
    pending_updates = 0

    def checkpoint():
        nonlocal pending_updates
        pending_updates += 1
        if pending_updates >= 50:
            save_manifest()
            pending_updates = 0

    pipeline._save = checkpoint
    for index, (key, entry) in enumerate(original["documents"].items(), 1):
        context = contexts.get(key, entry["context"])
        doc = RawDocument(**entry["document"])
        new_key = fingerprint({"source_id": doc.source_id, "context": context})
        current = pipeline.manifest["documents"].get(new_key)
        if current and current["extraction_version"] == EXTRACTION_VERSION:
            result = {"status": "cached"}
        else:
            result = pipeline._ingest_document(doc, context, allow_fallback_fetch=False)
        base_context = {k: v for k, v in context.items() if k != "sample_annotations"}
        obsolete = [
            k
            for k, e in pipeline.manifest["documents"].items()
            if k != new_key
            and e["document"]["source_id"] == doc.source_id
            and {
                field: value
                for field, value in e["context"].items()
                if field != "sample_annotations"
            }
            == base_context
        ]
        if obsolete:
            for old_key in obsolete:
                pipeline.manifest["documents"].pop(old_key)
            pipeline._save()
        if index % 50 == 0:
            print(index, "documents", result["status"], flush=True)
    pipeline._save = save_manifest
    pipeline._save()
    print(json.dumps(pipeline.aggregate()), flush=True)


if __name__ == "__main__":
    main()
