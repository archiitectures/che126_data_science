"""Source-cell replay of suspect legacy definitions; explicit ledger, never raw overwrites."""
import csv,json,re
from collections import Counter,defaultdict
from pathlib import Path
from che126_data_science.data_mining.acquisition import RawDocument
from che126_data_science.data_mining.patent_html import extract_patent
from che126_data_science.data_mining.normalization import ALIASES
RUN=Path(__file__).parent
baseline=RUN/'before/datasets/master_observations.csv'
rows=list(csv.DictReader(baseline.open()))
manifest=json.loads(Path('data/processed/source_manifest.json').read_text())
entries={}
for e in manifest['documents'].values():
 if e['document']['source']=='patents' and not e['document']['path'].endswith('.pdf'):
  entries.setdefault(e['document']['sha256'],e)
selected=[]
for r in rows:
 if r['source_type']!='patents':continue
 label=r['original_property_label']
 matches={p for rx,p in ALIASES if re.search(rx,label,re.I)}
 suspicious=(len(matches)>1 or (r['property']=='thermal_shrinkage' and float(r['value'])>100) or (r['property']=='pore_size' and float(r['value'])>10) or (r['property']=='thickness' and float(r['value'])==0) or ('packing density' in label.lower()))
 if suspicious:selected.append(r)
bysha=defaultdict(list)
for r in selected:bysha[r['source_sha256']].append(r)
revisions={};decisions=[]
for sha,group in bysha.items():
 entry=entries.get(sha)
 if not entry:continue
 context=dict(entry['context']);context.pop('accepted_observation_ids',None);context.pop('reviewed_conditions',None)
 fresh,_=extract_patent(RawDocument(**entry['document']),context)
 def key(r):return (r.source_table,str(r.source_row),str(r.source_column),float(r.original_value),r.direction)
 fresh_by=defaultdict(list)
 for r in fresh:
  try:fresh_by[key(r)].append(r)
  except (ValueError,TypeError):pass
 for old in group:
  k=(old['source_table'],old['source_row'],old['source_column'],float(old['original_value']),old['direction'] or None)
  candidates=fresh_by.get(k,[])
  replacements=[r for r in candidates if r.review_status=='accepted' and r.property!=old['property']]
  if len(replacements)==1:
   n=replacements[0]
   if n.property=='packing_density':
    # Packing density belongs to a coating, not to the inherited PE substrate.
    changes={'property':'packing_density','original_property_label':n.original_property_label,
      'sample_form':'separator_component','polymer':None,'material_class':'porous coating packing density',
      'temperature_C':None,'temperature_role':'unknown','method':None,
      'measurement_context':'Porous coating-layer packing density; not neat polymer matrix density'}
   else:
    fields=['property','original_property_label','original_unit','unit','value','conversion_metadata','temperature_C','temperature_role','duration_min','method','measurement_context','shrinkage_basis']
    changes={f:getattr(n,f) for f in fields}
   reason='Replayed exact primary table cell with corrected property-heading boundaries; raw numeric cell unchanged'
  elif old['property']=='thermal_shrinkage' and float(old['value'])>100:
   changes={};reason='Positive length/area shrinkage above 100% is incompatible with its definition; suspected adjacent elongation/header attribution requires explicit source correction'
  elif old['property']=='pore_size' and float(old['value'])>10:
   changes={};reason='Primary pore-size unit/header is ambiguous or inconsistent with the imported scale; quarantine pending original-PDF unit and sample review, not an automatic unit guess'
  elif old['property']=='thickness' and float(old['value'])==0:
   changes={};reason='Zero coating thickness/absent layer must not be treated as a measured separator thickness; pending explicit absent-component representation'
  elif 'packing density' in old['original_property_label'].lower():
   changes={'property':'packing_density','sample_form':'separator_component','polymer':None,'material_class':'porous coating packing density','temperature_C':None,'temperature_role':'unknown','method':None,'measurement_context':'Source labels packing density; this is not neat polymer matrix density'}
   reason='Primary property label explicitly identifies coating packing density, not bulk polymer density'
  else:continue
  rev={'source_sha256':sha,'reason':reason,'changes':changes,'source_coordinates':{'table':old['source_table'],'row':old['source_row'],'column':old['source_column']}}
  revisions[old['observation_id']]=rev
  decisions.append({'observation_id':old['observation_id'],'sample_id':old['sample_id'],'old_property':old['property'],'old_value':old['value'],'action':'correct' if changes else 'review','reason':reason,'source_url':old['source_url']})
ledger_path=Path('data_mining/reviewed_observation_revisions.json')
existing=json.loads(ledger_path.read_text()) if ledger_path.exists() else {}
for revision in revisions.values():
 if revision.get('changes',{}).get('property')=='packing_density':
  revision['changes'].update(material_identity_status='component_recipe_not_linked',material_identity_reason='Packing density applies to the porous coating, not inherited PE substrate composition.',material_identity_evidence=json.dumps({'source_sha256':revision['source_sha256'],'locator':revision['source_coordinates'],'basis':'Explicit packing-density property label; polymer composition not assigned'}))
existing.update(revisions)
ledger_path.write_text(json.dumps(existing,indent=2)+'\n')
manifest['curation_file']='data_mining/reviewed_observation_revisions.json'
Path('data/processed/source_manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
(RUN/'definition_review.json').write_text(json.dumps(decisions,indent=2)+'\n')
print('screened',len(selected),'sources',len(bysha),'revisions',len(revisions),Counter(d['action'] for d in decisions),flush=True)
