import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

manifest = json.loads(Path("fsri-manifest.json").read_text())
source_commit = "a432697e4b7d40f642b5cc8f384506439ebb32df"
exports = []
for item in manifest:
    path = item["path"]
    url = f"https://raw.githubusercontent.com/ulfsri/fsri_materials_database/{source_commit}/{path}"
    raw = urlopen(url, timeout=30).read()
    digest = hashlib.sha1(f"blob {len(raw)}\\0".encode() + raw).hexdigest()
    assert digest == item["sha"], (path, digest, item["sha"])
    text = raw.decode("utf-16" if path.endswith(".tst") else "utf-8")
    if path.endswith(".tst"):
        marker = "Results Table -- SI Units"
        assert marker in text, path
        payload = {"header": text.splitlines()[:45],
                   "results_si": text.rsplit(marker, 1)[1]}
    else:
        payload = {"csv": text}
    exports.append({"path": path, "blob_sha": item["sha"], "source_url": url, **payload})
Path("fsri_hfm_extract.json").write_text(json.dumps(
    {"source_commit": source_commit, "exports": exports}, indent=2) + "\\n")
print(f"Extracted {len(exports)} source files at {source_commit}")
