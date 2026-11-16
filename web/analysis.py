"""Run the repo's own step 1, 2, 5, 6 and 7 code on in-memory stacks (for the web API and the JS-vs-Python fixture).

Nothing here re-implements the analysis: it calls step1_data_loading.subtract_background / normalize_frames /
_compute_reference (with the normalisation options this repo adds), step2_edge_detection.detect_cell_edge /
smooth_edge, step5_edge_sampling.sample_all_edges, step6_sampling_rectangles.create_rectangles_for_frame and
step7_intensity_extraction.extract_intensity_from_rectangle (mean / max / percentile), and labels the intensity with
intensity_labels.build_intensity_label. The step functions read their module's CONFIG dict, so each run sets those
keys under a lock and restores them afterwards.

Units: pixels throughout, as in the pipeline. Coordinates are (row, col) = (y, x) with the pixel-centre convention of
skimage.measure.find_contours.
"""
import contextlib
import io
import os
import sys
import threading
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("MPLBACKEND", "Agg")  # the step modules import pyplot at import time

import config  # noqa: E402  (the single source of pipeline defaults)
import intensity_labels  # noqa: E402
import step1_data_loading as s1  # noqa: E402
import step2_edge_detection as s2  # noqa: E402
import step5_edge_sampling as s5  # noqa: E402
import step6_sampling_rectangles as s6  # noqa: E402
import step7_intensity_extraction as s7  # noqa: E402

_LOCK = threading.Lock()

# Choices exactly as offered by the step scripts' argparse options.
CHOICES = {
    "normalization_method": ["max", "percentile"], "normalization_region": ["frame", "mask"],
    "normalization_scope": ["per_frame", "global"], "intensity_statistic": ["mean", "max", "percentile"],
    "sampling_method": ["per_frame", "fixed_x", "dense", "displacement_like"], "y_selection": ["uppermost", "lowermost"],
    "rotation_method": ["none", "flip", "search", "vertical"],
}
INT_KEYS = {"n_points", "target_points_displacement", "depth", "width", "rotation_search_angles"}
BOOL_KEYS = {"normalize_frames", "subtract_background", "smooth_edges", "exclude_endpoints"}
STEP1_KEYS = ["normalize_frames", "normalization_scale", "normalization_method", "normalization_percentile",
              "normalization_region", "normalization_scope", "subtract_background", "background_percentile"]


def default_params():
    """The web parameters, with defaults from config.PIPELINE_CONFIG (shared with the scripts and the GUI)."""
    c = config.PIPELINE_CONFIG
    p = {k: c["step1"][k] for k in STEP1_KEYS}
    p.update({k: c["step2"][k] for k in ("smooth_edges", "smoothing_sigma")})
    p.update({k: c["step5"][k] for k in ("sampling_method", "n_points", "exclude_endpoints",
                                         "target_points_displacement", "y_selection")})
    p.update({k: c["step6"][k] for k in ("depth", "width", "min_cell_coverage", "rotation_method",
                                         "rotation_search_angles")})
    p.update({k: c["step7"][k] for k in ("intensity_statistic", "intensity_percentile")})
    return p


def clean_params(params):
    """Defaults overlaid with the given values, type-checked against the step scripts' options."""
    p = default_params()
    for k, v in (params or {}).items():
        if k not in p:
            raise ValueError(f"unknown parameter {k!r}")
        if k in BOOL_KEYS:
            p[k] = v if isinstance(v, bool) else str(v).lower() == "true"
        elif k in INT_KEYS:
            p[k] = int(v)
        elif k in CHOICES:
            p[k] = str(v)
            if p[k] not in CHOICES[k]:
                raise ValueError(f"{k} must be one of {CHOICES[k]}")
        else:
            p[k] = float(v)
    for k in ("normalization_percentile", "intensity_percentile", "background_percentile"):
        if not 0 <= p[k] <= 100:
            raise ValueError(f"{k} must be between 0 and 100")
    if p["smooth_edges"] and p["smoothing_sigma"] <= 0:
        raise ValueError("smoothing_sigma must be > 0")
    if p["n_points"] < 1 or p["target_points_displacement"] < 1 or p["rotation_search_angles"] < 1:
        raise ValueError("point counts and search angles must be >= 1")
    if p["width"] <= 0 or p["depth"] <= 0:
        raise ValueError("rectangle width and depth must be > 0")
    return p


@contextlib.contextmanager
def _config(module, values):
    old = {k: module.CONFIG.get(k, None) for k in values}
    missing = [k for k in values if k not in module.CONFIG]
    module.CONFIG.update(values)
    try:
        yield
    finally:
        module.CONFIG.update(old)
        for k in missing:
            module.CONFIG.pop(k, None)


def as_stacks(images, masks):
    """(T, H, W) image and binary-mask stacks as step 1 loads them (2-D inputs become one frame)."""
    images, masks = np.asarray(images), (np.asarray(masks) > 0).astype(np.uint8)
    if images.ndim == 2:
        images = images[np.newaxis]
    if masks.ndim == 2:
        masks = masks[np.newaxis]
    if images.ndim != 3 or masks.ndim != 3:
        raise ValueError(f"expected 2-D or 3-D stacks, got image {images.shape} and mask {masks.shape}")
    if images.shape[1:] != masks.shape[1:]:
        raise ValueError(f"image frames are {images.shape[1:]} but mask frames are {masks.shape[1:]}")
    if images.shape[0] != masks.shape[0]:
        raise ValueError(f"image stack has {images.shape[0]} frames but mask stack has {masks.shape[0]}")
    return images, masks


def step1_config(p):
    return {"BACKGROUND_PERCENTILE": p["background_percentile"], "NORMALIZATION_SCALE": p["normalization_scale"],
            "NORMALIZATION_METHOD": p["normalization_method"], "NORMALIZATION_PERCENTILE": p["normalization_percentile"],
            "NORMALIZATION_REGION": p["normalization_region"], "NORMALIZATION_SCOPE": p["normalization_scope"]}


def references(images, masks, p):
    """The value each frame is divided by in normalize_frames (one value repeated for 'global'), from the
    background-subtracted stack, using step1's own _compute_reference. Same fallbacks as normalize_frames."""
    method, pct = p["normalization_method"], p["normalization_percentile"]
    imgs = images.astype(np.float32)
    use_mask = p["normalization_region"] == "mask"
    if p["normalization_scope"] == "global":
        vals = imgs[masks > 0] if use_mask and np.any(masks > 0) else imgs
        return [s1._compute_reference(vals, method, pct)] * imgs.shape[0]
    out = []
    for i in range(imgs.shape[0]):
        sel = masks[i] > 0
        vals = imgs[i][sel] if use_mask and np.any(sel) else imgs[i].ravel()
        out.append(s1._compute_reference(vals, method, pct))
    return out


def preprocess(images, masks, params=None):
    """Step 1 on the stacks: (preprocessed float32 stack, per-frame references or None)."""
    p = clean_params(params)
    images, masks = as_stacks(images, masks)
    with _LOCK, contextlib.redirect_stdout(io.StringIO()), _config(s1, step1_config(p)):
        if p["subtract_background"]:
            images = s1.subtract_background(images)
        refs = None
        if p["normalize_frames"]:
            refs = references(images, masks, p)
            images = s1.normalize_frames(images, masks)
    return images.astype(np.float32), refs


def label(p):
    """The self-describing axis label the pipeline would put on these intensities (intensity_labels)."""
    meta = {"normalized": p["normalize_frames"], **{k: p[k] for k in STEP1_KEYS if k.startswith("normalization_")}}
    return intensity_labels.build_intensity_label(meta, p["intensity_statistic"], p["intensity_percentile"])


def run(images, masks, params=None, frames=None):
    """Steps 1, 2, 5, 6, 7 on the stacks. `frames` limits steps 6-7 to those frame indices (edges and sampling
    always use every frame, because 'fixed_x' sampling needs the x-range common to all frames)."""
    p = clean_params(params)
    images, masks = as_stacks(images, masks)
    frames = list(range(images.shape[0])) if frames is None else [int(f) for f in frames]
    pre, refs = preprocess(images, masks, p)
    with _LOCK, contextlib.redirect_stdout(io.StringIO()):
        edges = []
        for m in masks:
            e = s2.detect_cell_edge(m)
            if p["smooth_edges"] and len(e) > 0:
                e = s2.smooth_edge(e, p["smoothing_sigma"])
            edges.append(e)
        with _config(s5, {k: p[k] for k in ("sampling_method", "n_points", "exclude_endpoints", "y_selection",
                                            "target_points_displacement")}):
            sampled = s5.sample_all_edges(edges)
        out = []
        with _config(s6, {k: p[k] for k in ("depth", "width", "min_cell_coverage", "rotation_method",
                                            "rotation_search_angles")}):
            for i in frames:
                rects = []
                if len(sampled[i]) > 0 and len(edges[i]) > 0:
                    rects = s6.create_rectangles_for_frame(sampled[i], edges[i], masks[i])
                for r in rects:
                    r["intensity"] = (s7.extract_intensity_from_rectangle(
                        pre[i], r["pixels"], p["intensity_statistic"], p["intensity_percentile"])
                        if r["accepted"] else np.nan)
                out.append({"frame": i, "edge": edges[i], "sampled": sampled[i], "rects": rects})
    return {"params": p, "label": label(p), "references": refs, "n_frames": int(images.shape[0]),
            "shape": list(images.shape[1:]), "frames": out}


def num(v):
    v = float(v)
    return None if np.isnan(v) else v


def to_json(result):
    """JSON-safe form of run()'s result (NaN -> null; pixel lists replaced by their count)."""
    frames = []
    for f in result["frames"]:
        frames.append({
            "frame": f["frame"],
            "edge": [[num(a), num(b)] for a, b in np.asarray(f["edge"]).reshape(-1, 2)],
            "sampled": [[num(a), num(b)] for a, b in np.asarray(f["sampled"]).reshape(-1, 2)],
            "rects": [{"point_index": int(r["point_index"]), "edge_point": [num(v) for v in r["edge_point"]],
                       "corners": [[num(a), num(b)] for a, b in np.asarray(r["corners"])],
                       "coverage": num(r["coverage"]), "accepted": bool(r["accepted"]),
                       "rotation_angle": float(r["rotation_angle"]), "n_pixels": int(len(r["pixels"])),
                       "intensity": num(r["intensity"])} for r in f["rects"]],
        })
    refs = result["references"]
    return {"params": result["params"], "label": result["label"],
            "references": None if refs is None else [num(v) for v in refs],
            "n_frames": result["n_frames"], "shape": result["shape"], "frames": frames}
