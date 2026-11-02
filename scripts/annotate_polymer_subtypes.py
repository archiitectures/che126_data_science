"""Add conservative, traceable polymer subtype metadata to curated exports.

Run after assembling master/unique tables. Identity labels support grade assignments;
whole-document prose and recipe-family descriptions do not establish sample morphology.
Existing scientific IDs and measurements are preserved.
"""

import csv
import hashlib
import io
import json
import re
from collections import Counter
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from che126_data_science.data_science.master import atomic_bytes

ROOT = Path(__file__).resolve().parents[1]
COLUMNS = (
    "polymer_subtype",
    "polymer_morphology",
    "polymer_subtype_status",
    "polymer_subtype_evidence",
    "polymer_subtype_candidates",
    "polymer_crystallinity_measurements",
)
REVIEWED_PATH = ROOT / "data_mining/reviewed_polymer_morphology.json"
REVIEWED = json.loads(REVIEWED_PATH.read_text()) if REVIEWED_PATH.exists() else []


def sample_key(value):
    value = re.sub(
        r"\b(?:comparative|comparison|comp\.?)\s*(?:example|ex\.?)",
        "comparativeexample",
        str(value).lower(),
    )
    return re.sub(r"\s+", "", value)


REVIEWED_BY_SAMPLE = {}
for entry in REVIEWED:
    REVIEWED_BY_SAMPLE.setdefault(
        sample_key(entry["publication"] + ":" + entry["sample"]), []
    ).append(entry)

PATTERNS = {
    "UHMWPE": r"\bUHMWPE\b|ultra[ -]?high[ -]?molecular[ -]?weight polyethylene",
    "LLDPE": r"\bLLDPE\b|linear low[ -]density polyethylene",
    "HDPE": r"\bHDPE\b|high[ -]density polyethylene",
    "LDPE": r"\bLDPE\b|(?<!linear )low[ -]density polyethylene",
    "isotactic PP": r"\bisotactic polypropylene\b",
    "atactic PP": r"\batactic polypropylene\b",
    "syndiotactic PP": r"\bsyndiotactic polypropylene\b",
}


def classify(row):
    evidence = []
    labels = set()
    # Underscores in instrument sample IDs delimit material tokens.
    for field in ("polymer", "product", "sample_id", "material_grade"):
        text = str(row.get(field) or "")
        # Recipe-family metadata is not an exact sample assignment.
        if field == "material_grade" and re.search(
            r"recipe|vary|based", text, re.IGNORECASE
        ):
            continue
        normalized = text.replace("_", " ")
        matched = [
            label
            for label, pattern in PATTERNS.items()
            if re.search(pattern, normalized, re.IGNORECASE)
        ]
        if matched:
            labels.update(matched)
            evidence.append({"field": field, "text": text, "labels": matched})
    # Morphology requires a sample-specific explicit assignment; grade alone is insufficient.
    morphology = ""
    grade = str(row.get("material_grade") or "")
    if not re.search(r"recipe|vary|based", grade, re.IGNORECASE):
        if re.fullmatch(r"semi[- ]?crystalline", grade, re.IGNORECASE):
            morphology = "semicrystalline"
        elif re.fullmatch(r"amorphous|crystalline", grade, re.IGNORECASE):
            morphology = grade.lower()
        if morphology:
            evidence.append({"field": "material_grade", "text": grade})
    # Reviewed sample-linked source passages; scope morphology to the constituent
    # or feedstock, because processing and temperature can alter the final membrane.
    sample = sample_key(row.get("sample_id") or "")
    if sample.startswith("us20030031924a1:example1-") and sample[-1:] in {
        "1",
        "2",
        "3",
    }:
        labels.add("high-crystalline PP feedstock")
        morphology = "PP feedstock: high crystalline (source terminology)"
        if sample[-1:] in {"2", "3"}:
            labels.add("HDPE")
        evidence.append(
            {
                "field": "material_identity_evidence",
                "locator": "P-0107 / P-0109 / P-0111",
                "scope": "source-linked sample raw polymer; not final membrane crystallinity",
            }
        )
    elif sample == "us20190103593a1:example11":
        morphology = "PVDF resin component: amorphous (source terminology)"
        evidence.append(
            {
                "field": "material_identity_evidence",
                "locator": "p-0166",
                "scope": "PVDF organic resin component; whole separator morphology unspecified",
            }
        )
    source_evidence = str(row.get("material_identity_evidence") or "")
    candidates = sorted(
        label
        for label, pattern in PATTERNS.items()
        if re.search(pattern, source_evidence.replace("_", " "), re.IGNORECASE)
    )
    linked = REVIEWED_BY_SAMPLE.get(sample, [])
    if linked:
        morphology = (
            "PE layer component: semicrystalline; state during test unverified"
            if all(r["scope"] == "PE layer component" for r in linked)
            else "prepared membrane: semicrystalline; state during test unverified"
        )
        evidence.extend(linked)
    return dict(
        zip(
            COLUMNS,
            (
                "/".join(sorted(labels)),
                morphology,
                "explicit_identity_or_reviewed_sample_evidence"
                if labels or morphology
                else "not_reported_in_linked_identity",
                json.dumps(evidence, ensure_ascii=False) if evidence else "",
                "/".join(candidates),
                json.dumps(linked, ensure_ascii=False) if linked else "",
            ),
        )
    )


def main():
    if not REVIEWED_PATH.is_file():
        raise FileNotFoundError(
            "Reviewed morphology mapping is required; do not silently omit it"
        )
    for path, expected in {
        (r["evidence_source_file"], r["source_sha256"]) for r in REVIEWED
    }:
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected:
            raise ValueError(
                "Reviewed morphology primary-source hash mismatch: " + path
            )
    summary = {}
    for name in ("master_observations", "unique_points"):
        path = ROOT / "datasets" / f"{name}.parquet"
        table = pq.read_table(path)
        old = table.to_pylist()
        rows = [{**row, **classify(row)} for row in old]
        schema = pa.schema(
            [f for f in table.schema if f.name not in COLUMNS]
            + [pa.field(c, pa.string()) for c in COLUMNS],
            metadata=table.schema.metadata,
        )
        updated = pa.Table.from_pylist(rows, schema=schema)
        assert all(
            all(row[k] == original[k] for k in original if k not in COLUMNS)
            for row, original in zip(rows, old)
        )
        sink = pa.BufferOutputStream()
        pq.write_table(updated, sink, compression="zstd")
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=schema.names, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        for folder in ("datasets", "data/processed"):
            atomic_bytes(ROOT / folder / f"{name}.csv", stream.getvalue().encode())
            atomic_bytes(
                ROOT / folder / f"{name}.parquet", sink.getvalue().to_pybytes()
            )
        summary[name] = {
            "rows": len(rows),
            "subtypes": dict(
                Counter(row["polymer_subtype"] or "not reported" for row in rows)
            ),
            "morphology": dict(
                Counter(row["polymer_morphology"] or "not reported" for row in rows)
            ),
        }
    atomic_bytes(
        ROOT / "datasets/polymer_subtype_audit.json",
        (json.dumps(summary, indent=2) + "\n").encode(),
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
