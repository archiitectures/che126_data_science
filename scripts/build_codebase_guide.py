"""Build the newcomer guide: uv run --no-project --with reportlab python scripts/build_codebase_guide.py."""

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Flowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/pdf/codebase_guide.pdf"
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="Deck", fontName="Helvetica", fontSize=14, leading=20, textColor=colors.HexColor("#40566A"), spaceAfter=18))
styles.add(ParagraphStyle(name="Copy", fontName="Helvetica", fontSize=10.5, leading=15, spaceAfter=10))
styles.add(ParagraphStyle(name="CodeBlock", fontName="Courier", fontSize=8, leading=12, backColor=colors.HexColor("#EFF4F7"), borderPadding=9, spaceBefore=5, spaceAfter=14))
styles.add(ParagraphStyle(name="Cell", fontName="Helvetica", fontSize=9, leading=13, spaceAfter=0))
styles["Title"].alignment = TA_LEFT
styles["Title"].fontSize = 30
styles["Title"].leading = 35
styles["Title"].textColor = colors.HexColor("#16334A")
styles["Heading1"].textColor = colors.HexColor("#16334A")
styles["Heading2"].textColor = colors.HexColor("#107F83")
story = []


def p(text, style="Copy"):
    story.append(Paragraph(text, styles[style]))


def title(number, text, deck):
    if story:
        story.append(PageBreak())
    p(f"CHE126 / FIELD GUIDE / {number:02d}", "Heading2")
    p(text, "Title")
    p(deck, "Deck")


def h(text):
    p(text, "Heading2")


def code(text):
    text = text.replace(r"\n", "\\" + "\n")
    p(escape(text).replace("\n", "<br/>"), "CodeBlock")


def table(headers, rows, widths):
    data = [[Paragraph(escape(str(c)), styles["Cell"]) for c in row] for row in [headers] + rows]
    t = Table(data, colWidths=widths, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCECEF")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9E1E6")),
    ]))
    story.extend([t, Spacer(1, 12)])


class Pipeline(Flowable):
    def __init__(self):
        super().__init__()
        self.width, self.height = 468, 68

    def draw(self):
        labels = ["Discover", "Preserve raw", "Extract + review", "Validate", "Check gaps"]
        for i, label in enumerate(labels):
            x = i * 95
            self.canv.setFillColor(colors.HexColor("#16334A"))
            self.canv.roundRect(x, 18, 88, 36, 5, fill=1, stroke=0)
            self.canv.setFillColor(colors.white)
            self.canv.setFont("Helvetica", 8)
            self.canv.drawCentredString(x + 44, 33, label)
            if i < 4:
                self.canv.setStrokeColor(colors.HexColor("#107F83"))
                self.canv.line(x + 88, 36, x + 95, 36)


title(1, "Automatic separator data pipeline", "A newcomer guide to collection, extraction, review and master exports.\nChE126 | Python 3.12+ | CPU | 16 October 2026")
p("<b>Purpose.</b> Build traceable separator-property evidence for PE, PP, PP/PE/PP and coated variants through thermal exposure, pore changes and loss of integrity. Source documents, test conditions and uncertainty remain attached to each value.")
story.append(Pipeline())
h("What works now")
p("A source adapter registry joins public acquisition, immutable caching, HTML/PDF/structured extraction, normalized long-format records and review queues. Repeated runs reuse cached evidence and rebuild deterministic CSV and Parquet exports. The core remains dependency-free; ingestion and graph tools use optional extras.")
h("Start with the verified demonstration")
code("uv sync --locked --extra ingest --extra graph --group dev\nuv run python scripts/run_pipeline_demo.py")
p("The offline demo reads included primary-source fixtures and the pinned FSRI snapshot. It creates <b>95 accepted records and 52 review records</b>, checks byte-identical CSV/Parquet after a repeated run, and traces a selected real patent-curve segment. Outputs: <b>data/demo/processed/</b>.")
p("<b>Counts describe evidence rows.</b> Typical values, specification bounds, replicates and curve pixels are different kinds of evidence. A request for temperatures does not create measurements at those temperatures.")

title(2, "Follow one document", "The pipeline keeps numerical extraction separate from scientific interpretation.")
table(["Step", "Behavior"], [
 ("Discover", "Celgard catalog, pinned FSRI repository tree, EPO patent search; existing BigQuery is an explicit alternative."),
 ("Preserve", "Original bytes, URL, SHA-256, time and restrictions. Known receipts are adopted; unchanged resources reuse cache."),
 ("Extract", "Raw cells, text, geometry, context paragraphs, instrument tables and figure links are saved as artifacts."),
 ("Normalize", "Map explicit property labels and units, split paired statistics, attach sample identity and reported test conditions."),
 ("Validate", "Accepted values meet the schema; uncertain units, context or attribution enter a review queue."),
 ("Aggregate", "Rebuild selected manifests into typed CSV/Parquet; link duplicates and retain provenance aliases."),
], [85,395])
h("Main code seams")
p("<b>data_mining/pipeline.py</b> orchestrates the adapter registry and manifests. <b>acquisition.py</b> owns HTTP and document caching. Source adapters cover PDF tables, patent HTML and structured data. <b>data_science/master.py</b> defines the richer records and exports. Existing observations.py validation and legacy commands remain available.")
h("Local layout")
p("<b>data/raw/</b> holds immutable bytes; <b>data/cache/</b> stores acquisition/discovery metadata; <b>data/interim/</b> holds versioned artifacts. <b>data/processed/</b> contains master exports, review, manifests and QC. Raw/cache/interim files are ignored by Git. Historical datasets and run outputs remain separate.")

title(3, "Run a collection pass", "Bound the acquisition; inspect both accepted records and review outcomes.")
code("uv run python -m che126_data_science collect \\n  --sources fsri celgard patents \\n  --materials polyethylene polypropylene \\n  --max-documents 50 --patent-limit 25\nuv run python -m che126_data_science aggregate --data-dir data")
h("Patent discovery and budgets")
p("EPO OPS is the default discovery provider. Registered credentials are supplied through <b>EPO_OPS_KEY</b> and <b>EPO_OPS_SECRET</b>; they are not stored in exports. Missing credentials are reported while other sources continue. Individual Google patent pages are retrieved through permitted routes; its disallowed search route is not crawled.")
p("BigQuery remains available with <b>--patent-provider bigquery --project PROJECT --budget-usd 2</b>. Queries are estimated before execution. A cumulative byte ledger reserves capped cost; uncertain failures consume their reservation. Verify the configured price before use. Trial credit does not become an automatic spending limit. This implementation made no billing changes or paid queries.")
h("One source or a folder")
code("uv run python -m che126_data_science ingest --source celgard \\n  --input path/to/pdfs\nuv run python -m che126_data_science ingest --source patents \\n  --input https://patents.google.com/patent/US9911958B2/en")
p("Use <b>--context metadata.json</b> for known identity, restrictions and explicit mappings. Unchanged acquisition and search results stay cached. <b>--refresh</b> explicitly revalidates resources. Retries and download sizes are bounded. Parser-version changes cause local re-extraction on aggregate.")

title(4, "Read the master correctly", "One row means one scalar observation, with provenance and conditions.")
table(["Metadata", "Why it matters"], [
 ("Source identity", "URL/file, SHA-256, page/table/row/column, extraction method and version make values verifiable."),
 ("Material and construction", "Polymer, product, architecture, coating and sample form distinguish films, components and bulk references."),
 ("Test conditions", "Temperature role, duration, heating rate, direction, method and electrolyte details determine comparability."),
 ("Record type and statistic", "Measured, calculated, spec-limit, claimed-range, digitized-estimate and unknown stay distinct from typical/min/max/mean."),
 ("Quality and repeats", "Review status, original units, conversion metadata, replicate ID and curve ID prevent silent assumptions and pseudoreplication."),
], [130,350])
h("Three examples")
p("<b>PP1611:</b> all 12 scalar values are extracted. Eight normalize successfully; four tensile values printed as Kg/cm2 remain in review. Shrinkage retains 105 C exposure for 60 minutes. Calculated porosity remains calculated.")
p("<b>Patent US9911958B2:</b> 12 length-shrinkage values at 130/140/170 C retain four example/control identities and the 10-minute exposure protocol. Four thickness values retain their micrometer method. The table's values are not expanded into invented separate MD/TD observations.")
p("<b>FSRI:</b> Wet means ambient/unconditioned in this source, not electrolyte soaked. Bulk references remain labeled. Matching snapshot/raw representations are linked; different specimen replicates remain distinct.")
h("Training view")
code("uv run python -m che126_data_science aggregate \\n  --out-dir data/processed/measured --measured-only")
p("This exports accepted measured records only. Filter sample form separately when selecting separator films. Null temperature stays null; process temperatures are not test temperatures.")

title(5, "Graphs and human review", "Use original numeric data first. Digitize only a calibrated, isolated series.")
code("uv run python -m che126_data_science figures --data-dir data\nuv run python -m che126_data_science digitize \\n  --input tests/fixtures/pipeline/patent_tma.png \\n  --calibration tests/fixtures/pipeline/tma_calibration.json \\n  --out-dir data/processed/digitization")
p("The figure workflow preserves image sheets and description captions. A sheet may contain multiple numbered figures. The saved calibration supplies the actual figure, crop, axis reference points and units, curve color/isolation mask, image hash, reference points and tolerances.")
h("Verified proof of concept")
p("The demonstration uses a manually isolated Comparative Example 1 segment from Figure 5 of US20120077113A1. It traces <b>38 pixel samples sharing one curve ID</b>. Relative length is kept in its plotted units; it is not silently relabeled shrinkage.")
p("At five manually selected reference points, mean/max Y error is <b>0.0592 / 0.0739 percentage points</b>; X error is zero at those references. Eight ambiguous columns remain flagged, so this output stays in review. These errors measure reference-point agreement, not total experimental uncertainty.")
h("What requires review")
p("Overlapping series, unknown calibration, unsupported axes, gaps, thick/disconnected columns and failed tolerances are surfaced explicitly. No OCR or LLM is required. Digitized points are not automatically appended to the master and do not become independent experiments.")
h("NIMS and manual imports")
p("NIMS is local-file import only, with authorized=true and explicit restrictions in context metadata. CSV/TSV/XLSX headers can be mapped explicitly. Source restrictions travel with records; the tool does not scrape authenticated NIMS pages or publish restricted data.")

title(6, "Verify and extend", "Current evidence, operational boundaries and maintenance rules.")
h("Checks")
code(".venv/bin/python -m pytest -q\n.venv/bin/ruff check src tests\ngit diff --check")
p("<b>83 tests pass.</b> Regressions cover two real Celgard layouts, the verified patent table/context, complete UTF-16 instrument files, units/duration, source provenance, repeated setpoints, family aliases, measured-only exports, XLSX permissions, cache/rebuild idempotence, HTTP errors, cumulative BigQuery caps and real/synthetic graph calibration.")
h("Acquisition evidence")
p("A bounded live smoke test verified Celgard and FSRI discovery/acquisition. EPO reported missing credentials; its live OAuth/search remains unverified. Six linked public patent figure sheets were preserved. The main manifest currently exports <b>111 accepted and 60 review records</b>; the isolated demo exports 95 and 52. Neither count is a count of new independent experiments.")
h("Boundaries")
p("Arbitrary patent PDF tables and unresolved experimental context remain review work. Other FSRI apparatus (STA/MCC/Cone) are not automatically normalized by this version. The graph tool supports explicitly calibrated single-series linear tracing. NIMS requires authorized files. License/reuse status is preserved; no upload, billing change or Git push is automatic.")
h("Extend from real examples")
p("Add a source adapter to the small registry; return master records and raw artifacts. Reuse explicit property aliases and validation. Add fixtures before widening semantics. Bump EXTRACTION_VERSION when parsing changes affect cached outputs. Keep legacy wide tables and historical run CSVs separate from master rebuild inputs.")
h("References and companion docs")
for label,url in [
 ("FSRI raw materials repository", "https://github.com/ulfsri/fsri_materials_database"),
 ("Google patent access rules", "https://patents.google.com/robots.txt"),
 ("EPO OPS free-use policy", "https://www.epo.org/en/service-support/ordering/fair-use"),
 ("NIMS access and restrictions", "https://polymer.nims.go.jp/"),
]:
 p(f'<link href="{url}" color="#107F83">{label}</link>',"Cell")
p("<br/><b>Local guides:</b> docs/COLLECTION_GUIDE.md, docs/SOURCE_AUDIT.md and docs/CODE_REVIEW.md. Rebuild using scripts/build_codebase_guide.py.","Cell")

def footer(canvas, doc):
    canvas.setStrokeColor(colors.HexColor("#D9E1E6"))
    canvas.line(54, 45, 558, 45)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#40566A"))
    canvas.drawString(54, 30, "ChE126  |  Codebase & collection guide  |  2026-10-16")
    canvas.drawRightString(558, 30, str(doc.page))


OUT.parent.mkdir(parents=True, exist_ok=True)
SimpleDocTemplate(str(OUT), pagesize=(612, 792), rightMargin=66, leftMargin=66,
                  topMargin=48, bottomMargin=60, title="ChE126 codebase and collection guide",
                  author="ChE126 data science").build(story, onFirstPage=footer, onLaterPages=footer)
print(OUT)
