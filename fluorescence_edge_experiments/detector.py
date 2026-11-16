"""
Production fluorescence cell-edge detector (tuned + refined).

DIC-banded blurred-blob region boundary, validated against hand labels
(see tuning/RESULTS.md): roughly halves the DIC edge error and is robust.

Refinements over the raw tuning version:
  * median-filter despike (removes single-column spikes the Gaussian misses),
  * restrict the output to the cell's x-extent (no extrapolation / border spikes),
  * DIC fallback where the fluorescence is too faint near the boundary.

EXPLORATORY: still not wired into the main pipeline.
"""

import os
import sys
import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edge_methods as em

# Tuned on the 10 hand-labelled frames (tuning/tune_blob.py).
BEST = dict(blur=18, thr_scale=1.0, close=6, band=150, curve_sigma=8,
            median_size=15, restrict_to_dic=True)


def top_edge_banded(binary, dic, band):
    """Uppermost True per column within +/- band rows of the DIC edge.
    Columns where the DIC edge is undefined stay empty (NaN propagates)."""
    h = binary.shape[0]
    rows = np.arange(h)[:, None]
    with np.errstate(invalid='ignore'):
        valid = binary & (rows >= (dic - band)[None, :]) & (rows <= (dic + band)[None, :])
    yy = np.where(valid, rows, h + 1)
    top = yy.min(axis=0).astype(float)
    top[top > h] = np.nan
    return top


def _despike(y, size):
    """Median-filter the defined span of a per-column curve (interpolating gaps)."""
    valid = np.isfinite(y)
    if valid.sum() < max(size, 5):
        return y
    idx = np.where(valid)[0]
    a, b = idx[0], idx[-1]
    seg = y[a:b + 1].copy()
    gaps = ~np.isfinite(seg)
    if gaps.any():
        xs = np.arange(len(seg))
        seg[gaps] = np.interp(xs[gaps], xs[~gaps], seg[~gaps])
    seg = ndi.median_filter(seg, size=size, mode='nearest')
    out = y.copy()
    out[a:b + 1] = seg
    return out


def fluor_edge(image, mask, blur=18, thr_scale=1.0, close=6, band=150,
               curve_sigma=8, median_size=15, restrict_to_dic=True):
    """Return the refined per-column fluorescence edge y(x) (NaN outside the cell)."""
    dic = em.edge_dic(image, mask)
    b = ndi.gaussian_filter(image.astype(float), blur)
    t = em._safe_otsu(b)
    if t is None:
        return dic.copy()
    binary = b > (t * thr_scale)
    if close > 0:
        binary = em.close_binary(binary, close)
    binary = em.largest_component(ndi.binary_fill_holes(binary))

    y = top_edge_banded(binary, dic, band)
    y = np.where(np.isfinite(y), y, dic)      # DIC fallback where no nearby signal
    y = _despike(y, median_size)              # kill isolated spikes
    y = em.smooth_curve(y, curve_sigma)
    if restrict_to_dic:                       # don't extrapolate past the cell
        y = np.where(np.isfinite(dic), y, np.nan)
    return y


def detect_all(images, masks, **params):
    """Run the detector over a stack; returns (n_frames x width) edge array."""
    p = {**BEST, **params}
    w = images.shape[2]
    edges = np.full((images.shape[0], w), np.nan)
    for i in range(images.shape[0]):
        edges[i] = fluor_edge(images[i], masks[i], **p)
    return edges
