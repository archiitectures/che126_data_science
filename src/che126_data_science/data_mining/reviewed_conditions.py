"""Apply source-verified condition revisions without changing measured values."""

import hashlib
import json
import math
import re
from dataclasses import replace
from pathlib import Path

from lxml import html

from che126_data_science.data_science.master import fingerprint


def apply_reviewed_conditions(rows, document, revisions):
    if not isinstance(revisions, dict):
        raise TypeError("Condition revisions must be an observation-ID mapping")
    if not revisions:
        return rows
    source = re.sub(
        r"\W+",
        "",
        " ".join(
            html.fromstring(
                Path(document.path).read_bytes(),
                parser=html.HTMLParser(encoding="utf-8"),
            ).itertext()
        ),
    ).lower()
    found = set()
    result = []
    for row in rows:
        revision = revisions.get(row.observation_id)
        if revision is None:
            result.append(row)
            continue
        metadata = revision["metadata"]
        if (
            set(metadata) - {"temperature_C", "temperature_role", "duration_min"}
            or not {"temperature_C", "temperature_role"} <= set(metadata)
            or metadata["temperature_role"] not in {"measurement", "exposure"}
            or not math.isfinite(float(metadata["temperature_C"]))
            or row.temperature_C is not None
            or revision["source_sha256"] != document.sha256
        ):
            raise ValueError("Invalid reviewed temperature revision")
        evidence_source = source
        evidence = revision.get("evidence_document")
        if evidence:
            raw = Path(evidence["path"]).read_bytes()
            if (
                hashlib.sha256(raw).hexdigest() != evidence["sha256"]
                or evidence["source_url"] != row.source_url
            ):
                raise ValueError(
                    "External condition evidence hash or source URL mismatch"
                )
            if Path(evidence["path"]).suffix.lower() == ".pdf":
                import pymupdf

                with pymupdf.open(evidence["path"]) as pdf:
                    text = " ".join(page.get_text() for page in pdf)
            else:
                text = " ".join(
                    html.fromstring(
                        raw, parser=html.HTMLParser(encoding="utf-8")
                    ).itertext()
                )
            evidence_source = re.sub(r"\W+", "", text).lower()
        quote = revision["quote"]
        if not quote or re.sub(r"\W+", "", quote).lower() not in evidence_source:
            raise ValueError("Reviewed temperature evidence does not match source")
        new_id = fingerprint(
            {
                "parent_observation_id": row.observation_id,
                "reviewed_conditions": metadata,
            }
        )
        note = {"previous_observation_id": row.observation_id, **revision}
        result.append(
            replace(
                row,
                observation_id=new_id,
                **metadata,
                notes=(row.notes or "")
                + " Reviewed conditions: "
                + json.dumps(note, sort_keys=True),
            )
        )
        found.add(row.observation_id)
    if found != set(revisions):
        raise ValueError("Reviewed condition observation is absent from extraction")
    return result
