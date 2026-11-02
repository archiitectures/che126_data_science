"""Calibrated native-marker/peak recovery; one value per physical plotted condition."""
import csv,json,hashlib,statistics
from pathlib import Path
from lxml import etree
from che126_data_science.data_mining.digitize import digitize
from che126_data_science.data_mining.pipeline import Pipeline
RUN=Path(__file__).parent
acq=json.loads((RUN/'temperature_acquisition.json').read_text())
def doc(name):return next(e['document'] for e in acq if e['name']==name)
xml=doc('RSC_PP_XML');text=' '.join(etree.fromstring(Path(xml['path']).read_bytes()).itertext())
assert all(s in text for s in ['128','25','70','30 min'])
rows=[];profiles=[]
url=xml['url']
def add(sample,prop,value,unit,T,kind,context,figure,uncertainty=None,**kw):
 rows.append(dict(sample_id='PMC10680142:'+sample,property=prop,value=value,unit=unit,
 polymer='PEO/PP',separator_architecture='PP support infiltrated with PEO/LiTFSI/ionic-liquid electrolyte',
 coating='PEO/LiTFSI/ionic liquid',sample_form='separator',record_type=kind,
 temperature_C=T,temperature_role='measurement',source_url=url,source_figure=figure,
 electrolyte_salt='LiTFSI',electrolyte_solvent='1-ethyl-3-methylimidazolium bis(trifluoromethanesulfonyl)imide ionic liquid; PEO matrix',
 electrolyte_state='not_reported',material_class='PP-supported solid polymer electrolyte composite',
 method='AC impedance; stainless-steel blocking electrodes; 5 mV; 0.1 Hz-1 MHz; chamber stabilized 30 min' if prop=='ionic_conductivity' else 'Tensile stress-strain curve; 150x12 mm film, 100 mm gauge, 50 mm/min; direction not reported',
 measurement_context=context,uncertainty=uncertainty,
 notes=f"Primary XML {xml['path']}; SHA256 {xml['sha256']}. Solid polymer/ionic-liquid electrolyte-filled support; not pure PP or liquid-soaked neat membrane. "+kw.pop('notes',''),**kw))

# Exact source-reported 25 C scalar values are preferable to reading their markers.
for loading,value in zip([0,20,33,40,50,60,70],[9.6e-6,3.4e-5,5.1e-5,1.2e-4,4.7e-4,1.7e-3,2.9e-3]):
 add(f'PLI({loading})@PP','ionic_conductivity',value,'S/cm',25,'measured',f'IL loading {loading} wt%; source-reported scalar; electrochemistry Figure 3e','3e',notes='Seven ordered values explicitly printed in Results; no graph duplication at 25 C.')
add('PLI(70)@PP','tensile_strength',128,'MPa',25,'measured','IL loading 70 wt%; source-reported room-temperature tensile strength','3b',notes='128 MPa at 25 C stated in primary abstract/results; do not duplicate its representative plotted peak as another experiment.')

# Figure 3f: use four native temperature markers per series, not fitted pixels.
image=Path(doc('RSC_fig3')['path']);sha=hashlib.sha256(image.read_bytes()).hexdigest()
settings=[(0,[85,85,85],[316,309,304,300]),(20,[255,40,40],[299,289,283,277]),
 (33,[20,130,255],[281,275,271,267]),(40,[0,170,115],[265,258,254,250]),
 (50,[190,85,220],[248,239,235,231]),(60,[230,170,20],[241,235,231,228]),
 (70,[0,195,210],[235,231,228,225])]
held=[]
for loading,color,ys in settings:
 for T,x,y in zip([40,50,60,70],[648,682,715,749],ys):
  c={'source_sha256':sha,'source_url':doc('RSC_fig3')['url'],'figure':'3f','caption':'Native ionic-conductivity marker, PP-supported PEO/IL composite',
   'crop':[x-3,y-7,x+4,y+8],'x_reference':[[599,25],[749,70]],'y_reference':[[330,1e-5],[226,1e-2]],'x_unit':'C','y_unit':'S/cm','plot_type':'semilog_y',
   'single_series':True,'series_count':7,'series_label':f'PLI({loading})@PP',
   'mask_polygon':[[x-3,y-7],[x+4,y-7],[x+4,y+8],[x-3,y+8]],'curve_rgb':color,'color_tolerance':100,
   'sample_step_px':1,'max_curve_thickness_px':10,'max_jump_px':10,'calibration_error_px':2}
  out=RUN/'digitized_temperature'/f'PLI{loading}_{T}C';digitize(image,c,out);profiles.append(c)
  pts=list(csv.DictReader((out/'curve_points.csv').open()))
  if not pts:held.append({'sample':loading,'T':T,'reason':'no isolated trace'});continue
  v=statistics.median(float(p['y']) for p in pts)
  # 2-pixel y calibration uncertainty propagated by tracer, then S/cm -> S/m.
  err=max(float(p['uncertainty_y']) for p in pts)*100
  add(f'PLI({loading})@PP','ionic_conductivity',v,'S/cm',T,'digitized_estimate',f'IL loading {loading} wt%; native Figure 3f marker; calibration uncertainty 2 pixels','3f',uncertainty=err,curve_id=pts[0]['curve_id'],notes=f'Figure SHA256 {sha}; calibrated pixel marker x={x}; trace {out}. Nominal source temperature, not additional interpolated samples. Value uncertainty stored in canonical S/m.')

# Figure 6a: recover a peak from each original representative tensile curve.
image=Path(doc('RSC_fig6')['path']);sha=hashlib.sha256(image.read_bytes()).hexdigest()
for T,color,box in [(40,[245,75,80],[285,76,323,99]),(50,[75,145,225],[270,90,304,110]),(60,[45,175,105],[265,110,297,132]),(70,[185,120,225],[313,117,345,138])]:
 x0,y0,x1,y1=box
 c={'source_sha256':sha,'source_url':doc('RSC_fig6')['url'],'figure':'6a','caption':'Maximum stress of a representative tensile trace; not five-replicate mean',
 'crop':box,'x_reference':[[66,0],[374,120]],'y_reference':[[263,0],[14,160]],'x_unit':'strain %','y_unit':'MPa','plot_type':'linear','single_series':True,'series_count':5,'series_label':f'PLI(70)@PP {T} C','mask_polygon':[[x0,y0],[x1,y0],[x1,y1],[x0,y1]],'curve_rgb':color,'color_tolerance':100,'sample_step_px':1,'max_curve_thickness_px':10,'max_jump_px':8,'calibration_error_px':2}
 out=RUN/'digitized_temperature'/f'tensile_{T}C';digitize(image,c,out);profiles.append(c)
 pts=list(csv.DictReader((out/'curve_points.csv').open()))
 if not pts:held.append({'sample':'PLI70 tensile','T':T,'reason':'no isolated trace'});continue
 peak=max(pts,key=lambda p:float(p['y']))
 add('PLI(70)@PP','tensile_strength',float(peak['y']),'MPa',T,'digitized_estimate','Maximum stress of plotted representative curve, not reported five-specimen average; IL loading 70 wt%','6a',uncertainty=float(peak['uncertainty_y']),curve_id=peak['curve_id'],notes=f'Figure SHA256 {sha}; isolated peak region {box}; trace {out}. Native curve maxima only; no elongation-at-break inferred from partially drawn terminal drops.')

path=RUN/'temperature_rows.csv'
with path.open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=sorted({k for r in rows for k in r}));w.writeheader();w.writerows(rows)
(RUN/'temperature_calibrations.json').write_text(json.dumps(profiles,indent=2)+'\n')
(RUN/'temperature_held.json').write_text(json.dumps(held,indent=2)+'\n')
p=Pipeline('data');r=p.ingest('manual',path,context={'filename':path.name,'import_revision':'native_temperature_markers_v1','restrictions':'Primary RSC paper CC BY-NC 3.0; derived marker estimates retain source attribution and uncertainty.'})
a=json.loads(Path(r['artifact_file']).read_text());assert len(a['observations'])==len(rows) and all(r['review_status']=='accepted' for r in a['observations'])
print('temperature observations',len(rows),'held',held,flush=True)
