"""Audit cross-publication evidence sharing; do not equate it with independent experiments."""
import csv,json,re
from collections import defaultdict
from pathlib import Path
rows=list(csv.DictReader(open('datasets/master_observations.csv')))
byid={r['observation_id']:r for r in rows}
links=json.load(open('datasets/unique_point_evidence.json'))
result=[]
for e in links:
 group=[byid[i] for i in e['supporting_observation_ids']]
 pubs={m[0] for r in group if (m:=re.search(r'(?:US|EP|WO|JP|CN|KR)\d{6,}[A-Z]\d?',r['source_url']))}
 if len(pubs)<2:continue
 result.append({'unique_point_id':e['unique_point_id'],'property':group[0]['property'],'value':group[0]['value'],'unit':group[0]['unit'],'polymer':group[0]['polymer'],'publication_count':len(pubs),'publications':';'.join(sorted(pubs)),'interpretation':'Equal recorded scientific context already grouped; independent experiment and patent-family identity not certified'})
with open('datasets/cross_publication_context_audit.csv','w',newline='') as f:
 columns=['unique_point_id','property','value','unit','polymer','publication_count','publications','interpretation']
 w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows(result)
print('cross-publication exact-context groups',len(result))
