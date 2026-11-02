"""Scientific corrections are explicit, reversible and source bound."""

from types import SimpleNamespace

import pytest

from che126_data_science.data_mining.curation import apply_revision
from che126_data_science.data_science.master import make_observation


def test_revision_preserves_withdrawn_raw_evidence_and_checks_hash():
    doc = SimpleNamespace(
        source_id="test",
        source="patents",
        url="https://example.org",
        path="test.html",
        sha256="a" * 64,
        restrictions="test",
    )
    old = make_observation(
        doc,
        label="packing density",
        prop="density",
        raw_value=1.45,
        raw_unit="g/cm3",
        sample_id="Example 1",
    )
    revision = {
        "source_sha256": doc.sha256,
        "reason": "Reviewed primary coating property label",
        "changes": {
            "property": "packing_density",
            "sample_form": "separator_component",
        },
    }
    withdrawn, corrected = apply_revision(old, revision)
    assert (
        withdrawn.review_status == "pending" and corrected.review_status == "accepted"
    )
    assert withdrawn.observation_id == old.observation_id != corrected.observation_id
    assert (
        corrected.original_value == old.original_value
        and corrected.source_sha256 == old.source_sha256
    )
    with pytest.raises(ValueError, match="hash"):
        apply_revision(old, {**revision, "source_sha256": "b" * 64})
    with pytest.raises(ValueError, match="arbitrary"):
        apply_revision(old, {**revision, "changes": {"original_value": "2"}})
