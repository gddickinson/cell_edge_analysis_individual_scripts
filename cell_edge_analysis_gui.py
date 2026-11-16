#!/usr/bin/env python3
"""
Cell Edge Movement Analysis GUI
User-friendly interface for running and viewing analysis results.

The window is built by mixins (one concern per file): gui_layout (tabs, menus), gui_params (per-step parameter panels,
presets), gui_run (running the step scripts), gui_results (loading results), gui_views (result views), gui_stats
(statistics, frame navigation, correlation figures). Help text: gui_help / gui_help_content; tooltips: gui_tooltips.
"""

import subprocess  # noqa: F401  (gui_run starts the step scripts with it; tests patch it here)
import sys
from pathlib import Path
import tkinter as tk

# The step scripts live next to this file; resolve them here so the GUI also works when started from another directory.
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from config import PIPELINE_CONFIG as D  # noqa: E402  (initial widget values: the pipeline's defaults)
from gui_layout import LayoutMixin  # noqa: E402
from gui_params import ParamsMixin  # noqa: E402
from gui_run import RunMixin  # noqa: E402
from gui_results import ResultsMixin  # noqa: E402
from gui_views import ViewsMixin  # noqa: E402
from gui_stats import StatsMixin  # noqa: E402


class AnalysisGUI(LayoutMixin, ParamsMixin, RunMixin, ResultsMixin, ViewsMixin, StatsMixin):
    """Tk GUI: the setup / results / statistics / correlation tabs. Methods live in the gui_* mixin modules."""

    def __init__(self, root):
        self.root = root
        self.root.title("Cell Edge Movement Analysis")
        self.root.geometry("1400x900")

        # Analysis state
        self.image_stack_path = tk.StringVar()
        self.mask_stack_path = tk.StringVar()
        self.output_base_dir = tk.StringVar(value="analysis_results")
        self.current_step = None
        self.results_loaded = False
        self.current_frame = 0
        self.total_frames = 0

        # Initialize ALL parameter variables (so they exist when running all steps)
        # Step 1 parameters
        self.normalize_frames = tk.BooleanVar(value=D['step1']['normalize_frames'])
        self.normalization_scale = tk.DoubleVar(value=D['step1']['normalization_scale'])
        self.normalization_method = tk.StringVar(value=D['step1']['normalization_method'])
        self.normalization_percentile = tk.DoubleVar(value=D['step1']['normalization_percentile'])
        self.normalization_region = tk.StringVar(value=D['step1']['normalization_region'])
        self.normalization_scope = tk.StringVar(value=D['step1']['normalization_scope'])
        self.subtract_background = tk.BooleanVar(value=D['step1']['subtract_background'])
        self.background_percentile = tk.DoubleVar(value=D['step1']['background_percentile'])

        # Step 2 parameters
        self.smooth_edges = tk.BooleanVar(value=D['step2']['smooth_edges'])
        self.smoothing_sigma = tk.DoubleVar(value=D['step2']['smoothing_sigma'])

        # Step 3 parameters
        self.min_movement_pixels = tk.IntVar(value=D['step3']['min_movement_pixels'])
        self.arrow_scale = tk.DoubleVar(value=D['step3']['arrow_scale'])

        # Step 4 parameters
        self.movement_threshold = tk.DoubleVar(value=D['step4']['movement_threshold'])

        # Step 5 parameters
        self.sampling_method = tk.StringVar(value=D['step5']['sampling_method'])
        self.n_points = tk.IntVar(value=D['step5']['n_points'])
        self.target_points_displacement = tk.IntVar(value=D['step5']['target_points_displacement'])

        # Step 7 parameters
        self.intensity_statistic = tk.StringVar(value=D['step7']['intensity_statistic'])
        self.intensity_percentile = tk.DoubleVar(value=D['step7']['intensity_percentile'])

        # Results data
        self.images = None
        self.masks = None
        self.edges = None
        self.displacement_data = None
        self.classifications = None
        self.sampling_rectangles = None
        self.intensity_data = None
        self.movement_assignments = None
        self.correlation_results = None
        self.intensity_label = "PIEZO1 Intensity"  # Updated from step7 results when loaded

        # Create UI
        self.create_ui()


def main():
    root = tk.Tk()
    app = AnalysisGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
