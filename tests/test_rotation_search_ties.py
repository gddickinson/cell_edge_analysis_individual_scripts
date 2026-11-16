"""Regression: step 6 'search' picks the smallest angle among angles with equal coverage.

The search kept the first strictly larger coverage, so when several angles covered the same pixels (common for a
rectangle well inside the cell) the winner was decided by last-digit rounding of the rotated rectangle's area, which
differs between platforms and between the Python pipeline and the browser. Coverages within COVERAGE_TIE_TOL of the
best now count as ties, and the smallest such angle wins.
"""
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("MPLBACKEND", "Agg")

import step6_sampling_rectangles as s6  # noqa: E402


def test_near_tie_goes_to_smallest_angle(monkeypatch):
    # coverage by angle index (0, 90, 180, 270 deg): indices 1 and 2 tie up to rounding, 2 is larger by 1 ulp-ish
    cov = iter([0.5, 0.9, 0.9 + 4e-16, 0.9 - 4e-16])
    monkeypatch.setattr(s6, "check_cell_coverage", lambda corners, mask: (next(cov), np.empty((0, 2), int)))
    corners, coverage, angle, _ = s6.search_optimal_rotation(np.array([10.0, 10.0]), np.array([1.0, 0.0]), 5, 5,
                                                             np.ones((30, 30)), (30, 30), 4)
    assert angle == 90.0
    assert abs(coverage - 0.9) < 1e-12


def test_clear_winner_still_wins(monkeypatch):
    cov = iter([0.5, 0.7, 0.95, 0.9])
    monkeypatch.setattr(s6, "check_cell_coverage", lambda corners, mask: (next(cov), np.empty((0, 2), int)))
    _, coverage, angle, _ = s6.search_optimal_rotation(np.array([10.0, 10.0]), np.array([1.0, 0.0]), 5, 5,
                                                       np.ones((30, 30)), (30, 30), 4)
    assert angle == 180.0 and coverage == 0.95


def test_no_coverage_returns_none(monkeypatch):
    monkeypatch.setattr(s6, "check_cell_coverage", lambda corners, mask: (0.0, []))
    corners, coverage, angle, _ = s6.search_optimal_rotation(np.array([10.0, 10.0]), np.array([1.0, 0.0]), 5, 5,
                                                             np.ones((30, 30)), (30, 30), 4)
    assert corners is None and coverage == 0.0 and angle == 0.0
