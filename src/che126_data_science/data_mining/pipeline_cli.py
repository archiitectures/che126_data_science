"""New workflow commands, kept separate from the existing CLI contracts."""

import json
from pathlib import Path

COMMANDS = {"ingest", "collect", "aggregate", "manual-import", "digitize", "figures"}


def add_commands(commands):
    ingest = commands.add_parser(
        "ingest", help="Ingest one local document, folder, or public URL"
    )
    ingest.add_argument(
        "--source",
        required=True,
        choices=["celgard", "fsri", "patents", "manual", "polyinfo", "literature"],
    )
    ingest.add_argument("--input", required=True)
    ingest.add_argument(
        "--context", type=Path, help="Explicit metadata/column mapping JSON"
    )
    ingest.add_argument("--data-dir", type=Path, default=Path("data"))
    ingest.add_argument("--refresh", action="store_true")
    manual = commands.add_parser(
        "manual-import", help="Import an authorized local CSV/TSV/XLSX"
    )
    manual.add_argument(
        "--source", choices=["manual", "polyinfo", "literature"], default="manual"
    )
    manual.add_argument("--input", required=True, type=Path)
    manual.add_argument("--context", required=True, type=Path)
    manual.add_argument("--data-dir", type=Path, default=Path("data"))
    collect = commands.add_parser(
        "collect", help="Bounded, cached automatic collection"
    )
    collect.add_argument(
        "--sources",
        nargs="+",
        choices=["celgard", "fsri", "patents", "polyinfo"],
        default=["celgard", "fsri", "patents"],
    )
    collect.add_argument(
        "--materials", nargs="+", default=["polyethylene", "polypropylene"]
    )
    collect.add_argument("--max-documents", type=int, default=50)
    collect.add_argument("--patent-limit", type=int, default=25)
    collect.add_argument(
        "--patent-provider", choices=["epo", "bigquery"], default="epo"
    )
    collect.add_argument("--project")
    collect.add_argument("--budget-usd", default="2")
    collect.add_argument(
        "--usd-per-tib",
        default="6.25",
        help="Explicit US on-demand analysis rate; verify when running",
    )
    collect.add_argument("--fsri-revision", default="main")
    collect.add_argument("--refresh", action="store_true")
    collect.add_argument("--data-dir", type=Path, default=Path("data"))
    aggregate = commands.add_parser(
        "aggregate", help="Rebuild selected manifest's master exports"
    )
    aggregate.add_argument("--data-dir", type=Path, default=Path("data"))
    aggregate.add_argument("--out-dir", type=Path)
    aggregate.add_argument("--measured-only", action="store_true")
    figures = commands.add_parser(
        "figures", help="Preserve patent figure sheets and caption manifest"
    )
    figures.add_argument("--data-dir", type=Path, default=Path("data"))
    figures.add_argument("--refresh", action="store_true")
    graph = commands.add_parser(
        "digitize", help="Trace one explicitly calibrated/isolated curve"
    )
    graph.add_argument("--input", required=True, type=Path)
    graph.add_argument("--calibration", required=True, type=Path)
    graph.add_argument(
        "--out-dir", type=Path, default=Path("data/processed/digitization")
    )


def run(args):
    if args.command == "digitize":
        from .digitize import digitize

        return digitize(args.input, args.calibration, args.out_dir)
    from .pipeline import Pipeline

    pipeline = Pipeline(args.data_dir)
    if args.command == "figures":
        return pipeline.figures(refresh=args.refresh)
    if args.command == "aggregate":
        return pipeline.aggregate(args.out_dir, measured_only=args.measured_only)
    if args.command == "collect":
        return pipeline.collect(
            sources=args.sources,
            materials=args.materials,
            max_documents=args.max_documents,
            patent_limit=args.patent_limit,
            patent_provider=args.patent_provider,
            project=args.project,
            budget_usd=args.budget_usd,
            usd_per_tib=args.usd_per_tib,
            refresh=args.refresh,
            fsri_revision=args.fsri_revision,
        )
    context = json.loads(args.context.read_text()) if args.context else {}
    location = str(args.input)
    path = Path(location)
    locations = (
        sorted(
            p
            for p in path.iterdir()
            if p.is_file()
            and p.suffix.lower()
            in {".pdf", ".html", ".htm", ".csv", ".tsv", ".xlsx", ".tst", ".json"}
        )
        if path.is_dir()
        else [location]
    )
    if not locations:
        raise ValueError("No supported documents in input directory")
    results = []
    for location in locations:
        from .errors import source_failure

        try:
            results.append(
                pipeline.ingest(
                    args.source,
                    location,
                    context=context,
                    refresh=getattr(args, "refresh", False),
                )
            )
        except Exception as exc:
            if not source_failure(exc):
                raise
            results.append(
                {
                    "source": args.source,
                    "location": str(location),
                    "status": "fetch_failed",
                    "error": str(exc),
                }
            )
    return {"documents": results, "outputs": pipeline.aggregate()}
