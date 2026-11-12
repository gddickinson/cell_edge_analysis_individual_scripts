"""Regression: step 6 handles the NaN placeholders that step 5 writes for x-positions with no edge point.

step5_edge_sampling.sample_edge_at_fixed_x ('fixed_x' sampling) records [nan, x] where no edge point lies within the
search window (likely with many points, e.g. --n-points 100). step 6 then crashed with
"ValueError: cannot convert float NaN to integer" in check_cell_coverage, stopping the whole pipeline.
"""
import os
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("MPLBACKEND", "Agg")

import step6_sampling_rectangles as s6  # noqa: E402


@pytest.mark.parametrize("method", ["vertical", "none", "flip", "search"])
def test_nan_point_gives_rejected_rectangle(method, monkeypatch):
    mask = np.zeros((80, 80), np.uint8)
    mask[30:, :] = 1
    edge = np.array([[29.5, float(x)] for x in range(80)])
    pts = np.array([[29.5, 20.0], [np.nan, 40.0], [29.5, 60.0]])
    monkeypatch.setitem(s6.CONFIG, "rotation_method", method)
    rects = s6.create_rectangles_for_frame(pts, edge, mask)
    assert len(rects) == 3
    assert not rects[1]["accepted"] and rects[1]["coverage"] == 0.0 and len(rects[1]["pixels"]) == 0
    if method in ("vertical", "flip", "search"):  # 'none' keeps the edge normal, which this straight edge leaves ambiguous
        assert rects[0]["accepted"] and rects[2]["accepted"]
