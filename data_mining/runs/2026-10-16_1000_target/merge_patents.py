"""Merge immutable run documents into the master without re-downloading."""
import json
from pathlib import Path
from che126_data_science.data_mining.pipeline import Pipeline
from che126_data_science.data_mining.acquisition import RawDocument
from che126_data_science.data_science.master import atomic_json

source=Pipeline('data/runs/2026-10-16_patents')
master=Pipeline('data')
results=[]
for entry in source.manifest['documents'].values():
    results.append(master._ingest_document(RawDocument(**entry['document']),entry['context'],allow_fallback_fetch=False))
summary=master.aggregate()
atomic_json(Path('data_mining/runs/2026-10-16_1000_target/merge_summary.json'),{'documents':len(results),'outputs':summary})
print(json.dumps(summary,indent=2))
