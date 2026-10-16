import json
from dataclasses import asdict
from pathlib import Path
from che126_data_science.data_mining.sources import discover_celgard,discover_fsri,save_download
from che126_data_science.data_mining.celgard import pdf_text,parse_datasheet
from che126_data_science.data_mining.fsri import extract_public_curves
from che126_data_science.data_science.observations import write_observations
root=Path('data_mining/runs/2026-10-14_pe_pp')
docs={}
for material in ['polyethylene','polypropylene']:
 for source,fn in [('celgard',discover_celgard),('fsri',discover_fsri)]:
  try:
   found=fn(material)
   for d in found: docs[d.url]=d
   print(source,material,len(found),flush=True)
  except Exception as e: print(source,type(e).__name__,str(e),flush=True)
(root/'discovery.json').write_text(json.dumps([asdict(d) for d in docs.values()],indent=2))
rows=[];reports=[]
for url,d in docs.items():
 try:
  receipt=save_download(url,'data/raw')
  report={'document':asdict(d),'receipt':receipt}
  if d.source=='celgard':
   product=d.title.replace('Celgard®','').strip()
   material='PP/PE/PP' if 'PE' in d.material.replace('Celgard','') else 'PP'
   result=parse_datasheet(pdf_text(receipt['path']),product=product,material=material,source_url=url)
   rows.extend(result.pop('observations'));report.update(result)
  else:
   curves=extract_public_curves(Path(receipt['path']).read_text())
   slug=url.rsplit('/',1)[-1]
   (root/(slug+'_curves.json')).write_text(json.dumps(curves,indent=2))
   report['figures']=len(curves)
  reports.append(report)
  print(d.title,'saved',flush=True)
 except Exception as e:
  reports.append({'document':asdict(d),'error':str(e)})
  print(d.title,type(e).__name__,str(e),flush=True)
(root/'source_reports.json').write_text(json.dumps(reports,indent=2))
write_observations(rows,root/'celgard_observations.csv')
print('observations',len(rows),flush=True)
