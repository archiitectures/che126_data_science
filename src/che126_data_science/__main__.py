"""Command-line discovery, acquisition, cleaning and coverage; no implicit paid jobs."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .data_mining.sources import (
    discover_celgard,
    discover_fsri,
    documents_json,
    polyinfo_plan,
    save_download,
)
from .data_science.observations import coverage, read_observations, write_observations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    discover = commands.add_parser("discover")
    discover.add_argument("source", choices=["celgard", "fsri", "polyinfo"])
    discover.add_argument("material")
    discover.add_argument(
        "--properties",
        nargs="+",
        default=["porosity", "tensile_strength", "thermal_shrinkage"],
    )
    discover.add_argument(
        "--temperatures", nargs="+", type=float, default=[25, 60, 90, 120]
    )
    fetch = commands.add_parser("fetch")
    fetch.add_argument("url")
    fetch.add_argument("directory", type=Path)
    clean = commands.add_parser("clean")
    clean.add_argument("input", type=Path)
    clean.add_argument("output", type=Path)
    report = commands.add_parser("coverage")
    report.add_argument("input", type=Path)
    report.add_argument("--properties", nargs="+", required=True)
    report.add_argument("--temperatures", nargs="+", type=float, required=True)
    report.add_argument("--tolerance", type=float, default=0)
    hfm = commands.add_parser("fsri-hfm")
    hfm.add_argument("snapshot", type=Path)
    hfm.add_argument("output", type=Path)
    curves = commands.add_parser("fsri-curves")
    curves.add_argument("html", type=Path)
    celgard = commands.add_parser("celgard-extract")
    celgard.add_argument("pdf", type=Path)
    celgard.add_argument("output", type=Path)
    celgard.add_argument("--product", required=True)
    celgard.add_argument("--material", required=True)
    celgard.add_argument("--url", required=True)
    patent = commands.add_parser("patents")
    patent.add_argument("terms", nargs="+")
    patent.add_argument("--project", required=True)
    patent.add_argument("--maximum-bytes-billed", type=int, required=True)
    patent.add_argument(
        "--execute", action="store_true", help="Execute instead of dry-run estimate"
    )
    patent.add_argument("--start")
    patent.add_argument("--end")
    patent.add_argument(
        "--fields",
        nargs="+",
        choices=["title", "abstract", "claims", "description"],
        default=["title"],
    )
    from .data_mining.pipeline_cli import COMMANDS, add_commands, run

    add_commands(commands)
    args = parser.parse_args()
    if args.command in COMMANDS:
        print(json.dumps(run(args), indent=2, allow_nan=False))
        return
    if args.command == "discover":
        if args.source == "polyinfo":
            result = polyinfo_plan(args.material, args.properties, args.temperatures)
        else:
            result = documents_json(
                (discover_celgard if args.source == "celgard" else discover_fsri)(
                    args.material
                )
            )
    elif args.command == "fetch":
        result = save_download(args.url, args.directory)
    elif args.command == "clean":
        rows = read_observations(args.input)
        write_observations(rows, args.output)
        result = {"observations": len(rows), "output": str(args.output)}
    elif args.command == "coverage":
        result = coverage(
            read_observations(args.input),
            args.properties,
            args.temperatures,
            tolerance=args.tolerance,
        )
    elif args.command == "fsri-hfm":
        from .data_mining.fsri import hfm_observations

        rows = hfm_observations(json.loads(args.snapshot.read_text()))
        write_observations(rows, args.output)
        result = {"observations": len(rows), "output": str(args.output)}
    elif args.command == "fsri-curves":
        from .data_mining.fsri import extract_public_curves

        result = extract_public_curves(args.html.read_text(encoding="utf-8"))
    elif args.command == "celgard-extract":
        from .data_mining.celgard import parse_datasheet, pdf_text

        result = parse_datasheet(
            pdf_text(args.pdf),
            product=args.product,
            material=args.material,
            source_url=args.url,
        )
        rows = result.pop("observations")
        write_observations(rows, args.output)
        result.update(observations=len(rows), output=str(args.output))
    else:
        from .data_mining.patents import GooglePatentsClient

        result = asdict(
            GooglePatentsClient(project=args.project).search(
                args.terms,
                fields=args.fields,
                titles_only=True,
                publication_start=args.start,
                publication_end=args.end,
                maximum_bytes_billed=args.maximum_bytes_billed,
                dry_run=not args.execute,
            )
        )
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
