"""Bounded public-reference traversal through the existing source pipeline."""
import json
import re
from collections import deque
from pathlib import Path
from bs4 import BeautifulSoup
from che126_data_science.data_mining.pipeline import Pipeline
from che126_data_science.data_science.master import atomic_json

root=Path('data/runs/2026-10-16_patents')
p=Pipeline(root)
state=json.loads((root/'run_progress.json').read_text())
queue=deque(state['pending'])
reports=state['reports']
seen={r['publication_number'] for r in reports}
titles=set()
start=len(seen)
while queue and len(seen)<start+150:
    number=queue.popleft()
    if number in seen: continue
    seen.add(number)
    try:
        result=p.ingest('patents',number)
        result['publication_number']=number
        reports.append(result)
        artifact=json.loads(Path(result['artifact_file']).read_text())
        soup=BeautifulSoup(Path(artifact['document']['path']).read_text(),'lxml')
        for row in soup.select('tr[itemprop]'):
            title=row.select_one('[itemprop="title"]'); pub=row.select_one('[itemprop="publicationNumber"]')
            if not title or not pub: continue
            text=title.get_text(' ',strip=True).lower()
            identifier=pub.get_text(strip=True)
            if not re.fullmatch(r'US\d+[AB]\d?',identifier): continue
            if not re.search(r'separator|microporous.*(?:film|membrane)',text):continue
            # One publication per exact title, reducing grant/application repeats.
            if text in titles:continue
            titles.add(text)
            if identifier not in seen:queue.append(identifier)
        print(json.dumps({'n':len(seen),'publication':number,'accepted':result['accepted'],'review':result['review'],'queued':len(queue)}),flush=True)
    except (OSError,ValueError,RuntimeError) as exc:
        reports.append({'publication_number':number,'status':'failed','error':str(exc)})
        print(json.dumps(reports[-1]),flush=True)
    atomic_json(root/'run_progress.json',{'reports':reports,'pending':list(queue)})
    if len(seen)%10==0:p.aggregate()
summary=p.aggregate()
atomic_json(root/'run_summary.json',{'summary':summary,'reports':reports,'pending':list(queue)})
print(json.dumps(summary),flush=True)
