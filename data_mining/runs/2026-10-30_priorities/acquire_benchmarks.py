"""Bounded free primary-source acquisition; no billing or credentials."""
import json
from dataclasses import asdict
from pathlib import Path
from che126_data_science.data_mining.acquisition import DocumentStore,HTTPClient
store=DocumentStore('data/runs/2026-10-30_md_benchmarks',http=HTTPClient(timeout=35,max_bytes=25_000_000))
urls={
 'diffusion':'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC7762995/fullTextXML',
 'phase_Cp':'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6742827/fullTextXML',
 'phase_Cp_pdf':'https://nvlpubs.nist.gov/nistpubs/jres/78A/jresv78An3p387_A1b.pdf',
 'surface_tension':'https://www.collectionscanada.gc.ca/obj/thesescanada/vol2/OWTU/TC-OWTU-4551.pdf',
 'PVT':'https://www.collectionscanada.gc.ca/obj/s4/f2/dsk1/tape7/PQDD_0026/MQ50594.pdf',
}
run=Path(__file__).parent;results=[]
for name,url in urls.items():
 try:
  doc=store.fetch('literature',url,restrictions='Primary public research source; retain original reuse terms. Extracted facts and provenance only; no document redistribution.')
  results.append({'name':name,'document':asdict(doc)})
  print(name,'downloaded',Path(doc.path).stat().st_size,flush=True)
 except Exception as e:
  results.append({'name':name,'url':url,'error':str(e)})
  print(name,type(e).__name__,str(e),flush=True)
 (run/'benchmark_acquisition.json').write_text(json.dumps(results,indent=2)+'\n')
