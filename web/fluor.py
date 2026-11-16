"""Run the fluorescence-edge experiments' own code (fluorescence_edge_experiments/) on in-memory stacks.

- detect(): detector.fluor_edge (the tuned DIC-banded blurred-blob detector, still exploratory and not wired into
  the pipeline) and edge_methods.edge_dic for every requested frame, with errors against labels when given.
- methods(): all seven candidate detectors of edge_methods.METHODS on one frame (the "*_methods.png" comparison).
Like the experiments, both read step-1 output: the stack is first preprocessed with the pipeline's default step 1
(web.analysis.preprocess). Edges are per-column y(x) in pixels (NaN where undefined), 'uppermost' geometry.
"""
import sys

import numpy as np

from web import analysis

EXP = analysis.ROOT / "fluorescence_edge_experiments"
sys.path[:0] = [str(EXP), str(EXP / "tuning")]
import detector  # noqa: E402
import edge_methods as em  # noqa: E402
from run_experiments import gap_between  # noqa: E402
from tune_blob import frame_error  # noqa: E402

DETECTOR_KEYS = {"blur": float, "thr_scale": float, "close": int, "band": float, "curve_sigma": float,
                 "median_size": int, "restrict_to_dic": bool}


def detector_params(params=None):
    """detector.BEST overlaid with the given values (types as fluor_edge uses them)."""
    p = dict(detector.BEST)
    for k, v in (params or {}).items():
        if k not in DETECTOR_KEYS:
            raise ValueError(f"unknown detector parameter {k!r}")
        p[k] = (v if isinstance(v, bool) else str(v).lower() == "true") if DETECTOR_KEYS[k] is bool else DETECTOR_KEYS[k](v)
    if p["blur"] <= 0 or p["curve_sigma"] <= 0 or p["median_size"] < 1 or p["close"] < 0 or p["band"] < 0:
        raise ValueError("blur and curve_sigma must be > 0, median_size >= 1, close and band >= 0")
    return p


def label_error(edge, truth):
    """tune_blob.frame_error: median |edge - label| over columns where both are defined (None with < 5 such columns),
    and the fraction of columns scored."""
    if truth is None:
        return None
    err, cov = frame_error(np.asarray(edge, float), np.asarray(truth, float))
    return None if not np.isfinite(err) else {"median": err, "scored": cov}


def gap(edge, dic):
    """run_experiments.gap_between: median |edge - DIC edge| (px), the experiments' per-frame QC gap."""
    v = gap_between(np.asarray(edge, float), np.asarray(dic, float))
    return None if np.isnan(v) else v


def _list(y):
    return [analysis.num(v) for v in np.asarray(y, float)]


def detect(images, masks, params=None, frames=None, labels=None):
    """Detector + DIC edge for each frame; labels: {frame: y(x)} (optional)."""
    p = detector_params(params)
    pre, _ = analysis.preprocess(images, masks)
    images, masks = analysis.as_stacks(images, masks)
    frames = list(range(pre.shape[0])) if frames is None else [int(f) for f in frames]
    out = []
    for i in frames:
        dic = em.edge_dic(pre[i], masks[i])
        fl = detector.fluor_edge(pre[i], masks[i], **p)
        truth = None if labels is None else labels.get(i)
        out.append({"frame": i, "dic": _list(dic), "fluor": _list(fl), "gap": gap(fl, dic),
                    "error_dic": label_error(dic, truth), "error_fluor": label_error(fl, truth)})
    return {"params": p, "frames": out}


def methods(images, masks, frame, labels=None):
    """Every candidate method of edge_methods.METHODS on one frame (default parameters), with its coverage, median
    gap to the DIC edge and, when labels are given, its error against them."""
    pre, _ = analysis.preprocess(images, masks)
    images, masks = analysis.as_stacks(images, masks)
    img, m = pre[frame], masks[frame]
    dic = em.edge_dic(img, m)
    truth = None if labels is None else labels.get(frame)
    out = []
    for name, spec in em.METHODS.items():
        y = em.compute_edge(name, img, m)
        out.append({"name": name, "label": spec["label"], "kind": spec["kind"], "color": spec["color"],
                    "edge": _list(y), "coverage": float(np.isfinite(y).mean()), "gap_to_dic": gap(y, dic),
                    "error": label_error(y, truth)})
    tuned = detector.fluor_edge(img, m, **detector.BEST)
    out.append({"name": "detector", "label": "Tuned detector (detector.py)", "kind": "both", "color": "white",
                "edge": _list(tuned), "coverage": float(np.isfinite(tuned).mean()), "gap_to_dic": gap(tuned, dic),
                "error": label_error(tuned, truth)})
    return {"frame": int(frame), "methods": out}
