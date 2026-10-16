"""Calibrated single-series tracing; no OCR, agents, or inferred calibration."""

import hashlib
import json
import math
from pathlib import Path

from che126_data_science.data_science.master import (
    atomic_bytes,
    atomic_json,
    csv_bytes,
    fingerprint,
)


def digitize(path, calibration, out_dir):
    import numpy as np
    from PIL import Image, ImageDraw

    config = (
        json.loads(Path(calibration).read_text())
        if not isinstance(calibration, dict)
        else calibration
    )
    image_path = Path(path)
    digest = hashlib.sha256(image_path.read_bytes()).hexdigest()
    if config.get("source_sha256") != digest:
        raise ValueError("Calibration source hash must match image")
    image = Image.open(image_path).convert("RGB")
    width, height = image.size
    directory = Path(out_dir)
    figure = {
        "source_file": str(image_path),
        "source_sha256": digest,
        "source_url": config.get("source_url"),
        "figure": config.get("figure"),
        "caption": config.get("caption"),
        "crop": config.get("crop"),
    }
    columns = [
        "curve_id",
        "x",
        "y",
        "x_unit",
        "y_unit",
        "series_label",
        "plot_type",
        "uncertainty_x",
        "uncertainty_y",
        "pixel_x",
        "pixel_y",
    ]
    points, flags = [], []
    try:
        if config.get("plot_type") != "linear" or not config.get("single_series"):
            raise ValueError(
                "Only explicitly isolated single-series linear plots supported"
            )
        if config.get("series_count", 1) > 1 and not config.get("mask_polygon"):
            raise ValueError("Multi-series figure requires an explicit isolation mask")
        crop = config["crop"]
        if len(crop) != 4 or not (
            0 <= crop[0] < crop[2] <= width and 0 <= crop[1] < crop[3] <= height
        ):
            raise ValueError("Invalid plot crop")
        axes = []
        for axis in ("x", "y"):
            refs = config[axis + "_reference"]
            if len(refs) != 2 or not config.get(axis + "_unit"):
                raise ValueError("Two axis reference points and units required")
            p0, v0 = map(float, refs[0])
            p1, v1 = map(float, refs[1])
            if (
                not all(math.isfinite(x) for x in (p0, v0, p1, v1))
                or p0 == p1
                or v0 == v1
            ):
                raise ValueError("Degenerate or nonfinite axis calibration")
            if (
                axis == "x"
                and (v1 - v0) / (p1 - p0) <= 0
                or axis == "y"
                and (v1 - v0) / (p1 - p0) >= 0
            ):
                raise ValueError(
                    "Expected x increasing rightward and y increasing upward"
                )
            axes.append(((v1 - v0) / (p1 - p0), v0 - p0 * (v1 - v0) / (p1 - p0)))
        pixels = np.array(image)
        color = np.array(config.get("curve_rgb", [0, 0, 0]))
        mask = np.max(np.abs(pixels.astype(float) - color), axis=2) <= float(
            config.get("color_tolerance", 100)
        )
        x0, y0, x1, y1 = map(int, crop)
        # Remove long horizontal grid lines before applying a curve isolation mask.
        if config.get("remove_horizontal_grid", False):
            grid = mask[y0:y1, x0:x1].mean(axis=1) > 0.6
            for y in np.flatnonzero(grid) + y0:
                mask[max(y0, y - 1) : min(y1, y + 2), x0:x1] = False
        if config.get("mask_polygon"):
            selection = Image.new("1", image.size)
            ImageDraw.Draw(selection).polygon(
                [tuple(p) for p in config["mask_polygon"]], fill=1
            )
            mask &= np.array(selection, dtype=bool)
        curve_id = fingerprint({"image": digest, "calibration": config})
        max_thickness = float(config.get("max_curve_thickness_px", 15))
        max_jump = float(config.get("max_jump_px", 25))
        step = int(config.get("sample_step_px", 4))
        if step < 1:
            raise ValueError("sample_step_px must be positive")
        previous = None
        for x in range(x0, x1, step):
            ys = np.flatnonzero(mask[y0:y1, x]) + y0
            if not len(ys):
                previous = None
                continue
            # A disconnected group is an overlap/label, not an average curve.
            if np.any(np.diff(ys) > 3) or ys[-1] - ys[0] > max_thickness:
                flags.append({"pixel_x": x, "reason": "ambiguous_curve_column"})
                previous = None
                continue
            y = float(np.median(ys))
            if previous is not None and abs(y - previous) > max_jump:
                flags.append({"pixel_x": x, "reason": "implausible_jump"})
                previous = None
                continue
            previous = y
            ax, bx = axes[0]
            ay, by = axes[1]
            points.append(
                {
                    "curve_id": curve_id,
                    "x": ax * x + bx,
                    "y": ay * y + by,
                    "x_unit": config["x_unit"],
                    "y_unit": config["y_unit"],
                    "series_label": config["series_label"],
                    "plot_type": "linear",
                    "uncertainty_x": abs(ax)
                    * float(config.get("calibration_error_px", 1)),
                    "uncertainty_y": abs(ay)
                    * (
                        max(1, (ys[-1] - ys[0]) / 2)
                        + float(config.get("calibration_error_px", 1))
                    ),
                    "pixel_x": x,
                    "pixel_y": y,
                }
            )
        if not points:
            raise ValueError("No unambiguous calibrated curve points")
        errors_x, errors_y = [], []
        for reference in config.get("reference_points", []):
            nearest = min(points, key=lambda p: abs(p["x"] - reference[0]))
            errors_x.append(abs(nearest["x"] - reference[0]))
            errors_y.append(abs(nearest["y"] - reference[1]))
        metrics = {
            "reference_count": len(errors_y),
            "mean_error_x": sum(errors_x) / len(errors_x) if errors_x else None,
            "max_error_x": max(errors_x) if errors_x else None,
            "mean_error_y": sum(errors_y) / len(errors_y) if errors_y else None,
            "max_error_y": max(errors_y) if errors_y else None,
        }
        tolerances = config.get("tolerances", {})
        for metric, limit in tolerances.items():
            if (
                metric not in metrics
                or metrics[metric] is None
                or not math.isfinite(float(limit))
                or limit < 0
            ):
                raise ValueError(f"Invalid/unverifiable error tolerance: {metric}")
            if metrics[metric] > limit:
                flags.append({"reason": "error_tolerance_exceeded", "metric": metric})
        result = {
            "status": "review" if flags else "accepted",
            "points": len(points),
            "record_type": "digitized_estimate",
            "curve_count": 1,
            "curve_id": curve_id,
            "metrics": metrics,
            "review": flags,
            "note": "Selected trace/segment only. Pixel samples share one curve identity; not independent experiments.",
        }
        image.crop(tuple(crop)).save(directory_image_path(directory))
    except (KeyError, ValueError, TypeError) as exc:
        points = []
        result = {"status": "review", "points": 0, "review": [{"reason": str(exc)}]}
    atomic_bytes(directory / "curve_points.csv", csv_bytes(points, columns))
    atomic_bytes(directory / "figures_manifest.csv", csv_bytes([figure], list(figure)))
    atomic_json(directory / "calibration.json", config)
    atomic_json(directory / "digitization_qc.json", result)
    return result


def directory_image_path(directory):
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "figure_crop.png"
