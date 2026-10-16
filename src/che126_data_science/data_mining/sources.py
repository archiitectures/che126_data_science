"""Small, public-source discovery clients; discovery is not measurement extraction."""

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

ALIASES = {
    "polyethylene": ("polyethylene", "HDPE", "LDPE", "UHMWPE", "PE"),
    "polypropylene": ("polypropylene", "PP"),
    "pvdf": ("PVDF", "polyvinylidene fluoride"),
    "ptfe": ("PTFE", "polytetrafluoroethylene"),
    "polyimide": ("polyimide", "PI"),
    "cellulose": ("cellulose",),
    "pan": ("PAN", "polyacrylonitrile"),
}


def material_terms(material: str) -> tuple[str, ...]:
    """Expand family names, but do not broaden a requested grade to its family."""
    material = material.strip()
    if not material:
        raise ValueError("material must not be blank")
    for key, names in ALIASES.items():
        if material.casefold() == key or material.casefold() == names[-1].casefold():
            return names
    return (material,)


def matches_material(text: str, material: str) -> bool:
    # Boundaries prevent PE from matching 'properties' or PP from matching 'supply'.
    text = re.sub(r"polyethylene[ -]+terephthalate", "PET", text, flags=re.IGNORECASE)
    return any(
        re.search(
            r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", text, re.IGNORECASE
        )
        for term in material_terms(material)
    )


def read_url(url: str, *, max_bytes: int = 20_000_000, timeout: float = 30) -> bytes:
    """Bounded HTTPS reads. HTTP/auth/rate-limit errors are deliberately visible."""
    if urlparse(url).scheme != "https" or max_bytes <= 0 or timeout <= 0:
        raise ValueError("HTTPS URL and positive download limits required")
    request = Request(url, headers={"User-Agent": "che126-data-science/0.1"})
    with urlopen(request, timeout=timeout) as response:
        if urlparse(response.url).scheme != "https":
            raise ValueError("Refusing non-HTTPS redirect")
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError(f"Download exceeds {max_bytes} bytes")
    return data


def save_download(url: str, directory: str | Path) -> dict:
    """Content-addressed raw bytes plus an immutable acquisition receipt."""
    data = read_url(url)
    digest = hashlib.sha256(data).hexdigest()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    suffix = Path(urlparse(url).path).suffix.lower()
    if not re.fullmatch(r"\.[a-z0-9]{1,8}", suffix):
        suffix = ".bin"
    target = directory / (digest + suffix)
    if target.exists():
        if target.read_bytes() != data:
            raise ValueError("Existing raw artifact does not match its hash")
    else:
        with target.open("xb") as stream:
            stream.write(data)
    receipt = {
        "url": url,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "sha256": digest,
        "bytes": len(data),
        "path": str(target),
    }
    # Receipt per acquisition: identical bytes can legitimately have different URLs.
    receipt_path = directory / (
        digest
        + "-"
        + hashlib.sha256(json.dumps(receipt).encode()).hexdigest()[:16]
        + ".json"
    )
    with receipt_path.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2)
    return receipt


@dataclass(frozen=True)
class Document:
    source: str
    material: str
    title: str
    url: str


class _CelgardPage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.documents = []
        self.in_item = False
        self.depth = 0
        self.parts = []
        self.url = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "div" and "ds-item" in attrs.get("class", "").split():
            self.in_item, self.depth, self.parts, self.url = True, 0, [], ""
        if self.in_item:
            if tag == "div":
                self.depth += 1
            if tag == "a" and attrs.get("href", "").lower().endswith(".pdf"):
                self.url = urljoin("https://www.celgard.com", attrs["href"])

    def handle_data(self, data):
        if self.in_item and data.strip():
            self.parts.append(data.strip())

    def handle_endtag(self, tag):
        if self.in_item and tag == "div":
            self.depth -= 1
            if self.depth == 0:
                if self.url and urlparse(self.url).hostname == "www.celgard.com":
                    self.documents.append(
                        Document(
                            "celgard", " ".join(self.parts), self.parts[0], self.url
                        )
                    )
                self.in_item = False


def discover_celgard(material: str, *, html: str | None = None) -> list[Document]:
    """Find current official product PDFs by polymer family or product number."""
    parser = _CelgardPage()
    parser.feed(
        html
        if html is not None
        else read_url("https://www.celgard.com/product-data").decode("utf-8")
    )
    if not parser.documents:
        raise ValueError(
            "No Celgard datasheets found; product page layout may have changed"
        )
    return [d for d in parser.documents if matches_material(d.material, material)]


def discover_fsri(material: str) -> list[Document]:
    """Search the official public catalog, including all result pages.

    Full family names are used for catalog search (rather than short substrings).
    Catalog entries are leads; preserve retrieved metadata before extracting data.
    """
    term = material_terms(material)[0]
    base = "https://materials.fsri.org"
    pending = [base + "/search?" + urlencode({"search[search_text]": term})]
    visited, found = set(), {}
    while pending:
        url = pending.pop(0)
        if url in visited:
            continue
        if len(visited) >= 100:
            raise ValueError(
                "FSRI catalog exceeded 100 pages; narrow the material search"
            )
        visited.add(url)
        html = read_url(url).decode("utf-8")
        for href in re.findall(r'href="([^"#]+)"', html):
            href = unescape(href)
            target = urljoin(base, href)
            parsed = urlparse(target)
            if parsed.hostname != "materials.fsri.org":
                continue
            if parsed.path.startswith("/materialdetail/"):
                title = parsed.path.rsplit("/", 1)[-1].replace("-", " ")
                if matches_material(title, material):
                    found[target] = Document("fsri", title, title, target)
            elif (
                parsed.path == "/search"
                and "page=" in parsed.query
                and target not in visited
            ):
                pending.append(target)
    return list(found.values())


def polyinfo_plan(
    material: str, properties: list[str], temperatures: list[float]
) -> dict:
    """Prepare an assisted search; never scrape the authenticated NIMS database."""
    return {
        "source": "NIMS PoLyInfo",
        "url": "https://polymer.nims.go.jp/",
        "material_terms": material_terms(material),
        "requested_properties": properties,
        "requested_temperatures_C": temperatures,
        "instructions": [
            "Sign in through DICE/MatNavi and use Basic, Advanced or Text search.",
            "Inspect measurement conditions and original literature for each result.",
            "NIMS prohibits scraping and mass downloading; this tool makes no data requests.",
            "Import only records you are permitted to use with the observation CSV template.",
            "Obtain NIMS permission before redistributing its data.",
        ],
    }


def documents_json(documents: list[Document]) -> list[dict]:
    return [asdict(document) for document in documents]
