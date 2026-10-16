"""Report honest progress toward the separator collection target."""
import csv,json
from collections import Counter,defaultdict
from pathlib import Path
from che126_data_science.data_science.master import atomic_json,csv_bytes,atomic_bytes
from che126_data_science.data_science.observations import UNITS

root=Path('data_mining/runs/2026-10-16_1000_target')
rows=list(csv.DictReader(open('data/processed/master_observations.csv')))
review=list(csv.DictReader(open('data/processed/review_queue.csv')))
before=json.load(open('data/processed/pre_collection_1000.json'))
old=set(before['observation_ids'])
separator=[r for r in rows if r['sample_form'] in {'separator','separator_component'}]
measured=[r for r in separator if r['record_type']=='measured']
thermal=[r for r in measured if r['temperature_C']]
coverage=defaultdict(list)
for r in rows:coverage[(r['sample_form'],r['polymer'] or 'not_reported',r['property'],r['record_type'])].append(r)
entries=[]
for (form,polymer,prop,kind),group in sorted(coverage.items()):
 temps=sorted({float(r['temperature_C']) for r in group if r['temperature_C']})
 entries.append(dict(sample_form=form,polymer=polymer,property=prop,record_type=kind,
  observations=len(group),known_temperature=sum(bool(r['temperature_C']) for r in group),
  temperatures_C=';'.join(map(str,temps)),min_temperature_C=min(temps) if temps else '',
  max_temperature_C=max(temps) if temps else ''))
atomic_bytes(root/'coverage.csv',csv_bytes(entries,list(entries[0])))
summary={'target':1000,'starting_accepted':before['accepted'],'accepted':len(rows),
 'net_accepted_gain':len(rows)-before['accepted'], 'new_observation_ids':sum(r['observation_id'] not in old for r in rows),
 'separator_or_component_rows':len(separator),'measured_separator_rows':len(measured),
 'temperature_resolved_measured_separator_rows':len(thermal),
 'temperature_resolved_measured_separator_shortfall':max(0,1000-len(thermal)),
 'bulk_reference_rows':sum(r['sample_form']=='bulk_reference' for r in rows),
 'review':len(review),'properties':dict(Counter(r['property'] for r in rows)),
 'separator_properties':dict(Counter(r['property'] for r in separator)),
 'missing_separator_properties':sorted(set(UNITS)-{r['property'] for r in separator}),
 'missing_measured_separator_properties':sorted(set(UNITS)-{r['property'] for r in measured}),
 'separator_measured_properties':dict(Counter(r['property'] for r in measured)),
 'temperature_resolved_separator_properties':dict(Counter(r['property'] for r in thermal)),
 'review_reasons':dict(Counter(r['quality_flag'] for r in review)),
 'measured_separator_temperatures_C':sorted({float(r['temperature_C']) for r in thermal}),
 'measured_separator_rows_with_polymer':sum(bool(r['polymer']) for r in measured),
 'separator_types':dict(Counter(r['polymer'] or 'not_reported' for r in separator)),
 'source_counts':dict(Counter(r['source_type'] for r in rows))}
atomic_json(root/'summary.json',summary)
print(json.dumps(summary,indent=2))
