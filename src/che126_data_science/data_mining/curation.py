"""Replay explicit source-bound corrections while retaining withdrawn evidence in review."""

import json
from dataclasses import replace

from che126_data_science.data_science.master import fingerprint

ALLOWED = {
    "property",
    "original_property_label",
    "original_unit",
    "unit",
    "value",
    "conversion_metadata",
    "temperature_C",
    "temperature_role",
    "duration_min",
    "method",
    "measurement_context",
    "shrinkage_basis",
    "sample_form",
    "material_class",
    "polymer",
    "sample_id",
    "separator_architecture",
    "coating",
    "material_identity_status",
    "material_identity_reason",
    "material_identity_evidence",
}


def apply_revision(row, revision):
    if revision is None or row.review_status != "accepted":
        return [row]
    if row.source_sha256 != revision["source_sha256"] or not revision.get("reason"):
        raise ValueError("Curation source hash/reason mismatch")
    coordinates = revision.get("source_coordinates")
    if coordinates and coordinates != {
        "table": row.source_table or "",
        "row": str(row.source_row or ""),
        "column": str(row.source_column or ""),
    }:
        raise ValueError("Curation source coordinates mismatch")
    changes = revision.get("changes", {})
    if set(changes) - ALLOWED:
        raise ValueError(
            "Curation cannot change raw value, provenance or arbitrary fields"
        )
    note = " Reviewed curation: " + json.dumps(
        {"previous_observation_id": row.observation_id, **revision}, sort_keys=True
    )
    withdrawn = replace(
        row,
        review_status="pending",
        quality_flag="withdrawn_after_source_review",
        notes=(row.notes or "") + note,
    )
    if not changes:
        return [withdrawn]
    corrected = replace(
        row,
        **changes,
        observation_id=fingerprint(
            {"parent": row.observation_id, "revision": revision}
        ),
        notes=(row.notes or "") + note,
        quality_flag=None,
    )
    return [withdrawn, corrected]
