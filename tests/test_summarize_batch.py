"""Regression: summarize_batch_results.py reads the correlation that step 9 actually writes.

Step 9 saves step9_results/final_analysis_summary.json (correlation_analysis.overall.pearson_r, ...); the summary
script looked only for step9_results/correlation_statistics.json, which no step writes, so every dataset showed
"N Points 0, Pearson r N/A".
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import summarize_batch_results as sbr  # noqa: E402


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def test_reads_step9_final_summary(tmp_path):
    _write(tmp_path / "ds" / "step9_results" / "final_analysis_summary.json", {
        "correlation_analysis": {"n_points": 95, "overall": {"pearson_r": 0.25, "r_squared": 0.0625, "p_value": 0.01}},
        "data_summary": {"total_valid_points": 95}})
    s = sbr.load_statistics(str(tmp_path), "ds")
    assert s["correlation_coefficient"] == 0.25
    assert s["r_squared"] == 0.0625 and s["p_value"] == 0.01 and s["n_points"] == 95


def test_legacy_correlation_statistics_still_read(tmp_path):
    _write(tmp_path / "ds" / "step9_results" / "correlation_statistics.json",
           {"correlation_coefficient": 0.5, "p_value": 0.2, "r_squared": 0.25, "total_valid_points": 7})
    s = sbr.load_statistics(str(tmp_path), "ds")
    assert s["correlation_coefficient"] == 0.5 and s["n_points"] == 7
