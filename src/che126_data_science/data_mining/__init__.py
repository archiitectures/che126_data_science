"""Reusable acquisition tools; optional dependencies load only when used."""

from .patents import (
    GooglePatentsClient,
    LocalizedText,
    PatentRecord,
    PatentResults,
    QueryEstimate,
    export_json,
)

__all__ = [
    "GooglePatentsClient",
    "LocalizedText",
    "PatentRecord",
    "PatentResults",
    "QueryEstimate",
    "export_json",
]
