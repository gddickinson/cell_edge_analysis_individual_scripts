"""
Candidate cell-edge detectors for the PIEZO1 fluorescence experiments.

EXPERIMENTAL / EXPLORATORY. Nothing here is wired into the main pipeline.

Every method has the uniform signature ``fn(image, mask) -> top_y`` where
``top_y`` is a 1-D array of length = image width giving the edge's y (row) at
each x (column), or NaN where undefined. This "top edge per column"
representation matches the main pipeline's `uppermost`-edge / vertical-
displacement geometry and is trivially convertible to the Nx2 (y, x) contour
that step 2 stores (see ``top_y_to_contour``).

Methods are grouped by what information they use:
  * DIC only   : dic_baseline (the current pipeline edge, for reference)
  * Fluor only : otsu, blob, column_band, ridge
  * Combination: chanvese (DIC init + fluor evolution), snap (DIC + fluor peak)
"""

import numpy as np
from scipy import ndimage as ndi
from skimage import filters, segmentation
from skimage.morphology import disk

# 'uppermost' (min y) matches the pipeline default; 'lowermost' (max y) flips it.
SELECT = 'uppermost'


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def _safe_otsu(arr):
    """Otsu threshold, or None if the array has no usable contrast."""
    finite = arr[np.isfinite(arr)]
    if finite.size == 0 or finite.min() == finite.max():
        return None
    try:
        return float(filters.threshold_otsu(finite))
    except Exception:
        return None


def top_edge_from_binary(binary, which=None):
    """For each column, the uppermost (or lowermost) True row; NaN if none."""
    which = which or SELECT
    h, w = binary.shape
    rows = np.arange(h)[:, None]
    if which == 'lowermost':
        filled = np.where(binary, rows, -1)
        edge = filled.max(axis=0).astype(float)
        edge[edge < 0] = np.nan
    else:  # uppermost
        filled = np.where(binary, rows, h + 1)
        edge = filled.min(axis=0).astype(float)
        edge[edge > h] = np.nan
    return edge


def largest_component(binary):
    """Keep only the largest connected component of a boolean image."""
    lbl, n = ndi.label(binary)
    if n <= 1:
        return binary
    sizes = ndi.sum(np.ones_like(lbl), lbl, index=np.arange(1, n + 1))
    return lbl == (int(np.argmax(sizes)) + 1)


def close_binary(binary, radius):
    """Morphological closing with a disk that does not erode regions touching the image border.

    scipy's binary_closing applies one border_value to both steps, so its erosion treats the outside as background
    and trims a ``radius``-pixel strip wherever the region meets the image edge. Here the dilation treats the outside
    as background and the erosion as foreground (the usual definition, as skimage.morphology.binary_closing).
    """
    if radius <= 0:
        return np.asarray(binary, bool)
    se = disk(radius)
    dilated = ndi.binary_dilation(binary, structure=se, border_value=0)
    return ndi.binary_erosion(dilated, structure=se, border_value=1)


def smooth_curve(y, sigma=4.0):
    """Gaussian-smooth a per-column edge curve, interpolating internal gaps."""
    y = np.asarray(y, float)
    valid = np.isfinite(y)
    if valid.sum() < 3:
        return y
    x = np.arange(len(y))
    first, last = np.where(valid)[0][[0, -1]]
    seg = slice(first, last + 1)
    yi, xi = y[seg].copy(), x[first:last + 1]
    gaps = ~np.isfinite(yi)
    if gaps.any():
        yi[gaps] = np.interp(xi[gaps], xi[~gaps], yi[~gaps])
    yi = ndi.gaussian_filter1d(yi, sigma=sigma, mode='nearest')
    out = np.full_like(y, np.nan)
    out[seg] = yi
    return out


def _band_start(above, min_run):
    """Boolean image: True where a run of >=min_run True pixels starts (downward)."""
    if min_run <= 1:
        return above
    band = above.copy()
    for d in range(1, min_run):
        shifted = np.zeros_like(above)
        shifted[:-d] = above[d:]
        band &= shifted
    return band


def top_y_to_contour(top_y):
    """Convert a per-column edge to an Nx2 (y, x) array like step 2's edges."""
    xs = np.where(np.isfinite(top_y))[0]
    return np.column_stack([top_y[xs], xs.astype(float)]) if xs.size else np.empty((0, 2))


# ----------------------------------------------------------------------------
# Methods
# ----------------------------------------------------------------------------
def edge_dic(image, mask):
    """Baseline: top edge of the DIC-derived binary mask (current pipeline)."""
    return top_edge_from_binary(mask > 0)


def edge_otsu(image, mask=None, smooth_sigma=2.0):
    """Fluor only: Otsu threshold -> fill holes -> largest region -> top edge."""
    sm = ndi.gaussian_filter(image.astype(float), smooth_sigma)
    thr = _safe_otsu(sm)
    if thr is None:
        return np.full(image.shape[1], np.nan)
    binary = ndi.binary_fill_holes(sm > thr)
    binary = largest_component(binary)
    return top_edge_from_binary(binary)


def edge_blob(image, mask=None, smooth_sigma=12.0):
    """Fluor only: heavy blur merges puncta into a blob -> threshold -> top edge.

    Robust to gappy/punctate signal because blurring fills the gaps before the
    boundary is taken.
    """
    blur = ndi.gaussian_filter(image.astype(float), smooth_sigma)
    thr = _safe_otsu(blur)
    if thr is None:
        return np.full(image.shape[1], np.nan)
    binary = ndi.binary_fill_holes(largest_component(blur > thr))
    return top_edge_from_binary(binary)


def edge_column_band(image, mask=None, smooth_sigma=2.0, curve_sigma=4.0,
                     thr=None, min_run=3):
    """Fluor only: per column, the topmost start of a sustained bright band.

    Requiring ``min_run`` consecutive above-threshold pixels ignores lone hot
    pixels above the membrane. The resulting curve is then smoothed.
    """
    sm = ndi.gaussian_filter(image.astype(float), smooth_sigma)
    if thr is None:
        thr = _safe_otsu(sm)
    if thr is None:
        return np.full(image.shape[1], np.nan)
    band = _band_start(sm > thr, min_run)
    return smooth_curve(top_edge_from_binary(band), curve_sigma)


def edge_ridge(image, mask=None, sigmas=(1, 2, 3), curve_sigma=4.0, min_run=2):
    """Fluor only: enhance the membrane band with a Sato ridge filter, then
    take the topmost ridge per column. Targets the membrane line directly."""
    try:
        rid = filters.sato(image.astype(float), sigmas=sigmas, black_ridges=False)
    except Exception:
        return np.full(image.shape[1], np.nan)
    thr = _safe_otsu(rid)
    if thr is None:
        return np.full(image.shape[1], np.nan)
    band = _band_start(rid > thr, min_run)
    return smooth_curve(top_edge_from_binary(band), curve_sigma)


def edge_chanvese(image, mask, iters=200, smoothing=1):
    """Combination: morphological Chan-Vese segmentation of the fluorescence,
    initialised from the DIC mask. Needs enough iterations (~200) to migrate
    from the DIC seed to the true fluorescence boundary when the two disagree;
    too few iterations leaves it stuck on the (possibly wrong) DIC edge."""
    img = image.astype(float)
    img = img / (img.max() + 1e-9)
    init = (mask > 0).astype(np.uint8) if mask is not None else 'checkerboard'
    try:
        ls = segmentation.morphological_chan_vese(img, iters, init_level_set=init,
                                                  smoothing=smoothing)
    except Exception:
        return np.full(image.shape[1], np.nan)
    region = ndi.binary_fill_holes(largest_component(ls > 0))
    return top_edge_from_binary(region)


def edge_snap(image, mask, search=30, smooth_sigma=2.0, curve_sigma=4.0,
              min_signal=None):
    """Combination: start from the DIC edge, move each column to the brightest
    fluorescence pixel within +/- ``search`` rows; keep the DIC position where
    no pixel beats ``min_signal`` (conservative correction of clear gaps)."""
    sm = ndi.gaussian_filter(image.astype(float), smooth_sigma)
    if min_signal is None:
        min_signal = _safe_otsu(sm)
    dic_top = top_edge_from_binary(mask > 0)
    if min_signal is None:
        return dic_top
    h, w = sm.shape
    out = dic_top.copy()
    for x in range(w):
        d = dic_top[x]
        if not np.isfinite(d):
            continue
        y0, y1 = int(max(0, d - search)), int(min(h, d + search + 1))
        seg = sm[y0:y1, x]
        if seg.size and seg.max() >= min_signal:
            out[x] = y0 + int(np.argmax(seg))
    return smooth_curve(out, curve_sigma)


# Registry: name -> {fn, label, color, kind}
METHODS = {
    'dic_baseline': dict(fn=edge_dic,         label='DIC mask (baseline)',           color='red',         kind='dic'),
    'otsu':         dict(fn=edge_otsu,         label='Fluor: Otsu region',            color='cyan',        kind='fluor'),
    'blob':         dict(fn=edge_blob,         label='Fluor: blurred blob',           color='lime',        kind='fluor'),
    'column_band':  dict(fn=edge_column_band,  label='Fluor: top-of-band per column', color='yellow',      kind='fluor'),
    'ridge':        dict(fn=edge_ridge,        label='Fluor: Sato ridge',             color='magenta',     kind='fluor'),
    'chanvese':     dict(fn=edge_chanvese,     label='Chan-Vese (DIC init + fluor)',  color='orange',      kind='both'),
    'snap':         dict(fn=edge_snap,         label='DIC snapped to fluor peak',     color='deepskyblue', kind='both'),
}


def compute_edge(name, image, mask):
    """Run a named method, returning its per-column top edge (NaN-safe)."""
    return METHODS[name]['fn'](image, mask)
