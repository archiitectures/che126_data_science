"""Permitted patent discovery and pinned FSRI structured-data listings."""

import base64
import json
import math
import os
import time
import xml.etree.ElementTree as ET
from decimal import Decimal
from urllib.parse import quote, urlencode

from .acquisition import HTTPClient
from .sources import matches_material, material_terms


class EPOClient:
    def __init__(self, *, key=None, secret=None, http=None):
        self.key = key or os.environ.get("EPO_OPS_KEY")
        self.secret = secret or os.environ.get("EPO_OPS_SECRET")
        self.http = http or HTTPClient()
        self.token = None
        self.expires = 0

    def search(self, materials, *, limit=25):
        if not self.key or not self.secret:
            raise ValueError(
                "EPO_OPS_KEY and EPO_OPS_SECRET are required for live discovery; use supplied patent IDs/offline fixtures otherwise"
            )
        if not 1 <= limit <= 100:
            raise ValueError("EPO search limit must be 1..100")
        if self.token is None or time.monotonic() >= self.expires:
            auth = base64.b64encode(f"{self.key}:{self.secret}".encode()).decode()
            body, _, _ = self.http.request(
                "https://ops.epo.org/3.2/auth/accesstoken",
                headers={
                    "Authorization": f"Basic {auth}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data=b"grant_type=client_credentials",
            )
            result = json.loads(body)
            self.token = result["access_token"]
            self.expires = time.monotonic() + float(result.get("expires_in", 1200)) - 30
        terms = [material_terms(m)[0] for m in materials]
        if any('"' in term or "\\" in term for term in terms):
            raise ValueError("Invalid material search term")
        query = (
            "("
            + " or ".join(f'ta="{term}"' for term in terms)
            + ') and ta="separator" and (ta="thermal" or ta="shrinkage" or ta="porosity" or ta="shutdown")'
        )
        body, headers, _ = self.http.request(
            "https://ops.epo.org/3.2/rest-services/published-data/search/biblio?"
            + urlencode({"q": query}),
            headers={
                "Authorization": "Bearer " + self.token,
                "Accept": "application/exchange+xml",
                "X-OPS-Range": f"1-{limit}",
            },
        )
        used = next(
            (
                v
                for k, v in headers.items()
                if k.lower() == "x-individualquotaperweek-used"
            ),
            None,
        )
        if used and int(used) >= 4_000_000_000:
            raise RuntimeError("EPO free weekly quota exhausted; no paid fallback")
        root = ET.fromstring(body)
        ns = {"e": "http://www.epo.org/exchange"}
        candidates = []
        for doc in root.findall(".//e:exchange-document", ns):
            country, number, kind = (
                doc.get(k, "") for k in ("country", "doc-number", "kind")
            )
            if not (country and number and kind):
                continue
            publication = country + number + kind
            candidates.append(
                {
                    "publication_number": publication,
                    "url": f"https://patents.google.com/patent/{publication}/en",
                    "family_id": doc.get("family-id"),
                    "provider": "epo",
                }
            )
        return list({c["publication_number"]: c for c in candidates}.values())[:limit]


class BigQueryBudget:
    """Per-run cumulative cap, charging uncertain failures their full reservation."""

    def __init__(self, client, *, usd="2", usd_per_tib="6.25"):
        budget, rate = Decimal(str(usd)), Decimal(str(usd_per_tib))
        if not budget.is_finite() or not rate.is_finite() or budget <= 0 or rate <= 0:
            raise ValueError("Finite positive budget and US on-demand rate required")
        self.client, self.rate = client, rate
        self.limit = int(budget / rate * (1 << 40))
        self.spent_bytes = 0
        self.jobs = []

    def search(self, terms, *, limit=25):
        remaining = self.limit - self.spent_bytes
        if remaining <= 0:
            raise ValueError("Cumulative BigQuery budget exhausted")
        args = {
            "fields": ["title"],
            "titles_only": True,
            "limit": limit,
            "maximum_bytes_billed": remaining,
        }
        estimate = self.client.search(terms, dry_run=True, **args)
        cap = math.ceil(estimate.bytes_processed / (1 << 20)) * (1 << 20) + (1 << 20)
        if cap > remaining:
            raise ValueError("Dry-run estimate exceeds remaining BigQuery budget")
        self.spent_bytes += cap
        try:
            result = self.client.search(terms, **(args | {"maximum_bytes_billed": cap}))
        except Exception:
            self.jobs.append({"status": "uncertain_failure", "reserved_bytes": cap})
            raise
        billed = result.bytes_billed
        if type(billed) is int and 0 <= billed <= cap:
            self.spent_bytes += billed - cap
        self.jobs.append(
            {
                "job_id": result.job_id,
                "bytes_billed": billed,
                "reserved_bytes": cap,
                "status": "complete",
            }
        )
        return result

    def summary(self):
        return {
            "maximum_bytes": self.limit,
            "accounted_bytes": self.spent_bytes,
            "conservative_cost_usd": str(
                Decimal(self.spent_bytes) / (1 << 40) * self.rate
            ),
            "usd_per_tib": str(self.rate),
            "jobs": self.jobs,
        }


def fsri_files(store, materials, *, revision="main", refresh=False):
    base = "https://api.github.com/repos/ulfsri/fsri_materials_database"
    tree = json.loads(
        store.read(
            f"{base}/git/trees/{quote(revision, safe='')}?recursive=1", refresh=refresh
        )
    )
    if tree.get("truncated"):
        raise ValueError("Truncated FSRI tree; cannot claim complete discovery")
    commit = tree["sha"]
    candidates = []
    for entry in tree["tree"]:
        path = entry["path"]
        parts = path.split("/")
        if (
            len(parts) < 4
            or parts[0] != "01_Data"
            or parts[2] != "HFM"
            or entry["type"] != "blob"
        ):
            continue
        if not any(
            matches_material(parts[1].replace("_", " "), material)
            for material in materials
        ):
            continue
        if not (
            path.lower().endswith(".tst")
            or "density" in parts[-1].lower()
            and path.lower().endswith(".csv")
        ):
            continue
        candidates.append(
            {
                "url": f"https://raw.githubusercontent.com/ulfsri/fsri_materials_database/{commit}/{quote(path)}",
                "filename": parts[-1],
                "polymer": parts[1],
                "source_commit": commit,
                "blob_sha": entry["sha"],
            }
        )
    return candidates
