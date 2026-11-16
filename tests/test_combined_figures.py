"""Regression: combined_batch_analysis.py draws its verification figures with current matplotlib.

The movement box plot passed boxplot(labels=...), a keyword matplotlib renamed to tick_labels in 3.9 and has since
removed, so `python combined_batch_analysis.py` crashed with "TypeError: Axes.boxplot() got an unexpected keyword
argument 'labels'" after writing its JSON results (step 9 already used tick_labels).
"""
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("MPLBACKEND", "Agg")

import combined_batch_analysis as cba  # noqa: E402


def test_verification_figures_are_written(tmp_path):
    rng = np.random.default_rng(1)
    pts = [{"displacement": float(d), "intensity": float(10 + 0.3 * d + rng.normal()), "valid": True,
            "dataset": "A" if i % 2 else "B"} for i, d in enumerate(rng.normal(0, 8, 300))]
    corr = cba.perform_correlation_analysis(pts)
    binned = cba.perform_binned_analysis(pts)
    cba.create_verification_figures(pts, corr, binned, [("A", "", ""), ("B", "", "")], str(tmp_path))
    pngs = sorted(p.name for p in (tmp_path / "verification_figures").glob("*.png"))
    assert len(pngs) == 4, pngs
