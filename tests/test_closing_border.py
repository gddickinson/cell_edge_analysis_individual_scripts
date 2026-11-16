"""Regression: the fluorescence detector's morphological closing does not erode regions touching the image border.

scipy.ndimage.binary_closing uses one border_value (0) for both the dilation and the erosion, so the erosion treated
everything outside the image as background and removed a `close`-pixel strip wherever the bright region touched the
image edge: detector.fluor_edge then lost (or moved) the edge in the outer columns. Closing now follows the usual
definition (dilation with outside = 0, erosion with outside = 1, as skimage.morphology.binary_closing), so only gaps
narrower than the disk are filled and nothing touching the border is removed.
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "fluorescence_edge_experiments"), str(ROOT / "fluorescence_edge_experiments" / "tuning")]

import detector  # noqa: E402
import edge_methods as em  # noqa: E402


def test_closing_keeps_region_touching_the_border():
    b = np.zeros((40, 50), bool)
    b[20:, :] = True                  # a cell sheet filling the lower half, touching left, right and bottom
    b[20:23, 30] = False              # a 1-px notch the closing should fill
    out = em.close_binary(b, 3)
    assert out[20:, 0].all() and out[20:, -1].all() and out[-1].all(), "border strip eroded"
    assert out[21:23, 30].all(), "notch not closed"
    assert not out[:20].any() and (out[20:] | ~b[20:]).all()


def test_detector_edge_reaches_the_outer_columns():
    rows, cols = np.mgrid[0:120, 0:160]
    img = np.where(rows > 60, 100.0, 0.0)
    mask = (rows > 60).astype(np.uint8)
    y = detector.fluor_edge(img, mask, blur=3, close=6, band=30, curve_sigma=1, median_size=1)
    assert np.isfinite(y).all()
    assert np.abs(y - y[80]).max() < 0.5, "edge bends near the image border"


def test_tune_blob_uses_the_same_closing():
    import tune_blob
    b = np.zeros((30, 30))
    b[15:, :] = 1.0
    out = tune_blob.clean_binary(b, 0.5, 1.0, 4)
    assert out[15:, 0].all() and out[15:, -1].all() and out[-1].all()
