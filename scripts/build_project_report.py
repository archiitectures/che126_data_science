"""Build a current newcomer report and optional PDF from the assembled exports."""
import argparse
import json
import re
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]


def markdown():
    summary = json.loads((ROOT / 'datasets/unique_points_summary.json').read_text())
    coverage = json.loads((ROOT / 'datasets/coverage_audit.json').read_text())
    audit = json.loads((ROOT / 'datasets/quality_review.json').read_text())
    revisions = json.loads((ROOT / 'data_mining/reviewed_observation_revisions.json').read_text())
    corrected = sum(bool(r.get('changes')) for r in revisions.values())
    held = len(revisions) - corrected
    counts = {k: summary[k] for k in ['accepted_master_rows', 'unique_value_context_points', 'separator_or_component_points', 'bulk_reference_points', 'measured_separator_points', 'temperature_resolved_measured_separator_points']}
    property_table = '\n'.join(f'| {k} | {v:,} |' for k,v in sorted(summary['by_property'].items(), key=lambda x:-x[1]))
    adapter_table = '\n'.join(f'| {k} | {v:,} |' for k,v in summary['by_source'].items())
    return f'''# ChE126 separator project: codebase, pipeline and dataset

Prepared {date.today().isoformat()} from the assembled local exports. This report is a
newcomer guide and a record of the five-priority improvement pass. The dataset CSV
SHA256 is `{coverage['input_sha256']}`. Earlier dated reports and handbooks are
historical snapshots; the exported tables and this report provide current totals.

## 1. What the project does

The project collects source-reported properties of battery separator materials,
normalizes units, records test conditions and material scope, and preserves evidence
for every accepted value. Patents, manufacturer datasheets, public materials
instrument files and research papers contribute different kinds of evidence.
Bulk polymer references support physical comparisons; they do not establish
performance of a porous separator. Molecular dynamics outputs remain in separate
comparison artifacts and are not relabelled as experimental observations.

The main dataset is tidy: one property observation per row. Properties such as
porosity or crystallinity are values in the `property` column, rather than separate
wide columns. `value` and `unit` describe the property. Conditions, specimen scope,
source locations and quality status accompany that value.

## 2. Current dataset and what the counts mean

| Measure | Count |
|---|---:|
| Accepted source observations | {counts['accepted_master_rows']:,} |
| Distinct normalized value/context points | {counts['unique_value_context_points']:,} |
| Represented properties | {coverage['properties']} |
| Separator/component points | {counts['separator_or_component_points']:,} |
| Bulk-reference points | {counts['bulk_reference_points']:,} |
| Points with numeric test/exposure temperature | {coverage['numeric_temperature_points']:,} |
| Points without numeric temperature | {coverage['missing_temperature_points']:,} |
| Measured separator/component points | {counts['measured_separator_points']:,} |
| Measured separator/component points with temperature | {counts['temperature_resolved_measured_separator_points']:,} |

An observation is supporting source evidence. A unique point groups equal
normalized scientific values and recorded contexts; it is not necessarily one
independent experiment. A document, patent publication, patent family, curve,
replicate and temperature setpoint are also different counting units. Native
thermal-curve samples share curve IDs and must not be treated as thousands of
independent experiments in statistical validation or train/test splitting.

This pass began with 10,654 contexts and 13,371 observations. It added 25 MD-reference
contexts and 40 actual separator temperature observations. It also corrected
{corrected} observation definitions and held {held} ambiguous source observations in
review. Old raw cells were not deleted. Changes in the total and temperature counts
therefore include withdrawals, corrected definitions and deduplication, rather than
just newly found numbers. In particular, temperature attached to a misclassified
elongation value was not retained as a shrinkage test condition.

## 3. Where to find the data

| File or folder | Purpose |
|---|---|
| datasets/unique_points.csv and .parquet | Main distinct value/context analysis table |
| datasets/master_observations.csv and .parquet | All accepted evidence observations |
| datasets/unique_point_evidence.json | Supporting observation IDs for every unique point |
| datasets/temperature_resolved_points.csv and .parquet | Subset with numeric measurement/exposure conditions |
| datasets/temperature_gap_audit.csv | Current per-point missing-temperature actions |
| datasets/separator_type_property_coverage.csv | Material/property counts and temperature coverage |
| datasets/material_identity.csv | Current material-attribution evidence per representative point |
| datasets/quality_review.json | Current structural, unit, source-hash and cell-check results |
| datasets/assembly_manifest.json | Artifact hashes from the unified assembly |
| data/processed/review_queue.csv | Ambiguous, unsupported or withdrawn evidence |
| data/processed/source_manifest.json | Explicit selected source/artifact corpus and curation-file pointer |
| visualizations/ | Plot code, figures, source count tables and input hash |

The datasets and processed CSV/Parquet views are synchronized. Keep the evidence
links when working with the smaller distinct table. Missing values mean unknown
or unreported, never zero. The legacy dry/wet wide tables are a different format
and are not the complete current dataset.

## 4. Source coverage and processing routes

| Adapter route | Distinct contexts |
|---|---:|
{adapter_table}

These are processing routes, not original-document categories. The reviewed
manual route includes primary PDF cells, paper XML, supplemental tables and
calibrated figure estimates, including facts originally reported in patents.
A manual import is therefore not necessarily a new independent research source.

Patents usually provide more specimen variants, recipes and mechanical/geometry
properties. Celgard datasheets give commercial product specifications. FSRI HFM
and STA files provide bulk-reference thermal measurements and curves. Papers add
methods, figures and electrolyte-dependent behavior. PoLyInfo is an authorized
structured-import path, not an unrestricted crawler. EPO and budgeted BigQuery
interfaces exist; neither is required for rebuilding the present local exports.
This pass used public sources and cached documents without paid cloud queries.

## 5. Codebase map

| Area | Files and responsibility |
|---|---|
| Public CLI | src/che126_data_science/__main__.py and data_mining/pipeline_cli.py |
| Discovery | data_mining/discovery.py, sources.py and patents.py |
| Raw preservation | data_mining/acquisition.py: bounded HTTPS, cache receipts and content hashes |
| Orchestration | data_mining/pipeline.py: adapter registry, manifests, reviews and aggregation |
| Patent extraction | data_mining/patent_html.py, normalization.py, material_identity.py |
| PDFs/datasheets | data_mining/pdf_tables.py and celgard.py |
| FSRI | data_mining/structured.py, fsri.py and fsri_sta.py |
| Reviewed corrections | data_mining/curation.py and reviewed_conditions.py |
| Typed records/units | data_science/master.py and observations.py |
| Current reporting | data_science/reporting.py |
| Complete assembly | scripts/assemble_dataset.py |
| Metadata/export helpers | scripts/export_unique_points.py, annotate_polymer_subtypes.py, export_temperature_views.py |
| Calibrated curve tool | data_mining/digitize.py |
| Figures | visualizations/generate_figures.py |
| Current report builder | scripts/build_project_report.py |
| Regression proof | tests/; dated runs retain source-specific checks and receipts |

Paths in the table after the package prefix are relative to
src/che126_data_science/. The reusable library owns parsing, validation and
aggregation. Dated run scripts own evidence-specific acquisition, calibration and
review decisions. The core has no mandatory dependencies; ingestion, graphs/PDFs,
and BigQuery use optional extras. Matplotlib now belongs to the graph extra, so
the documented assembly environment includes its figure dependency.

## 6. Data flow and reproducible assembly

Discovery -> immutable raw bytes -> adapter extraction -> reviewed corrections ->
accepted/review records -> distinct-context grouping -> metadata annotation ->
temperature subsets -> coverage and evidence audits -> figures -> publication.

Use the project environment, with the selected local source archive present:

```sh
uv sync --locked --extra ingest --extra graph --group dev
.venv/bin/python scripts/assemble_dataset.py --check-replay
```

The assembly command uses data/processed/source_manifest.json as the explicit
corpus selection. It is offline and does not start discovery, cloud queries or
billing. It aggregates cached artifacts, exports master/unique tables, validates
primary evidence used for morphology annotation, writes temperature subsets,
refreshes coverage/gap/identity tables, runs the dataset audit and regenerates all
six figures. `--skip-figures` omits only plotting. `--check-replay` runs assembly
twice and requires matching artifact hashes. SVG dates and generated element IDs
are fixed so unchanged figures can be checked byte-for-byte.

A fresh clone contains code and small review mappings, not every raw research
archive file. The Hub provides ready-to-use exports. A full offline rebuild also
requires the manifest's raw and interim files; missing evidence fails visibly.
Backups for this pass are in the dated priorities run's before/ folder. Restoring
that snapshot plus its original manifest/curation pointer rolls back the view;
never overwrite or delete raw originals to perform a correction.

## 7. IDs, deduplication and source lineage

Observation IDs identify an extraction with source hash, sample, property and
conditions. Unique-point IDs fingerprint normalized scientific context fields.
Those fields include property, value, unit, material/product, specimen scope,
temperature role, direction, method, electrolyte, replicate/curve identity and
uncertainty. Different reported protocols remain different contexts.

The distinct exporter intentionally groups equal contexts, even across different
source observations or samples. Equal numbers alone do not prove that experiments
are duplicates; conversely, changing a source URL does not make a repeated patent
family result independent. Five cross-publication exact-context groups were found
in this review and are listed in cross_publication_context_audit.csv. Comprehensive
patent-family experiment identity remains uncertified.

Correction IDs retain their parent ID in notes. A source-bound curation ledger
changes the assembled interpretation without editing the raw cell: the old record
is preserved in review and a corrected record receives a new ID. Source hash and
table coordinates must match. The ledger can change explicit interpretation fields
but cannot rewrite the original numeric cell or source provenance.

## 8. Material identity, morphology and temperature

Polymer family, commercial grade, layer architecture, coating and morphology are
separate attributes. HDPE is a grade description; it does not by itself establish
a finished membrane's crystalline fraction. A PP-supported PEO/ionic-liquid
composite is not pure PP. A coating packing density is not PE matrix density.

The annotation step adds subtype, scoped morphology, status, evidence, candidate
mentions and polymer_crystallinity_measurements. The last field is a JSON list so
DSC and X-ray estimates can coexist. Reviewed assignments are keyed to exact source
samples and checked against primary-source hashes. Prepared membrane morphology
is not automatically its morphology during an elevated-temperature test. Feedstock
or binder morphology does not classify the entire separator.

All 29 numeric-crystallinity proximity candidates from the earlier scan have a
review category in morphology_source_review.csv. Seven publications were confirmed
to report numerical membrane or PE-layer crystalline fractions; other hits concern
feedstock, binders, optional definitions, prior art or unrelated nearby percentages.
Some publications are related and do not add independent experiments.

Temperature during measurement, thermal exposure, processing, prior conditioning
and soaking are different concepts. Only supported measurement/exposure conditions
enter temperature_C. Room temperature without a numeric source value is not
assigned 25 C. A standard reference is not permission to invent a temperature.
A melting-temperature value is a response, not an automatic test condition for
other properties. Missing-temperature actions inspect linked methods; they do not
prove the entire original document lacks that information.

## 9. Scientific corrections in this pass

A parser error allowed direction-only value rows to inherit the next property
heading. It changed some elongation percentages into apparent thermal shrinkage,
including values above 100%. The parser now associates these rows with their
preceding heading while retaining legitimate split temperature/shrinkage headers.
A source-cell replay corrected 92 observations from shrinkage to elongation.
Invalid inherited shrinkage temperatures were removed.

Thirteen records explicitly labelled packing density were separated into
packing_density and scoped to porous coating components. Their inherited PE
substrate label was not used as the coating composition. Ambiguous pore-size
units/headers and zero coating thickness treated as whole-separator thickness
were moved to review. Four previously hidden aliases were also withdrawn when
related evidence changed; otherwise they could have reappeared in the accepted
view. In total {corrected} observations have corrected definitions and {held} are held.

Future ingestion routes positive shrinkage above 100% and zero separator
thickness to review. Dataset auditing checks those conditions as well as schema,
units, source files, CSV/Parquet parity, context membership and stored cell values.
Source-cell equality verifies transcription, not complete scientific interpretation.
The ledger makes the reviewed legacy corrections reproducible; changing extraction
logic for other cached sources may still require deliberate refresh/version
migration rather than assuming every cached artifact has been re-extracted.

## 10. New MD benchmarks and what they establish

Twenty-five explicit-temperature bulk-reference contexts were imported from three
primary sources. They remain separate from separator performance measurements.

| Source | Contribution | Interpretation |
|---|---|---|
| PGSE NMR, PMC7762995 | PE chain Dc = 7.0e-13 m2/s at 426 K, standard error 8.0e-14 | Experimental model fit; SRM1482 Mn 11.4 and Mw 13.6 kg/mol |
| NIST 1974, Table 3 | 22 Cp values for extrapolated amorphous/crystalline PE at 273.15-360 K | Calculated phase estimates based on calorimetry, not pure-phase direct measurements |
| Wei 2009 thesis | HDPE/N2 tension 25.5 mN/m at 125 C, 500 psi; 20.5 at 190 C, 1500 psi | Primary reported endpoints; high-pressure gas interface, not vacuum |

The NIST source uses a base mole of CH2 with mass 14.027 g/mol. Its molar Cp is
converted using that explicit repeat-unit mass, not the molecular weight of an
entire simulated chain. At 25 C the amorphous estimate is 2.393 J/(g K), versus
the submitted CG window-fit values near 0.82-0.84. The deficit remains expected
for a coarse-grained model with missing degrees of freedom and is not repaired
by relabelling a crystalline benchmark as amorphous.

The new diffusion point is at 152.85 C and has a different molecular-weight
comparison from the short-chain simulation. The submitted long-chain case did
not reach a Fickian diffusion regime, so no matched diffusion error is asserted.
The tension endpoints differ from the simulation in gas environment, pressure
and/or temperature. Thesis PVT/compressibility candidates remain held after
access/certificate failures; no insecure download or invented numerical benchmark
was used. Free original university and national-lab sources were tried.

The earlier closest expansion comparison remains about 1.85-1.87% derived MD
linear expansion to 105 C versus selected PE substrate oven-test values of 2.0%.
This is agreement of scale under different protocols. Prepared membrane
crystallinity of 59-87% is still substantially different from nominally amorphous
MD. The simulation has not been validated as a complete commercial separator.

## 11. New separator temperature coverage and figure tools

The pass added 40 observations from PMC10680142, a primary RSC study of PP supports
filled with PEO, LiTFSI and ionic liquid. Seven formulations have conductivity at
25, 40, 50, 60 and 70 C. Seven 25 C values came directly from the prose; the other
28 are calibrated original-marker estimates. One tensile value at 25 C is directly
reported; four representative curve peaks at 40-70 C are digitized estimates.
They are not relabelled as five-specimen average tensile strengths.

The built-in digitizer was used for all 32 estimated marker/peak regions. Each
calibration records image hash, native crop, two axis references, series mask,
color selection, units and pixel uncertainty. All 32 regions passed its isolation
checks. Only native marker values or one maximum per physical curve were imported;
intermediate pixel samples are not independent data. Calibrations, source receipts,
coordinate profiles, uncertainty and QC remain in the dated run.

A PP/PET figure with a temperature-axis/prose discrepancy and an ORNL report
without the required temperature-resolved mechanical table were retained as
candidates, not used to manufacture new measurements. The digitizer is automatic
after an approved calibration. It does not infer axes, select a material or solve
arbitrary OCR/layout ambiguity without review. This is a deliberate accuracy
boundary and an important limit on fully unattended mining.

## 12. Property coverage

| Property | Distinct contexts |
|---|---:|
{property_table}

The table counts accepted reported contexts, including measured, calculated,
digitized, uncertain-status and specification records. Filter record_type,
sample_form and temperature_role for the intended analysis. Most temperature
coverage remains in shrinkage and bulk thermal curves. There is still no complete
property-by-material-by-temperature characterization matrix.

## 13. Validation, publication and safe reuse

The final gate runs the full test suite, focused lint, source/evidence checks and
byte-identical assembly replay. The structured audit currently has
{len(audit['failed_checks'])} failed checks. Check the dated final logs for the exact
completed test count and replay result; this report does not substitute for those
machine-readable artifacts. Raw-cell corrections remain reversible through the
review queue and the initial before/ snapshot.

Hugging Face is the home of the dataset exports, reports and evidence links:
https://huggingface.co/datasets/archiitecture/che126

GitHub is the home of the matching workflows, small reviewed mappings, tests,
figures and documentation:
https://github.com/archiitectures/che126_data_science

Publication uses an explicit file list. Source caches, credential files and
unrelated local runs are not staged with the code. Tokens are read from existing
credential storage and are not written into reports. Uploaded key exports are
downloaded from the returned Hub revision and compared byte-for-byte; the GitHub
branch head is checked after push. Final receipt hashes are recorded in the dated
run. Public hosting does not grant a dataset-wide license over third-party source
material; source-specific restrictions remain in provenance.

## 14. How to extend the project without making it bloated

Use the existing discovery, DocumentStore and adapter registry for a new source.
Define a property's units and meaning before parsing it. Put ambiguous or
unsupported rows in review. Keep sample identity and exact method conditions
attached to the value. For a figure, retain the original image and calibration,
import original markers or a declared sampling scheme, and carry uncertainty.
Run assembly/audit and compare source evidence before publication.

Implement a generic parsing rule only after proving the layout and unit contract.
Keep genuinely source-specific evidence in small reviewed mappings or dated import
files. Do not duplicate acquisition/normalization code in each run. The curation
ledger and morphology mapping are part of the selected corpus and should be
versioned with the workflow. Raw archives remain external to routine code pushes.

The main remaining technical improvements are comprehensive patent-family linkage,
broader sample/header attribution audits, an explicit pressure metadata field with
an ID-safe schema migration, and automated calibration discovery with human review
for uncertain figures. The main data goals are phase-matched PE PVT/density and
compressibility, equivalent surface environments and molecular weights for MD,
and more actual separator mechanics/transport across temperature.

## 15. Primary references and detailed artifacts

- Diffusion: https://pmc.ncbi.nlm.nih.gov/articles/PMC7762995/
- Phase Cp: https://doi.org/10.6028/jres.078A.022
- Surface tension thesis: the university-source receipt is in benchmark_acquisition.json.
- Separator temperature study: https://doi.org/10.1039/D3RA05899A
- Expansion: https://patents.google.com/patent/US10326120B2/en
- Compression: https://patents.google.com/patent/US20240253287A1/en

The dated work record is data_mining/runs/2026-10-30_priorities/. Its acquisition,
review, import, calibration, test, replay and publication records explain what
was attempted, accepted and held. The earlier source probe report and MD comparison
remain useful historical context. New users should begin with this guide, then
README.md, the current datasets README and the unified assembly command.
'''


def pdf(text, path):
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Body',fontName='Helvetica',fontSize=9.5,leading=13.5,spaceAfter=8,splitLongWords=True))
    styles.add(ParagraphStyle(name='CellSmall',fontName='Helvetica',fontSize=8,leading=10.5,splitLongWords=True))
    styles.add(ParagraphStyle(name='CodeSmall',fontName='Courier',fontSize=8,leading=11,spaceAfter=8,splitLongWords=True))
    styles['Title'].textColor=colors.HexColor('#17344f')
    styles['Heading1'].textColor=colors.HexColor('#17344f')
    def rich(s):
        s=escape(s)
        s=re.sub(r'`([^`]+)`',r'<font name="Courier">\1</font>',s)
        return s
    story=[];lines=text.splitlines();i=0;paragraph=[];in_code=False
    def flush():
        if paragraph:
            story.append(Paragraph(rich(' '.join(paragraph)),styles['Body']));paragraph.clear()
    while i<len(lines):
        line=lines[i]
        if line.startswith('```'):
            flush();in_code=not in_code;i+=1;continue
        if in_code:
            story.append(Paragraph(escape(line),styles['CodeSmall']));i+=1;continue
        if line.startswith('|'):
            flush();table=[]
            while i<len(lines) and lines[i].startswith('|'):
                cells=[s.strip() for s in lines[i].strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?',s) for s in cells):table.append([Paragraph(rich(s),styles['CellSmall']) for s in cells])
                i+=1
            n=len(table[0]);widths=([360,108] if n==2 else [150,155,163])
            t=Table(table,colWidths=widths,repeatRows=1,hAlign='LEFT')
            t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e9eff4')),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#ccd5dd')),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
            story.extend([t,Spacer(1,12)]);continue
        if line.startswith('# '):
            flush();story.extend([Paragraph(rich(line[2:]),styles['Title']),Spacer(1,15)])
        elif line.startswith('## '):
            flush();story.extend([Spacer(1,12),Paragraph(rich(line[3:]),styles['Heading1'])])
        elif not line.strip():flush()
        else:paragraph.append(line)
        i+=1
    flush()
    def footer(canvas,doc):
        canvas.saveState();canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#526579'));canvas.drawString(48,30,'ChE126 | Current project guide | '+date.today().isoformat());canvas.drawRightString(564,30,str(doc.page));canvas.restoreState()
    SimpleDocTemplate(str(path),pagesize=(612,792),leftMargin=48,rightMargin=48,topMargin=45,bottomMargin=48,title='ChE126 separator project guide',author='ChE126 project').build(story,onFirstPage=footer,onLaterPages=footer)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--pdf',action='store_true');args=parser.parse_args()
    text=markdown()
    for path in [ROOT/'docs/COMPREHENSIVE_PROJECT_REPORT.md',ROOT/'datasets/project_report.md']:path.write_text(text)
    if args.pdf:pdf(text,ROOT/'datasets/project_report.pdf')
    print('Project report generated'+(' (Markdown and PDF)' if args.pdf else ' (Markdown)'))
