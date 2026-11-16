"""Regression: every entry point uses the same pipeline defaults (config.PIPELINE_CONFIG).

Before the fix run_all_steps.py kept its own copy of PIPELINE_CONFIG (config.py was not imported), the Tk GUI started
with n_points 10 and target_points_displacement 5 (pipeline: 12 and 20), and step 8 run on its own (as the GUI runs it)
used temporal_direction 'past' while run_all_steps.py passed 'future', so the GUI and the batch pipeline gave
different results on the same data.
"""
import importlib
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("MPLBACKEND", "Agg")

from config import PIPELINE_CONFIG  # noqa: E402

STEPS = {"step1": "step1_data_loading", "step2": "step2_edge_detection", "step3": "step3_displacement_calculation",
         "step4": "step4_movement_classification", "step5": "step5_edge_sampling",
         "step6": "step6_sampling_rectangles", "step7": "step7_intensity_extraction",
         "step8": "step8_movement_assignment", "step9": "step9_correlation_analysis"}


@pytest.mark.parametrize("step", list(STEPS))
def test_step_script_config_matches(step):
    cfg = {k.lower(): v for k, v in importlib.import_module(STEPS[step]).CONFIG.items()}
    for key, value in PIPELINE_CONFIG[step].items():
        assert cfg[key] == value, f"{STEPS[step]}.CONFIG[{key!r}] = {cfg[key]!r}, config.py says {value!r}"


def test_run_all_steps_uses_config():
    import run_all_steps
    assert run_all_steps.PIPELINE_CONFIG is PIPELINE_CONFIG


def test_gui_initial_values_match():
    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display for Tk")
    root.withdraw()
    try:
        import cell_edge_analysis_gui as g
        gui = g.AnalysisGUI(root)
        d = PIPELINE_CONFIG
        pairs = {"normalize_frames": "step1", "normalization_scale": "step1", "normalization_method": "step1",
                 "normalization_region": "step1", "normalization_scope": "step1", "subtract_background": "step1",
                 "background_percentile": "step1", "smooth_edges": "step2", "smoothing_sigma": "step2",
                 "min_movement_pixels": "step3", "arrow_scale": "step3", "movement_threshold": "step4",
                 "sampling_method": "step5", "n_points": "step5", "target_points_displacement": "step5",
                 "intensity_statistic": "step7", "intensity_percentile": "step7"}
        for name, step in pairs.items():
            assert getattr(gui, name).get() == d[step][name], name
    finally:
        root.destroy()
