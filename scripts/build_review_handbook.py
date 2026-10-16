"""Generate a source-grounded newcomer handbook for the automation code review."""
import json
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/pdf/code_review_handbook.pdf'
S=getSampleStyleSheet()
S.add(ParagraphStyle(name='Body',fontName='Helvetica',fontSize=10,leading=14.5,spaceAfter=10))
S.add(ParagraphStyle(name='Deck2',fontName='Helvetica',fontSize=13,leading=18,textColor=colors.HexColor('#436175'),spaceAfter=18))
S.add(ParagraphStyle(name='Cell2',fontName='Helvetica',fontSize=9,leading=12))
S.add(ParagraphStyle(name='Mono2',fontName='Courier',fontSize=8,leading=11,backColor=colors.HexColor('#EDF4F5'),borderPadding=8,spaceBefore=7,spaceAfter=12))
for name in ['Title','Heading1','Heading2']:S[name].textColor=colors.HexColor('#18394B')
S['Title'].alignment=0;S['Title'].fontSize=27;S['Title'].leading=32
story=[]
def p(t,style='Body'):story.append(Paragraph(t,S[style]))
def page(n,title,deck):
 if story:story.append(PageBreak())
 p(f'CHE126 / CODE REVIEW HANDBOOK / {n:02d}','Heading2');p(title,'Title');p(deck,'Deck2')
def h(t):p(t,'Heading2')
def code(t):p(escape(t).replace('\n','<br/>'),'Mono2')
def table(headers,rows,widths):
 data=[[Paragraph(escape(str(c)),S['Cell2']) for c in row] for row in [headers]+rows]
 t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#DCECEE')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,-1),.4,colors.HexColor('#CCD8DD'))]))
 story.extend([t,Spacer(1,12)])

page(1,'Understand the pipeline\nand its code review','A practical guide for a new researcher or developer. Evidence, architecture, operation, fixes and remaining boundaries. Snapshot: 16 October 2026.')
p('This project collects published evidence about battery separator materials and how their properties depend on temperature. It preserves source documents, extracts numerical tables and instrument results, normalizes explicit units, and exports accepted observations alongside a review queue.')
p('The central review question is whether collection can run across different sources without a person interpreting every file. Supported layouts run automatically. Unfamiliar layouts, uncertain units, conflicting protocols and image calibration still need attention. A passing test suite demonstrates the covered cases; it cannot certify every future source.')
h('How to use this handbook')
table(['Pages','What you will learn'],[['2-3','Project boundaries, architecture and file ownership'],['4-5','Observation semantics, temperature and uniqueness'],['6-7','Source capabilities and daily operation'],['8-10','Review findings, fixes and regression evidence'],['11-12','Efficiency decisions and current collection results'],['13-14','Contributor workflow, troubleshooting and reading map']],[65,403])
p('All paths in this handbook are relative to the repository che126_data_science unless otherwise stated. The PDF is generated from scripts/build_review_handbook.py. It documents the actual implementation rather than a proposed system.')

page(2,'What the project owns','Data acquisition and analysis for the ChE126 separator study.')
h('Scientific objective')
p('Collect porosity, tensile and puncture behavior, thickness, pore size, thermal behavior and other supported properties across materials and conditions. PE, PP and multilayer polyolefin separators are prominent sources; the discovery interface also accepts PVDF, PTFE, polyimide, cellulose and PAN. A material search is a lead, not proof of specimen composition.')
h('Evidence categories matter')
p('A manufacturer typical value, an experimental table entry, a patent claim and a calculated quantity have different meanings. The master keeps record_type and statistic separately. A maximum specification is not a measured maximum from a known experiment. Unknown metadata stays unknown.')
p('FSRI thermal data describe bulk reference materials. They can inform reference comparisons, but do not establish separator-film porosity, mechanical strength or electrolyte response. FSRI specimens called Wet are not automatically battery-electrolyte-soaked separators.')
h('Repository boundaries')
p('Atomistic and continuum simulation work belongs elsewhere. This repository manages acquisition, provenance, normalization, validation, coverage and export. It does not automatically publish datasets, change billing, or run simulations. The source package has no mandatory runtime dependencies; specialized features use optional extras.')
h('What completion means')
p('A collection run is operationally complete when its bounded inputs have been attempted, failures are visible, outputs agree, and coverage is reported. A scientific target is complete only when enough distinct, suitable observations exist with the required materials and conditions. Download counts and review counts do not satisfy that target.')

page(3,'Architecture and file ownership','A small orchestration layer connects source-specific adapters to one observation model.')
table(['Module','Responsibility'],[['data_mining/pipeline.py','Ingest, collection, active document manifest, versioned extraction and aggregation'],['data_mining/acquisition.py','HTTPS access, finite downloads, retries, immutable raw storage and cache receipts'],['data_mining/discovery.py','EPO OPS, capped BigQuery discovery and pinned FSRI listings'],['data_mining/patent_html.py','Patent HTML grids, example identity, method linkage and figure/PDF metadata'],['data_mining/pdf_tables.py','PDF table geometry and Celgard normalization'],['data_mining/structured.py','HFM, density and mapped CSV/TSV/XLSX imports'],['data_mining/normalization.py','Property aliases, explicit units, numeric cell and condition parsing'],['data_science/master.py','Versioned records, IDs, validation integration, CSV/Parquet and QC'],['data_mining/pipeline_cli.py','User-facing automatic workflow commands'],['data_mining/errors.py','Expected source errors without hiding programming defects']],[178,290])
p('The adapter registry is intentionally small. Adapters return observation objects plus evidence artifacts. They do not own publication or billing policy. Legacy helpers and CLI commands remain available for compatibility.')
p('The normal path is discovery -> raw bytes and receipt -> adapter evidence -> normalized record -> accepted or pending -> deduplicated export -> coverage assessment. A missing stage should be explicit in the run report.')

page(4,'Read an observation correctly','One row is a property observation with provenance and conditions.')
table(['Field group','Interpretation'],[['sample_id, polymer, product','Identity of the specimen or product. The polymer may remain unresolved even if the source search used a material keyword.'],['property, value, unit','Normalized numeric quantity. Original label/value/unit remain available for audit.'],['source_sha256, source_file, locators','Exact local evidence, source hash and table/page/row/column coordinates.'],['record_type, statistic','Measured / calculated / specification / unknown; reported / typical / minimum / maximum / mean.'],['temperature_C, temperature_role','Known temperature plus measurement or exposure role; unknown is explicit.'],['direction, duration_min, method','MD/TD or other direction, conditioning duration and linked test protocol.'],['review_status, quality_flag','Whether the record is accepted or requires review, with the reason.']],[170,298])
p('Example: 2.5% shrinkage after 105 C for eight hours is an exposure-conditioned measurement. That exposure does not apply to a neighboring porosity or puncture row unless the source explicitly says so. MD and TD measurements are distinct observations. Repeated temperature cycles and replicates retain their identities.')
p('Accepted means that the implemented rules accept the numeric evidence. It does not guarantee complete material identity, an independent experiment, redistribution rights, or suitability for a particular model. Filter those dimensions explicitly.')

page(5,'Temperature, units and uniqueness','Three common ways to overstate a material dataset.')
h('Temperature is not inherited from manufacturing')
p('Extrusion, stretching, annealing and heat-setting temperatures are process conditions. Measurement temperature and exposure temperature are different roles. A range such as 100-150 C cannot become one measurement at 150 C. Multiple test conditions require an explicit mapping to values; otherwise the record is pending review. Heating rates such as 10 K/min are not absolute temperatures.')
h('Units require explicit meaning')
p('The parser converts only recognized units. Explicit kgf/cm2 can become MPa; a printed kg/cm2 remains ambiguous. A force normalized to 20 um specimen thickness is not a raw puncture load and remains unresolved in the current schema. Original values and conversion metadata stay with the record. Unit conversions must not erase test normalization or specimen geometry.')
h('Unique rows are not independent experiments')
p('Observation IDs fingerprint source content, sample identity, property and conditions. Exact duplicate IDs are collapsed. Verified patent-family and FSRI evidence groups can link repeated representations. Cross-source independence is harder: two patents may report the same experiment, and a figure may contain many correlated samples. Family linkage and provenance checks remain necessary before modeling.')
p('The collection target uses unique accepted observation IDs. Report separator-only, measured-only and known-temperature counts as separate views. Never count unresolved rows, interpolated temperature points or dense pixel traces as independent measurements merely to reach 1,000.')

page(6,'What each source can do','Automation is source- and layout-specific.')
table(['Source / view','Automatic path','Remaining boundary'],[['Celgard PDF','Discover product data; preserve PDFs; parse recognized tables and paired specifications.','Nonstandard layouts, product ambiguity and kg/cm2 tensile units can require review.'],['FSRI HFM / density','Pinned file listing; UTF-16 instrument decoding; explicit SI results and density CSVs.','Bulk references. Other apparatus are outside the implemented normalizer.'],['Patent HTML','Example grids, units, unique protocols, numbered heading/body methods, description-line and description-paragraph views.','Split/irregular headers, conflicting methods, material identity and some property semantics remain unresolved.'],['Patent PDF','Preserve fallback document and table geometry.','Arbitrary experimental semantics are not automatically normalized.'],['EPO / BigQuery','Discover candidate patent documents. BigQuery estimates and cumulative spending cap.','EPO needs credentials; discovery is not extraction. No silent paid fallback.'],['PoLyInfo','Authorized local structured imports with explicit restrictions.','No automatic authenticated scraping or implied reuse permission.'],['Graphs','Reproducible tracing after saved calibration and curve isolation.','New images need calibration; points stay outside the master by default.']],[85,188,195])
p('CSV/TSV/XLSX imports support canonical columns or an explicit column mapping and selected worksheet. A malformed row is retained as review evidence while valid neighbors continue. This is structured ingestion, not a general workbook interpreter.')

page(7,'Run and inspect the system','Start with a small bounded batch, then check coverage.')
code('uv sync --locked --extra ingest --extra graph --extra pdf --group dev\nuv run python scripts/run_pipeline_demo.py')
p('The offline demonstration exercises primary-source fixtures, aggregation repeatability and a calibrated graph. It is the fastest check of a fresh installation. Add --extra patents only when the BigQuery client is needed.')
code('uv run python -m che126_data_science collect \\\n  --sources celgard fsri patents \\\n  --materials polyethylene polypropylene \\\n  --max-documents 50 --patent-limit 25 --data-dir data')
p('EPO uses EPO_OPS_KEY and EPO_OPS_SECRET from the environment. Keep credentials out of source files and logs. On this Mac, public HTTPS calls may require SSL_CERT_FILE=/etc/ssl/cert.pem. A source failure is recorded while unaffected sources continue.')
code('uv run python -m che126_data_science aggregate --data-dir data\nuv run python -m che126_data_science aggregate \\\n  --data-dir data --out-dir data/processed/measured --measured-only')
p('Repeated collection skips processed source/context/version combinations. Use --refresh to revisit them intentionally. Unchanged sources use cached bytes. A parser-version change triggers local re-extraction during aggregation; it does not require a fresh download.')
p('Inspect master_observations.csv, review_queue.csv, qc_summary.json and source_manifest.json under data/processed. CSV and Parquet are matching views. A measured-only export still needs separate bulk-reference, material, temperature and experiment filters.')

page(8,'Review findings 1-3','Scientific attribution, row isolation and collection progress.')
h('1 / Ambiguous temperatures became accepted scalars')
p('Before: conditions selected the first matching temperature token, turning a reported range into a single endpoint. After: ranges and multiple distinct temperatures receive an ambiguity flag; no scalar temperature is invented. The patent and Celgard adapters propagate the review status. A clearly mapped scalar table condition may still be used with its associated method.')
p('Regression evidence includes hyphen/en-dash ranges, the word to, multiple explicit temperatures, and ambiguity inside a method paragraph. These tests verify the resulting observation status as well as the condition parser.')
h('2 / One malformed row discarded valid neighbors')
p('Before: a bad structured row raised through the adapter, replacing the entire document with one review entry. After: each row is isolated. Valid neighbors remain accepted; the invalid row retains its original fields, row coordinate and error. Malformed archive/XML/document inputs are also operational failures rather than reasons to abandon an input folder.')
h('3 / Bounded runs repeated the same initial files')
p('Before: cached documents consumed the document cap on every run. After: the collector consults persisted extraction version, source URL and context. Processed documents are skipped, allowing later candidates to run. Explicit refresh revisits them. Review documents are not repeatedly reparsed under identical rules; download failures remain retryable.')
p('Regression evidence reopens Pipeline between batches, checks that each candidate is reached, verifies that the remaining count falls, and confirms refresh behavior. This tests persistence rather than only one in-memory loop.')

page(9,'Review findings 4-6','Table structure, protocol coverage and operational resilience.')
h('4 / Qualified cells disappeared')
p('Before: the first bare numeric cell defined the value columns. A leading bound such as <=20 could disappear and shift example identities. After: table structure and example headers determine the boundary. Bounds retain their minimum/maximum semantics; unresolved ranges remain review evidence. Separate unit columns and explicit example-per-row layouts are supported, with original cell coordinates retained.')
h('5 / Most properties lacked protocol association')
p('Before: useful method matching was largely restricted to shrinkage and micrometer thickness. After: explicit unique property protocols can be linked more broadly. The collection follow-up also recognizes numbered property headings with adjacent test descriptions and both description-line and description-paragraph HTML views. Ex 1 headers and explicit terminal units are recognized.')
p('The rules remain conservative: multiple conflicting protocols stay pending. No specimen polymer is assigned solely from document title or search keywords. A thickness-normalized puncture value is not converted into an ordinary force. These boundaries are tested.')
h('6 / Some source exceptions aborted the batch')
p('Before: common SDK exceptions fell outside the collection exception tuple. After: a small source-failure classifier recognizes operational HTTP/SDK, XML, archive and document errors at the boundary. Other sources and folder inputs continue. Unexpected programming errors such as AttributeError still propagate so defects are not silently disguised as bad source files.')
p('The full regression suite currently has 102 passing tests. Live external authentication is a separate check: offline tests do not prove that a credential, quota or external website is currently available.')

page(10,'Evidence and acceptance gates','What was proved, and what still needs verification.')
table(['Gate','Evidence and practical limit'],[['Unit and regression tests','102 passing cases across existing and new contracts. Coverage includes the reproduced failures; arbitrary unseen patents are not certified.'],['Real source fixtures','Celgard layouts, patent tables, FSRI snapshots and graph image. Source bytes and extraction artifacts remain local.'],['Deterministic exports','Repeated aggregation is checked for byte-identical CSV/Parquet in the demonstration. This is reproducibility of extraction, not scientific independence.'],['Static checks and build','Ruff, whitespace checks and offline source/wheel build are required for code changes.'],['Data checks','Unique observation IDs, finite accepted values, provenance, consistent temperature roles and matching CSV/Parquet row counts.'],['Live collection','Public Celgard, FSRI and patent-reference runs. EPO live authentication is not established without credentials.']],[137,331])
h('How to read review status')
p('Pending entries may contain valuable evidence; they are excluded because one or more required interpretations are unresolved. Read the quality_flag and source artifacts before changing anything. Never change pending to accepted as a counting exercise. Fix a reusable rule with a test, or supply a documented interpretation with exact source evidence.')
h('Version changes')
p('EXTRACTION_VERSION is separator-v5 for the current parser improvements. Version-keyed artifacts keep prior outputs available. Aggregate rebuilds stale artifacts locally. Changing code without advancing the extraction version can leave old cached results active and conceal a fix.')

page(11,'Efficiency and code size','Prefer focused consolidation over a framework rewrite.')
h('Implemented improvements')
p('Candidate round-robin uses deque rather than repeated list pop(0). Ordinary aggregation reuses the artifact it has already loaded instead of reading it twice. Legacy receipt discovery is indexed lazily once per DocumentStore. Completed inputs no longer consume every bounded batch. These changes address repeated work without adding a service or database.')
h('Deliberate compatibility decisions')
p('Legacy source acquisition helpers and CLI contracts still coexist with the newer pipeline. They should eventually use shared internals behind compatibility wrappers. Deleting them immediately risks breaking existing commands and tests. The master currently reuses legacy numeric validation by constructing an Observation; a later validation change should extract shared functions rather than maintain two scientific rule sets.')
h('Deferred optimizations')
p('Whole-master CSV/Parquet export is reasonable for the present dataset. A database or distributed scheduler is not justified by a few thousand rows. Graph tracing allocates arrays for the complete image; cropping first would reduce memory for large images. This is lower priority than extraction correctness and has not been changed in this collection task.')
h('Where effort pays off')
p('The largest collection bottleneck is semantic extraction coverage, especially irregular example headers, test-method association, unit context and specimen identity. More downloads alone can grow the review queue much faster than the accepted dataset. Add held-out real layouts and measure accepted yield, unresolved reasons and provenance quality after each parser change.')

page(12,'Current collection and the 1,000-point target','Counts are a snapshot of local exports at handbook generation time.')
summary=json.loads((ROOT/'data/processed/qc_summary.json').read_text())
runpath=ROOT/'data_mining/runs/2026-10-16_1000_target/summary.json'
run=json.loads(runpath.read_text()) if runpath.exists() else {}
table(['View','Observation rows'],[['All accepted',summary['accepted']],['Pending review',summary['review']],['Measured records, including bulk references',summary['by_record_type'].get('measured',0)],['Separator/component rows',run.get('separator_or_component_rows','See coverage export')],['Measured separator rows',run.get('measured_separator_rows','See coverage export')],['Measured separator rows with explicit temperature',run.get('temperature_resolved_measured_separator_rows','See coverage export')],['Bulk reference rows',run.get('bulk_reference_rows','See coverage export')]],[338,130])
p('The 1,000-point operational target concerns unique accepted observation IDs. It does not imply 1,000 independent experiments, complete material identity, complete temperatures or every property at every temperature. The coverage matrix and strict measured-separator views must accompany the headline number.')
p('Do not interpolate or digitize extra points simply to satisfy the count. Manufacturer specifications and bulk references remain useful evidence categories, but should be filtered for separator-specific modeling. Unknown polymer and electrolyte state are material limitations, not blanks to fill from assumptions.')
p('The run artifacts and coverage matrix live under data_mining/runs/2026-10-16_1000_target. Raw public patent documents and saved reference candidates are under data/runs/2026-10-16_patents. Read the run README for exact acquisition scope, current totals and remaining gaps.')

page(13,'Contribute without weakening the data','A repeatable workflow for fixes and new source layouts.')
h('1 / Locate the responsible layer')
p('A discovery failure belongs in the discovery/client boundary. Wrong example identity belongs in table interpretation. Unit ambiguity belongs in normalization or source context. Export schema and shared validation belong in master/observations. Avoid fixing a source-specific symptom by weakening validation globally.')
h('2 / Preserve the evidence')
p('Keep immutable raw bytes, a source URL/hash and exact locators. Add a minimal public-source fixture or a synthetic reproduction with the same structural behavior. Record source restrictions; possession of a PDF is not permission to redistribute it.')
h('3 / Implement a reusable rule')
p('Prefer a layout or protocol rule over a patent-number branch. Keep ambiguous cases pending. Check bounds, paired statistics, MD/TD, repeated cycles, multiple temperatures, normalized thickness and component-versus-total construction. Use one-time metadata only where the source actually supports it.')
h('4 / Verify and stop')
code('.venv/bin/python -m pytest -q\n.venv/bin/ruff check src tests\ngit diff --check\nuv build --offline --no-build-isolation')
p('Use a writable UV_CACHE_DIR when the environment restricts the default cache. Run the offline demonstration after changes that affect adapters or export. Compare counts and review reasons, but inspect scientific meaning when accepted counts increase. Advance the extraction version and update the review/collection guide. Preserve unrelated uncommitted work.')

page(14,'Troubleshooting and reading map','A newcomer can use this page as an operating checklist.')
table(['Symptom','First check'],[['No new files on collect','Were source/context/version combinations already processed? Inspect remaining_candidates and discovery status before using refresh.'],['EPO cannot discover','Check presence of the two environment variables without printing values. Missing credentials do not imply source extraction is broken.'],['Many patent rows pending','Group quality_flag counts. Inspect example headers, explicit units, local protocol and source layout. Keep uncertainty visible.'],['CSV import loses a row','Inspect that row in review_queue and its raw JSON fields; verify canonical columns/mapping and temperature role.'],['Known source changed','Refresh deliberately, preserve new hash, and compare versions. Do not overwrite immutable raw bytes.'],['Need wet/dry data','Filter explicit electrolyte_state. Manufacturing wet process and FSRI Wet are not electrolyte soaking.'],['Need 1,000 independent samples','Use experiment/family/replicate provenance; observation-row count alone is insufficient.']],[147,321])
h('Read these repository documents next')
p('README.md: project entry point. docs/COLLECTION_GUIDE.md: commands, caching, source boundaries and permissions. docs/AUTOMATION_REVIEW.md: original six findings and their implementation follow-up. docs/SOURCE_AUDIT.md: primary-source evidence and early fixtures. docs/CODE_REVIEW.md: review history. tests/test_automation_regressions.py: executable failure cases. The parent AGENT_HANDOFF.md records session state and historical constraints.')
p('This handbook is a dated explanation of the checked-out code and local run artifacts. External services, credentials, source layouts and dataset contents can change. Re-run the relevant checks before making a new claim about access, collection completeness or model readiness.')

def footer(canvas,doc):
 canvas.setStrokeColor(colors.HexColor('#CCD8DD'));canvas.line(54,43,558,43)
 canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#526878'))
 canvas.drawString(54,30,'ChE126 | Code review and operating handbook | 2026-10-16')
 canvas.drawRightString(558,30,str(doc.page))
OUT.parent.mkdir(parents=True,exist_ok=True)
SimpleDocTemplate(str(OUT),pagesize=(612,792),leftMargin=72,rightMargin=72,topMargin=48,bottomMargin=60,title='ChE126 code review and operating handbook',author='ChE126 project').build(story,onFirstPage=footer,onLaterPages=footer)
print(OUT)
