"""Plot accepted distinct contexts; run from any working directory."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/che126-matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm
from matplotlib.ticker import MaxNLocator

ROOT = Path(__file__).resolve().parents[1]
BASE_GROUPS = ["PE", "PP", "PE/PP", "PP/PE/PP"]
ROLES = ["measurement", "exposure", "unknown"]
ROLE_COLORS = ["#2878B5", "#E58A32", "#9CA3AF"]


def separator_group(row):
    if row["sample_form"] == "bulk_reference":
        return "Bulk reference"
    polymer = row["polymer"].strip()
    return polymer or "Type not linked"


def temperature(row):
    return float(row["temperature_C"]) if row["temperature_C"] else None


def labels(ax, bars):
    ax.bar_label(
        bars,
        labels=[f"{v:,.0f}" if v else "" for v in bars.datavalues],
        padding=3,
        fontsize=9,
    )


def style_axis(ax, horizontal=False):
    ax.set_axisbelow(True)
    ax.grid(axis="x" if horizontal else "y", color="#E5E7EB", linewidth=0.7)
    ax.spines[["top", "right"]].set_visible(False)
    (ax.xaxis if horizontal else ax.yaxis).set_major_locator(MaxNLocator(integer=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path, default=ROOT / "datasets/unique_points.csv"
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path(__file__).parent / "figures"
    )
    args = parser.parse_args()
    rows = list(csv.DictReader(args.input.open(newline="", encoding="utf-8")))
    ids = [r["unique_point_id"] for r in rows]
    if not rows or len(set(ids)) != len(ids) or any(not i for i in ids):
        raise ValueError("Input must contain nonempty, distinct unique_point_id values")
    if any(r["review_status"] != "accepted" for r in rows):
        raise ValueError("Input contains records that are not accepted")
    if any(r["temperature_role"] not in ROLES for r in rows):
        raise ValueError("Unexpected temperature role")
    additional = sorted(
        {separator_group(r) for r in rows}
        - set(BASE_GROUPS)
        - {"Type not linked", "Bulk reference"}
    )
    group_order = BASE_GROUPS + additional + ["Type not linked", "Bulk reference"]
    group_colors = (
        ["#2878B5", "#F28E2B", "#59A14F", "#AF7AA1"]
        + [plt.get_cmap("Set2")(i % 8) for i in range(len(additional))]
        + ["#9CA3AF", "#D5BD99"]
    )
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    tables = out.parent / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.titlesize": 15,
            "axes.labelsize": 11,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
            "svg.fonttype": "none",
        }
    )
    artifacts = []

    def save(fig, stem, note):
        fig.text(0.01, 0.012, note, fontsize=9, color="#4B5563", va="bottom")
        for extension in ("png", "svg"):
            path = out / f"{stem}.{extension}"
            fig.savefig(path, dpi=180)
            if extension == "svg":
                # Path-data lines contain significant token separators; trim only
                # trailing XML whitespace to keep generated files diff-clean.
                payload = path.read_bytes()
                path.write_bytes(
                    re.sub(rb"[ \t]+(?=\r?$)", b"", payload, flags=re.MULTILINE)
                )
            artifacts.append(str(path.relative_to(out.parent)))
        plt.close(fig)

    def table(name, fields, records):
        with (tables / f"{name}.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerow(fields)
            writer.writerows(records)

    groups = Counter(separator_group(r) for r in rows)
    fig, ax = plt.subplots(figsize=(14, max(6, 0.34 * len(group_order) + 1.8)))
    fig.subplots_adjust(bottom=0.12, top=0.9, left=0.34, right=0.96)
    bars = ax.barh(
        group_order, [groups[g] for g in group_order], color=group_colors, height=0.65
    )
    ax.invert_yaxis()
    labels(ax, bars)
    ax.set_xlim(0, max(groups.values()) * 1.16)
    ax.set_title(f"Distinct data points by separator type  |  n = {len(rows):,}")
    ax.set_xlabel("Distinct property/context points")
    style_axis(ax, horizontal=True)
    save(
        fig,
        "01_separator_types",
        "Separator types include coatings and component measurements. Bulk references are shown separately.",
    )
    table(
        "separator_types",
        ["separator_type", "count"],
        [(g, groups[g]) for g in group_order],
    )

    temps = sorted({temperature(r) for r in rows if temperature(r) is not None})
    temp_counts = Counter((temperature(r), r["temperature_role"]) for r in rows)
    missing = sum(temperature(r) is None for r in rows)
    fig, ax = plt.subplots(figsize=(16, 6))
    fig.subplots_adjust(bottom=0.25, top=0.83, left=0.06, right=0.98)
    # Native ramps introduce hundreds of slightly different actual temperatures.
    # Bin only the display; exact source temperatures remain in the CSV/table.
    binned = len(temps) > 60
    displayed = sorted({5 * np.floor(t / 5) for t in temps}) if binned else temps
    display_counts = Counter()
    for (temp, role), count in temp_counts.items():
        if temp is not None:
            display_counts[(5 * np.floor(temp / 5) if binned else temp, role)] += count
    x = np.arange(len(displayed))
    bottom = np.zeros(len(displayed))
    for role, color in zip(ROLES, ROLE_COLORS, strict=True):
        values = np.array([display_counts[t, role] for t in displayed])
        ax.bar(x, values, bottom=bottom, color=color, label=role.capitalize())
        bottom += values
    if not binned:
        for position, value in zip(x, bottom, strict=True):
            ax.text(
                position,
                value + 3,
                f"{value:,.0f}",
                ha="center",
                fontsize=8,
                rotation=90,
            )
    tick_positions = x[::2] if binned else x
    tick_labels = [f"{t:g}–{t + 5:g}" if binned else f"{t:g}" for t in displayed]
    ax.set_xticks(
        tick_positions,
        [tick_labels[i] for i in tick_positions],
        rotation=60,
        ha="right",
    )
    ax.set_ylim(0, max(bottom) * 1.23)
    ax.set_title(
        f"Temperature coverage{' (5 °C bins)' if binned else ''}  |  {len(rows) - missing:,} numeric; {missing:,} missing"
    )
    ax.set_xlabel(
        "Temperature bins [lower, upper) in °C; exact temperatures retained in data"
        if binned
        else "Recorded temperature (°C); categorical spacing, no binning"
    )
    ax.set_ylabel("Distinct property/context points")
    ax.legend(frameon=False, loc="upper left")
    style_axis(ax)
    save(
        fig,
        "02_exact_temperatures",
        "Includes bulk references. Exposure ≠ measurement temperature. Missing temperatures are not assumed to be room temperature.\n"
        f"High-temperature records can include composite fiber systems. Includes {sum(r['record_type'] == 'digitized_estimate' for r in rows)} digitized estimates; curve samples are not independent experiments.",
    )
    table(
        "exact_temperatures",
        ["temperature_C", *ROLES, "total"],
        [
            (
                f"{t:g}",
                *(temp_counts[t, role] for role in ROLES),
                sum(temp_counts[t, role] for role in ROLES),
            )
            for t in temps
        ],
    )

    properties = sorted(
        {r["property"] for r in rows},
        key=lambda p: (-sum(r["property"] == p for r in rows), p),
    )
    pc = Counter((r["property"], separator_group(r)) for r in rows)
    fig, ax = plt.subplots(figsize=(14, 11))
    fig.subplots_adjust(left=0.24, right=0.95, top=0.84, bottom=0.08)
    y = np.arange(len(properties))
    left = np.zeros(len(properties))
    for group, color in zip(group_order, group_colors, strict=True):
        values = np.array([pc[p, group] for p in properties])
        ax.barh(y, values, left=left, color=color, label=group, height=0.72)
        left += values
    for position, value in zip(y, left, strict=True):
        ax.text(
            value + max(left) * 0.008,
            position,
            f"{value:,.0f}",
            va="center",
            fontsize=9,
        )
    ax.set_yticks(y, [p.replace("_", " ").capitalize() for p in properties])
    ax.invert_yaxis()
    ax.set_xlim(0, max(left) * 1.1)
    ax.set_xlabel("Distinct property/context points")
    fig.suptitle(
        "Property availability, stratified by separator type", y=0.975, fontsize=17
    )
    ax.legend(
        ncols=4, frameon=False, bbox_to_anchor=(0, 1.01), loc="lower left", fontsize=9
    )
    style_axis(ax, horizontal=True)
    save(
        fig,
        "03_properties_by_separator",
        "All accepted distinct contexts. Type not linked has a per-point identity status/reason in the CSV; it does not imply the patent omits the material.",
    )
    table(
        "properties_by_separator",
        ["property", *group_order, "total"],
        [
            (p, *(pc[p, g] for g in group_order), sum(pc[p, g] for g in group_order))
            for p in properties
        ],
    )

    separators = [r for r in rows if r["sample_form"] != "bulk_reference"]
    st = sorted({temperature(r) for r in separators if temperature(r) is not None})
    coverage = Counter((r["property"], temperature(r)) for r in separators)
    matrix = np.array([[coverage[p, t] for t in st] for p in properties])
    fig, ax = plt.subplots(figsize=(15, 11))
    fig.subplots_adjust(left=0.24, bottom=0.15, top=0.89, right=0.88)
    cmap = plt.get_cmap("Blues").copy()
    cmap.set_bad("#F2F3F5")
    im = ax.imshow(
        np.ma.masked_equal(matrix, 0),
        aspect="auto",
        cmap=cmap,
        norm=LogNorm(vmin=1, vmax=max(2, matrix.max())),
    )
    for i in range(len(properties)):
        for j in range(len(st)):
            value = matrix[i, j]
            ax.text(
                j,
                i,
                str(value) if value else "·",
                ha="center",
                va="center",
                fontsize=8,
                color="white" if value > 40 else "#263238",
            )
    ax.set_xticks(range(len(st)), [f"{t:g}" for t in st], rotation=45, ha="right")
    ax.set_yticks(
        range(len(properties)), [p.replace("_", " ").capitalize() for p in properties]
    )
    ax.set_xlabel("Reported measurement or exposure temperature (°C)")
    ax.set_title(
        "Separator property × temperature coverage\nIncludes points without a linked type; bulk references excluded",
        pad=20,
    )
    fig.colorbar(
        im, ax=ax, fraction=0.025, pad=0.025, label="Count (logarithmic color scale)"
    )
    save(
        fig,
        "04_property_temperature_coverage",
        "Dots denote zero records. Numeric measurement and exposure conditions are combined here; see figure 02 for their distinction.\n"
        "A melting/shutdown temperature result is a property value, not automatically a measurement-temperature condition.",
    )
    table(
        "property_temperature_coverage",
        ["property", *[f"{t:g} C" for t in st]],
        [(p, *matrix[i]) for i, p in enumerate(properties)],
    )

    fig, axes = plt.subplots(1, 3, figsize=(17, 6))
    fig.subplots_adjust(left=0.04, right=0.97, bottom=0.26, top=0.79, wspace=0.43)
    panels = [
        ("extraction_method", "Extraction method"),
        ("record_type", "Record type"),
        ("sample_form", "Sample scope"),
    ]
    meta = []
    for ax, (field, title) in zip(axes, panels, strict=True):
        counts = Counter(r[field] or "unknown" for r in rows)
        pairs = counts.most_common()
        bars = ax.bar(range(len(pairs)), [n for _, n in pairs], color="#2878B5")
        labels(ax, bars)
        ax.set_xticks(
            range(len(pairs)), [k.replace("_", "\n") for k, _ in pairs], fontsize=9
        )
        ax.set_ylim(0, max(counts.values()) * 1.17)
        ax.set_title(title)
        style_axis(ax)
        meta.extend((field, k, n) for k, n in pairs)
    axes[0].set_ylabel("Distinct property/context points")
    fig.suptitle("Collection and evidence metadata", fontsize=17, y=0.96)
    save(
        fig,
        "05_collection_metadata",
        "Extraction method is taken from each distinct point's representative observation. Manual imports include patent and paper tables.\n"
        "Measured, digitized estimates, specification limits, calculated values and unknown record types are retained as separate categories.",
    )
    table("collection_metadata", ["field", "category", "count"], meta)
    if "material_identity_status" in rows[0]:
        counts = Counter(
            r["material_identity_status"] or "not recorded"
            for r in rows
            if not r["polymer"]
        )
        if counts:
            pairs = counts.most_common()
            fig, ax = plt.subplots(figsize=(12, 6))
            fig.subplots_adjust(left=0.32, right=0.94, top=0.85, bottom=0.16)
            bars = ax.barh(
                [k.replace("_", " ") for k, _ in pairs],
                [n for _, n in pairs],
                color="#9CA3AF",
            )
            labels(ax, bars)
            ax.invert_yaxis()
            ax.set_xlim(0, max(counts.values()) * 1.2)
            ax.set_xlabel("Distinct property/context points")
            ax.set_title("Why a specific separator type is not yet linked")
            style_axis(ax, horizontal=True)
            save(
                fig,
                "06_material_identity_gaps",
                "Reasons describe remaining evidence/linking gaps. They are not interchangeable with source material being undisclosed.",
            )
            table("material_identity_gaps", ["status", "count"], pairs)
    summary = {
        "input": str(args.input.resolve()),
        "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "distinct_points": len(rows),
        "separator_or_component_points": len(separators),
        "bulk_reference_points": groups["Bulk reference"],
        "numeric_temperature_points": len(rows) - missing,
        "missing_temperature_points": missing,
        "separator_types": dict(groups),
        "property_count": len(properties),
        "matplotlib_version": matplotlib.__version__,
        "figures": artifacts,
    }
    (out.parent / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    assert sum(groups.values()) == len(rows)
    assert sum(pc.values()) == len(rows)
    assert sum(temp_counts[t, role] for t in temps for role in ROLES) + missing == len(
        rows
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
