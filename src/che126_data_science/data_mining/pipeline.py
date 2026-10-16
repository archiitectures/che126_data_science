"""Source-to-master orchestration with resumable manifests and no paid fallback."""

import json
import re
from collections import deque
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlparse

from che126_data_science.data_science.master import (
    EXTRACTION_VERSION,
    MasterObservation,
    atomic_bytes,
    atomic_json,
    csv_bytes,
    export_master,
    fingerprint,
    make_observation,
)

from .acquisition import DocumentStore, RawDocument
from .errors import source_failure

ADAPTERS = {
    "celgard": ("pdf_tables", "extract_celgard"),
    "patents": ("patent_html", "extract_patent"),
    "fsri": ("structured", "extract_fsri"),
    "manual": ("structured", "extract_manual"),
    "polyinfo": ("structured", "extract_manual"),
    "literature": ("structured", "extract_manual"),
}


def _adapter(source):
    from importlib import import_module

    if source not in ADAPTERS:
        raise ValueError(f"Unknown source adapter {source}")
    module, name = ADAPTERS[source]
    return getattr(import_module(f"che126_data_science.data_mining.{module}"), name)


class Pipeline:
    def __init__(self, directory="data", *, store=None):
        self.root = Path(directory)
        self.store = store or DocumentStore(directory)
        self.manifest_path = self.root / "processed" / "source_manifest.json"
        self.manifest = (
            json.loads(self.manifest_path.read_text())
            if self.manifest_path.exists()
            else {
                "schema_version": "1",
                "documents": {},
                "batch_status": [],
                "duplicates": [],
            }
        )

    def ingest(self, source, location, *, context=None, refresh=False):
        context = dict(context or {})
        if source == "patents" and re.fullmatch(
            r"(?:US|EP|WO|CN|JP|KR)\d+[A-Z]\d?", str(location)
        ):
            context.setdefault("publication_number", str(location))
            location = f"https://patents.google.com/patent/{location}/en"
        if source == "polyinfo" and (
            not context.get("authorized") or not context.get("restrictions")
        ):
            raise PermissionError(
                "PoLyInfo manual import requires authorized=true and explicit restrictions metadata"
            )
        if source in {"polyinfo", "manual"} and str(location).startswith("https://"):
            raise PermissionError("Manual imports accept local files only")
        context.setdefault("filename", Path(urlparse(str(location)).path).name)
        doc = self.store.fetch(
            source,
            location,
            refresh=refresh,
            source_url=context.get("source_url"),
            restrictions=context.get("restrictions"),
        )
        return self._ingest_document(doc, context, refresh=refresh)

    def _ingest_document(
        self, doc, context, *, refresh=False, allow_fallback_fetch=True
    ):
        source = doc.source
        logical_key = fingerprint({"source_id": doc.source_id, "context": context})
        version_key = fingerprint(
            {
                "logical_key": logical_key,
                "sha256": doc.sha256,
                "extractor": EXTRACTION_VERSION,
            }
        )
        artifact_path = self.root / "interim" / (version_key + ".json")
        if artifact_path.exists():
            result = json.loads(artifact_path.read_text())
        else:
            artifacts, rows, status = [], [], "complete"
            try:
                if source == "patents" and Path(doc.path).suffix.lower() == ".pdf":
                    from .pdf_tables import extract_tables

                    artifacts = extract_tables(doc.path)
                    raise ValueError(
                        "PDF tables extracted; experimental context requires review"
                    )
                rows, artifacts = _adapter(source)(doc, context)
                if not rows:
                    if source == "patents":
                        fallback = next(
                            (a for a in artifacts if a.get("kind") == "pdf_fallback"),
                            None,
                        )
                        if fallback and allow_fallback_fetch:
                            from .pdf_tables import extract_tables

                            try:
                                pdf = self.store.fetch(
                                    "patent_pdf", fallback["url"], refresh=refresh
                                )
                                artifacts.append(
                                    {
                                        "kind": "pdf_fallback_document",
                                        "document": asdict(pdf),
                                        "tables": extract_tables(pdf.path),
                                    }
                                )
                            except (
                                OSError,
                                ValueError,
                                PermissionError,
                                RuntimeError,
                            ) as exc:
                                artifacts.append(
                                    {"kind": "pdf_fallback_error", "error": str(exc)}
                                )
                    raise ValueError(
                        "No supported numeric observations; table artifacts retained for review"
                    )
            except Exception as exc:
                if not source_failure(exc):
                    raise
                status = "review"
                rows = [
                    make_observation(
                        doc,
                        label="Document extraction",
                        prop="unresolved",
                        raw_value="",
                        raw_unit="",
                        sample_id=context.get("product") or doc.source_id,
                        quality_flag="unsupported_document_or_context",
                        extraction_method="review_required",
                        notes=str(exc),
                    )
                ]
                artifacts.append({"kind": "extraction_error", "error": str(exc)})
            result = {
                "document": asdict(doc),
                "context": context,
                "artifacts": artifacts,
                "observations": [asdict(row) for row in rows],
                "status": status,
                "extraction_version": EXTRACTION_VERSION,
            }
            atomic_json(artifact_path, result)
        self.manifest["documents"][logical_key] = {
            "document": asdict(doc),
            "context": context,
            "artifact_file": str(artifact_path),
            "version_key": version_key,
            "status": result["status"],
            "extraction_version": EXTRACTION_VERSION,
        }
        self._save()
        return {
            "source_id": doc.source_id,
            "status": result["status"],
            "accepted": sum(
                r["review_status"] == "accepted" for r in result["observations"]
            ),
            "review": sum(
                r["review_status"] == "pending" for r in result["observations"]
            ),
            "artifact_file": str(artifact_path),
        }

    def _save(self):
        atomic_json(self.manifest_path, self.manifest)

    def figures(self, *, refresh=False):
        """Preserve linked patent figure sheets; calibration supplies figure/crop.

        Image sheets can contain several figures. Never equate sheet index with
        a figure number; save the description captions for manual calibration.
        """
        rows = []
        for _, entry in sorted(self.manifest["documents"].items()):
            artifact = json.loads(Path(entry["artifact_file"]).read_text())
            for item in artifact["artifacts"]:
                if item.get("kind") != "figure":
                    continue
                row = {
                    "source_id": entry["document"]["source_id"],
                    "source_url": entry["document"]["url"],
                    "source_sha256": entry["document"]["sha256"],
                    "sheet": item["sheet"],
                    "source_page": None,
                    "figure": None,
                    "caption": item.get("caption", ""),
                    "crop_bbox": None,
                    "image_file": None,
                    "image_sha256": None,
                    "status": "requires_figure_selection",
                    "error": None,
                }
                try:
                    image = self.store.fetch(
                        "patent_figure", item["url"], refresh=refresh
                    )
                    row.update(image_file=image.path, image_sha256=image.sha256)
                except Exception as exc:
                    if not source_failure(exc):
                        raise
                    row.update(status="fetch_failed", error=str(exc))
                rows.append(row)
        columns = [
            "source_id",
            "source_url",
            "source_sha256",
            "sheet",
            "source_page",
            "figure",
            "caption",
            "crop_bbox",
            "image_file",
            "image_sha256",
            "status",
            "error",
        ]
        atomic_bytes(
            self.root / "processed" / "figures_manifest.csv", csv_bytes(rows, columns)
        )
        return {
            "figure_sheets": len(rows),
            "downloaded": sum(r["image_file"] is not None for r in rows),
        }

    def aggregate(self, out_dir=None, *, measured_only=False):
        rows, aliases, seen, families, evidence = [], [], {}, {}, {}
        for key, entry in sorted(self.manifest["documents"].items()):
            result = json.loads(Path(entry["artifact_file"]).read_text())
            if result.get("extraction_version") != EXTRACTION_VERSION:
                updated = self._ingest_document(
                    RawDocument(**entry["document"]),
                    entry["context"],
                    allow_fallback_fetch=False,
                )
                result = json.loads(Path(updated["artifact_file"]).read_text())
            for raw in result["observations"]:
                row = MasterObservation(**raw)
                family_key = None
                if row.family_id and row.review_status == "accepted":
                    family_key = fingerprint(
                        {
                            "family": row.family_id,
                            "example": row.sample_id.split(":", 1)[-1],
                            **{
                                k: getattr(row, k)
                                for k in (
                                    "property",
                                    "value",
                                    "unit",
                                    "statistic",
                                    "record_type",
                                    "temperature_C",
                                    "temperature_role",
                                    "duration_min",
                                    "direction",
                                    "measurement_context",
                                    "replicate_id",
                                )
                            },
                        }
                    )
                evidence_key = (
                    fingerprint(
                        {
                            "evidence": row.evidence_group,
                            **{
                                k: getattr(row, k)
                                for k in (
                                    "property",
                                    "value",
                                    "unit",
                                    "record_type",
                                    "statistic",
                                    "replicate_id",
                                    "temperature_C",
                                    "temperature_role",
                                )
                            },
                        }
                    )
                    if row.evidence_group
                    else None
                )
                previous = (
                    seen.get(row.observation_id)
                    or (families.get(family_key) if family_key else None)
                    or (evidence.get(evidence_key) if evidence_key else None)
                )
                if previous:
                    aliases.append(
                        {
                            "observation_id": previous.observation_id,
                            "also_reported_as": row.observation_id,
                            "source_id": row.source_id,
                            "source_url": row.source_url,
                        }
                    )
                    continue
                seen[row.observation_id] = row
                if evidence_key:
                    evidence[evidence_key] = row
                if family_key:
                    families[family_key] = row
                rows.append(row)
        self.manifest["duplicates"] = sorted(
            aliases, key=lambda r: (r["observation_id"], r["source_id"])
        )
        self._save()
        directory = Path(out_dir or self.root / "processed")
        summary = export_master(rows, directory, measured_only=measured_only)
        if directory / "source_manifest.json" != self.manifest_path:
            atomic_json(directory / "source_manifest.json", self.manifest)
        return summary

    def collect(
        self,
        *,
        sources=("celgard", "fsri", "patents"),
        materials=("polyethylene", "polypropylene"),
        max_documents=50,
        patent_limit=25,
        patent_provider="epo",
        project=None,
        budget_usd="2",
        usd_per_tib="6.25",
        refresh=False,
        fsri_revision="main",
    ):
        from .discovery import BigQueryBudget, EPOClient, fsri_files
        from .sources import discover_celgard

        if max_documents < 1 or not 1 <= patent_limit <= 100:
            raise ValueError("Positive document limit and patent limit 1..100 required")
        candidates, statuses = [], []
        for source in sources:
            try:
                if source == "celgard":
                    html = self.store.read(
                        "https://www.celgard.com/product-data", refresh=refresh
                    ).decode()
                    for material in materials:
                        for doc in discover_celgard(material, html=html):
                            products = re.findall(
                                r"Celgard[®\s]*([A-Z]*\d+[A-Z0-9]*)",
                                doc.title,
                                re.IGNORECASE,
                            )
                            candidates.append(
                                (
                                    source,
                                    doc.url,
                                    {"product": products[0]}
                                    if len(products) == 1
                                    else {},
                                )
                            )
                elif source == "fsri":
                    for doc in fsri_files(
                        self.store, materials, revision=fsri_revision, refresh=refresh
                    ):
                        candidates.append(
                            (
                                source,
                                doc["url"],
                                {k: v for k, v in doc.items() if k != "url"},
                            )
                        )
                elif source == "patents":
                    discovery_key = fingerprint(
                        {
                            "provider": patent_provider,
                            "materials": list(materials),
                            "limit": patent_limit,
                        }
                    )
                    discovery_file = (
                        self.root / "cache" / ("discovery-" + discovery_key + ".json")
                    )
                    if discovery_file.exists() and not refresh:
                        docs = json.loads(discovery_file.read_text())
                    elif patent_provider == "epo":
                        docs = EPOClient(http=self.store.http).search(
                            materials, limit=patent_limit
                        )
                        atomic_json(discovery_file, docs)
                    elif patent_provider == "bigquery":
                        from .patents import GooglePatentsClient

                        budget = BigQueryBudget(
                            GooglePatentsClient(project=project),
                            usd=budget_usd,
                            usd_per_tib=usd_per_tib,
                        )
                        docs = []
                        try:
                            for material in materials:
                                result = budget.search(
                                    [material, "separator"], limit=patent_limit
                                )
                                docs.extend(
                                    {
                                        "url": row.url + "/en",
                                        "publication_number": row.publication_number,
                                        "family_id": row.family_id,
                                    }
                                    for row in result.records
                                )
                        finally:
                            atomic_json(
                                self.root / "processed" / "google_budget.json",
                                budget.summary(),
                            )
                    else:
                        raise ValueError("Patent provider must be epo or bigquery")
                    if not discovery_file.exists() or refresh:
                        atomic_json(discovery_file, docs)
                    for doc in docs[:patent_limit]:
                        candidates.append(
                            (
                                source,
                                doc["url"],
                                {k: v for k, v in doc.items() if k != "url"},
                            )
                        )
                elif source == "polyinfo":
                    statuses.append(
                        {"source": source, "status": "manual_import_required"}
                    )
                else:
                    raise ValueError(f"Unsupported collection source {source}")
            except Exception as exc:
                if not source_failure(exc):
                    raise
                statuses.append(
                    {"source": source, "status": "discovery_failed", "error": str(exc)}
                )
        buckets = {
            source: deque(c for c in candidates if c[0] == source) for source in sources
        }
        ordered = []
        while any(buckets.values()):
            for bucket in buckets.values():
                if bucket:
                    ordered.append(bucket.popleft())
        completed = {
            fingerprint(
                {
                    "source": entry["document"]["source"],
                    "location": entry["document"]["url"],
                    "context": entry["context"],
                }
            )
            for entry in self.manifest["documents"].values()
            if entry.get("extraction_version") == EXTRACTION_VERSION
            and Path(entry["artifact_file"]).exists()
        }
        results, locations = [], set()
        for source, url, context in ordered:
            if url in locations:
                continue
            identity = fingerprint(
                {
                    "source": source,
                    "location": url,
                    "context": {"filename": Path(urlparse(url).path).name, **context},
                }
            )
            if not refresh and identity in completed:
                locations.add(url)
                continue
            if len(results) >= max_documents:
                continue
            locations.add(url)
            try:
                results.append(
                    self.ingest(source, url, context=context, refresh=refresh)
                )
            except Exception as exc:
                if not source_failure(exc):
                    raise
                results.append(
                    {
                        "source": source,
                        "url": url,
                        "status": "fetch_failed",
                        "error": str(exc),
                    }
                )
        self.manifest["batch_status"] = statuses + [
            r for r in results if r.get("status") == "fetch_failed"
        ]
        self._save()
        return {
            "documents": results,
            "discovery": statuses,
            "remaining_candidates": max(
                0, len({u for _, u, _ in candidates}) - len(locations)
            ),
            "outputs": self.aggregate(),
        }
