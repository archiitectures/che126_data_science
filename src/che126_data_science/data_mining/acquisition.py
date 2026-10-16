"""Immutable documents, access-aware HTTP, and explicit offline cache reuse."""

import hashlib
import json
import re
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from che126_data_science.data_science.master import atomic_json, fingerprint

USER_AGENT = "che126-data-science/0.2"
# Direct API/raw-object endpoints are not website search/crawl surfaces.
API_HOSTS = {
    "api.github.com",
    "raw.githubusercontent.com",
    "ops.epo.org",
    "patentimages.storage.googleapis.com",
}


def robots_allowed(text: str, url: str) -> bool:
    """Longest matching Allow/Disallow rule, including * and terminal $."""
    groups, agents, rules = [], [], []
    for raw in [*text.splitlines(), "User-agent: __end__"]:
        line = raw.split("#", 1)[0].strip()
        key, sep, value = line.partition(":")
        if not sep:
            continue
        key, value = key.lower(), value.strip()
        if key == "user-agent":
            if rules:
                groups.append((agents, rules))
                agents, rules = [], []
            agents.append(value.lower())
        elif key in {"allow", "disallow"} and agents and value:
            rules.append((key == "allow", value))
    if rules:
        groups.append((agents, rules))
    candidates = [
        (len(a) if a != "*" else 0, rs)
        for aa, rs in groups
        for a in aa
        if a == "*" or a in USER_AGENT.lower()
    ]
    if not candidates:
        return True
    best = max(n for n, _ in candidates)
    parsed = urlparse(url)
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    matches = []
    for n, rs in candidates:
        if n != best:
            continue
        for allow, pattern in rs:
            regex = "^" + re.escape(pattern).replace(r"\*", ".*")
            if pattern.endswith("$"):
                regex = regex[:-2] + "$"
            if re.search(regex, path):
                matches.append((len(pattern.replace("*", "").rstrip("$")), allow))
    return max(matches, default=(0, True))[1]


class HTTPClient:
    """Serial requests, visible failures, finite reads and transient retries only."""

    def __init__(
        self,
        *,
        interval: float = 1,
        max_bytes: int = 20_000_000,
        timeout: float = 30,
        opener=urlopen,
        sleep=time.sleep,
    ):
        if interval < 0 or max_bytes <= 0 or timeout <= 0:
            raise ValueError("Positive HTTP limits and nonnegative interval required")
        self.interval, self.max_bytes, self.timeout = interval, max_bytes, timeout
        self.opener, self.sleep = opener, sleep
        self.last = 0.0
        self.robots = {}

    def request(self, url: str, *, headers=None, data=None, check_access=True):
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("Only absolute HTTPS URLs are allowed")
        if parsed.hostname == "polymer.nims.go.jp":
            raise PermissionError("NIMS is manual-import only")
        if check_access and parsed.hostname not in API_HOSTS:
            origin = f"{parsed.scheme}://{parsed.netloc}"
            if origin not in self.robots:
                try:
                    body, _, _ = self.request(
                        origin + "/robots.txt", check_access=False
                    )
                    self.robots[origin] = body.decode("utf-8", errors="replace")
                except HTTPError as exc:
                    if exc.code != 404:
                        raise PermissionError(
                            f"Cannot establish robots access for {origin}"
                        ) from exc
                    self.robots[origin] = ""
            if not robots_allowed(self.robots[origin], url):
                raise PermissionError(f"robots.txt disallows {url}")
        request = Request(
            url, data=data, headers={"User-Agent": USER_AGENT, **(headers or {})}
        )
        for attempt in range(3):
            self.sleep(max(0, self.interval - (time.monotonic() - self.last)))
            self.last = time.monotonic()
            try:
                with self.opener(request, timeout=self.timeout) as response:
                    if urlparse(response.url).scheme != "https":
                        raise PermissionError("Non-HTTPS redirect")
                    if response.url != url and check_access:
                        redirected = urlparse(response.url)
                        if redirected.hostname != parsed.hostname:
                            raise PermissionError(
                                "Cross-origin redirect requires an explicit source URL"
                            )
                    body = response.read(self.max_bytes + 1)
                    if len(body) > self.max_bytes:
                        raise ValueError("Document exceeds download byte limit")
                    return body, dict(response.headers), response.url
            except HTTPError as exc:
                if exc.code not in {429, 500, 502, 503, 504} or attempt == 2:
                    raise
                delay = exc.headers.get("Retry-After", "") if exc.headers else ""
                if delay.isdigit() and int(delay) > 60:
                    raise RuntimeError(
                        "Retry-After exceeds 60 seconds; resume later"
                    ) from exc
                self.sleep(int(delay) if delay.isdigit() else 2**attempt)
            except (URLError, TimeoutError, ConnectionError):
                if attempt == 2:
                    raise
                self.sleep(2**attempt)
        raise RuntimeError("Unreachable retry state")


@dataclass(frozen=True)
class RawDocument:
    source_id: str
    source: str
    path: str
    sha256: str
    url: str | None = None
    retrieved_at: str | None = None
    restrictions: str = (
        "License/reuse permission not established; local research evidence only"
    )
    etag: str | None = None
    last_modified: str | None = None


class DocumentStore:
    def __init__(self, directory="data", *, http=None):
        self.root = Path(directory)
        self.http = http or HTTPClient()
        self._legacy_receipts = None

    def fetch(
        self,
        source: str,
        location: str | Path,
        *,
        refresh=False,
        source_url: str | None = None,
        restrictions: str | None = None,
    ) -> RawDocument:
        location = str(location)
        remote = location.startswith("https://")
        key = fingerprint({"source": source, "location": location})
        receipt = self.root / "cache" / (key + ".json")
        previous = json.loads(receipt.read_text()) if receipt.exists() else None
        # Adopt the existing project's immutable acquisition receipts, preserving
        # the raw source and avoiding a first-run download of known URLs.
        if remote and previous is None and not refresh:
            if self._legacy_receipts is None:
                self._legacy_receipts = {}
                for legacy in sorted((self.root / "raw").glob("*.json")):
                    try:
                        old = json.loads(legacy.read_text())
                    except (OSError, ValueError):
                        continue
                    if isinstance(old, dict) and isinstance(old.get("url"), str):
                        self._legacy_receipts.setdefault(old["url"], []).append(old)
            for old in self._legacy_receipts.get(location, []):
                try:
                    raw_path = Path(old.get("path", ""))
                    if not raw_path.is_file():
                        continue
                    if hashlib.sha256(raw_path.read_bytes()).hexdigest() != old.get(
                        "sha256"
                    ):
                        continue
                    previous = asdict(
                        RawDocument(
                            key,
                            source,
                            str(raw_path),
                            old["sha256"],
                            location,
                            old.get("retrieved_at"),
                            restrictions
                            or RawDocument.__dataclass_fields__["restrictions"].default,
                        )
                    )
                    atomic_json(receipt, previous)
                    break
                except (OSError, ValueError, TypeError):
                    continue
        if remote and previous and not refresh:
            doc = RawDocument(**previous)
            if hashlib.sha256(Path(doc.path).read_bytes()).hexdigest() != doc.sha256:
                raise ValueError("Cached file hash mismatch")
            return doc
        response_headers = {}
        if remote:
            headers = {}
            if previous:
                if previous.get("etag"):
                    headers["If-None-Match"] = previous["etag"]
                if previous.get("last_modified"):
                    headers["If-Modified-Since"] = previous["last_modified"]
            try:
                data, response_headers, _ = self.http.request(location, headers=headers)
            except HTTPError as exc:
                if exc.code == 304 and previous:
                    doc = RawDocument(**previous)
                    if (
                        hashlib.sha256(Path(doc.path).read_bytes()).hexdigest()
                        != doc.sha256
                    ):
                        raise ValueError("Cached file hash mismatch") from exc
                    return doc
                raise
        else:
            data = Path(location).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        suffix = Path(urlparse(location).path).suffix.lower()
        if not re.fullmatch(r"\.[a-z0-9]{1,8}", suffix):
            suffix = ".bin"
        path = self.root / "raw" / (digest + suffix)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.read_bytes() != data:
                raise ValueError("Raw artifact hash mismatch")
        else:
            with path.open("xb") as stream:
                stream.write(data)
        doc = RawDocument(
            key,
            source,
            str(path),
            digest,
            location if remote else source_url,
            datetime.now(UTC).isoformat(),
            restrictions
            or (previous or {}).get("restrictions")
            or RawDocument.__dataclass_fields__["restrictions"].default,
            response_headers.get("ETag"),
            response_headers.get("Last-Modified"),
        )
        atomic_json(receipt, asdict(doc))
        return doc

    def read(self, url: str, *, refresh=False) -> bytes:
        return Path(self.fetch("catalog", url, refresh=refresh).path).read_bytes()
