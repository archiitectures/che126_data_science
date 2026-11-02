"""Source-verified experimental diffusion/tension and phase-extrapolated Cp references."""
import csv,json,hashlib
from pathlib import Path
from lxml import etree
import pymupdf
from che126_data_science.data_mining.pipeline import Pipeline
RUN=Path(__file__).parent
acq=json.loads((RUN/'benchmark_acquisition.json').read_text())
rows=[]
def document(name):
 e=next(e for e in acq if e['name']==name and 'document' in e)['document']
 assert hashlib.sha256(Path(e['path']).read_bytes()).hexdigest()==e['sha256']
 return e

def add(doc,sample,prop,value,unit,temp,kind,method,context,**kw):
 rows.append(dict(sample_id=sample,property=prop,value=value,unit=unit,polymer='PE',sample_form='bulk_reference',temperature_C=temp,temperature_role='measurement',record_type=kind,source_url=doc['url'],method=method,measurement_context=context,notes=f"Primary source {doc['path']}; SHA256 {doc['sha256']}. "+kw.pop('notes',''),**kw))

# A fitted macroscopic chain coefficient, not the poorly constrained segmental Ds.
doc=document('diffusion');root=etree.fromstring(Path(doc['path']).read_bytes())
table=root.xpath('//table-wrap[@id="molecules-25-05813-t001"]')[0]
cells=[''.join(c.itertext()).strip() for c in table.xpath('.//tbody/tr')[0]]
assert '7.0' in cells[1] and '13' in cells[1] and '8.0' in cells[2] and '14' in cells[2],cells
add(doc,'PMC7762995:SRM1482 melt','polymer_self_diffusion_coefficient',7e-13,'m2/s',426-273.15,'measured','PGSE NMR; macroscopic Dc fitted to experimental effective-diffusion model Eq. 9','Linear PE melt at 426 K; Mn 11400 g/mol, Mw 13600 g/mol; diffusion time 80 ms; fitted Dc not segmental Ds',source_table='Table 1',source_column='Dc estimate',uncertainty=8e-14,material_grade='linear PE SRM 1482',notes='Fit standard error 8.0e-14 m2/s. Model fit to experimental data; not a direct trajectory or independent fit replicate. Ds has high uncertainty and is not admitted as chain self diffusion.')

# Phase-specific estimates based on calorimetry; not direct measurements of pure phases.
doc=document('phase_Cp_pdf');pdf=pymupdf.open(doc['path']);page=pdf[7];words=page.get_text('words')
entries=[]
for w in words:
 if not 45<w[0]<80:continue
 try:T=float(w[4])
 except ValueError:continue
 if not 273<=T<=360:continue
 cy=(w[1]+w[3])/2
 def cell(left,right):
  found=[v[4] for v in words if left<v[0]<right and abs((v[1]+v[3])/2-cy)<1]
  assert len(found)==1,(T,left,found)
  return float(found[0])
 entries.append((T,cell(95,130),cell(340,380)))
assert len(entries)==11,entries
assert next(v for v in entries if v[0]==298.15)==(298.15,22.6,33.57)
for T,crystal,amorph in entries:
 for phase,value,column in [('crystalline',crystal,'Crystalline Cp'),('amorphous',amorph,'Amorphous Cp')]:
  add(doc,f'NIST1974:extrapolated {phase} PE','specific_heat_capacity',value,'J/(mol_CH2 K)',round(T-273.15,8),'calculated','Phase-fraction extrapolation of adiabatic calorimetry; Table 3','Extrapolated pure-phase heat capacity; not a directly measured pure-phase specimen; base mole CH2 mass 14.027 g/mol',source_page=8,source_table='Table 3',source_column=column,material_grade=phase,material_class='phase-extrapolated PE reference',notes=f'Printed T={T} K, Cp={value} J/(base mol CH2 K). Converted using the paper\'s 14.027 g/mol, not an assumed whole-chain molar mass. Original PDF table rendered and inspected. Values outside 273.15-360 K not imported in this MD-targeted pass.')

# Exact endpoint values explicitly reported in the author's thesis prose.
doc=document('surface_tension_university');pdf=pymupdf.open(doc['path']);text=pdf[55].get_text()
assert all(s in text for s in ['20.5','25.5','190','125','1500','500'])
for T,pressure,value in [(125,500,25.5),(190,1500,20.5)]:
 add(doc,f'Wei2009:HDPE in N2:{pressure}psi','surface_tension',value,'mJ/m2',T,'measured','ADSA-P pendant-drop analysis; equilibrium endpoint values reported in thesis prose','Molten HDPE / supercritical N2 interface; pressure '+str(pressure)+' psi; not a polymer-vacuum surface',source_page=56,source_figure='18',material_grade='HDPE',material_class='molten HDPE interface reference',notes='Endpoints printed in primary thesis on printed page 43 (PDF page 56); precision 0.1 mJ/m2. Source unit mJ/m2 equals mN/m for interfacial tension. Do not generate samples from its regression formula or treat pressure as ambient.')

path=RUN/'md_benchmark_rows.csv'
with path.open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=sorted({k for r in rows for k in r}));w.writeheader();w.writerows(rows)
p=Pipeline('data')
r=p.ingest('manual',path,context={'filename':path.name,'import_revision':'primary_MD_benchmarks_v1','restrictions':'Extracted primary research facts; original source reuse terms retained; pure-phase Cp is calculated not directly measured.'})
a=json.loads(Path(r['artifact_file']).read_text());assert len(a['observations'])==25
assert all(r['review_status']=='accepted' for r in a['observations']),a
print('accepted MD benchmarks',len(rows))
