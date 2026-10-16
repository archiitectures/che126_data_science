import json
from collections import Counter
from dataclasses import replace
from pathlib import Path
from che126_data_science.data_science.observations import Observation,read_observations,write_observations,coverage
root=Path('data_mining/runs/2026-10-14_pe_pp')
reports=json.loads((root/'source_reports.json').read_text())
by_url={r['document']['url']:r for r in reports}
rows=[];quarantine=[]
for row in read_observations(root/'celgard_observations.csv'):
 d=by_url[row.source_url]['document']
 row=replace(row,notes=row.notes+' Product construction: '+d['material'])
 if row.sample_id in ['celgard_4560','celgard_5550']:
  quarantine.append(row);continue
 rows.append(row)
# Reviewed against the saved official Q18G1SY PDF, page 1. Typography prevented
# the narrow automatic parser from matching these rows; do not guess tensile units.
q=next(r for r in reports if r['document']['title']=='Celgard® Q18G1SY')
for prop,value,kind,direction in [('porosity',53,'calculated','unspecified'),('thermal_shrinkage',2.5,'typical','MD'),('thermal_shrinkage',8,'maximum','MD'),('thermal_shrinkage',0,'typical','TD'),('thermal_shrinkage',1.5,'maximum','TD')]:
 rows.append(Observation(record_id=f'celgard_Q18G1SY_reviewed_{prop}_{direction}_{kind}',sample_id='celgard_Q18G1SY',material='PP/PE/PP',property=prop,value=value,unit='%',source_url=q['document']['url'],source_locator='PDF page 1; Basic Film Properties; '+prop+' '+direction,sample_form='separator',temperature_C=120 if prop=='thermal_shrinkage' else None,temperature_role='exposure' if prop=='thermal_shrinkage' else 'unknown',direction=direction,conditions='heat exposure 1 hour; measurement temperature unspecified' if prop=='thermal_shrinkage' else 'unspecified',value_type=kind,raw_value=str(value),raw_unit='%',notes='Reviewed manual extraction; ceramic-coated trilayer: 16 um PP/PE/PP membrane plus 2 um ceramic on one side. Unknown electrolyte state.'))
write_observations(rows,root/'separator_observations.csv')
write_observations(quarantine,root/'laminate_component_review.csv')
thermal=[]
for report in reports:
 d=report['document']
 if d['source']!='fsri' or 'error' in report:continue
 slug=d['url'].rsplit('/',1)[-1]
 for c in json.loads((root/(slug+'_curves.json')).read_text()):
  xlabel=c['xaxis'].get('title',{}).get('text','');ylabel=c['yaxis'].get('title',{}).get('text','')
  if xlabel!='Temperature (&deg;C)' or ylabel not in ['Specific Heat (J/kgK)','Thermal Conductivity (W/mK)']:continue
  prop,unit=('specific_heat_capacity','J/(kg K)') if ylabel.startswith('Specific Heat') else ('thermal_conductivity','W/(m K)')
  for trace in c['traces']:
   assert len(trace['x'])==len(trace['y'])
   for i,(temp,value) in enumerate(zip(trace['x'],trace['y'])):
    uncertainty=trace.get('error_y',{}).get('array',[])
    thermal.append(Observation(record_id=f'fsri_public_{slug}_{c["figure"]}_{trace["name"]}_{i}',sample_id=f'fsri_public_{slug}_{trace["name"]}',material=d['material'],property=prop,value=float(value),unit=unit,source_url=d['url'],source_locator=f'Public plot {c["figure"]}; trace {trace["name"]}; point {i}; raw SHA256 {report["receipt"]["sha256"]}',sample_form='bulk_reference',temperature_C=float(temp),temperature_role='measurement',method='FSRI HFM published aggregate',conditions='FSRI '+trace['name']+'; Wet means unconditioned, not electrolyte soaked',value_type='calculated',raw_value=str(value),raw_unit=unit,notes='Published aggregate, not an independent specimen measurement. '+('Overlaps existing HDPE/LDPE raw HFM evidence. ' if slug.startswith(('high-density','low-density')) else '')+('Source plotted error bar: '+str(uncertainty[i])+' '+unit+'; interpretation retained in source.' if uncertainty else '')))
write_observations(thermal,root/'bulk_thermal_aggregates.csv')
(root/'coverage.json').write_text(json.dumps(coverage(rows,['porosity','thickness','tensile_strength','puncture_force','thermal_shrinkage'],[25,60,90,105,120]),indent=2))
summary={'separator_scalar_records':len(rows),'separator_products':len({r.sample_id for r in rows}),'by_material':dict(Counter(r.material for r in rows)),'by_property':dict(Counter(r.property for r in rows)),'by_value_type':dict(Counter(r.value_type for r in rows)),'exposure_temperatures_C':sorted({r.temperature_C for r in rows if r.temperature_C is not None}),'unknown_temperature_records':sum(r.temperature_C is None for r in rows),'laminate_records_held_for_review':len(quarantine),'bulk_thermal_aggregate_records':len(thermal),'new_bulk_aggregate_records_excluding_HDPE_LDPE':sum(not r.material.startswith(('high density','low density')) for r in thermal),'bulk_thermal_temperatures_C':sorted({r.temperature_C for r in thermal}),'google_status':'blocked pending explicit billing-link approval','google_executed_queries':0}
(root/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
