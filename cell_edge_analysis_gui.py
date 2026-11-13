#!/usr/bin/env python3
"""
Cell Edge Movement Analysis GUI
User-friendly interface for running and viewing analysis results
"""

import os
import sys
import json
import pickle
import subprocess
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import tifffile

import gui_help
from gui_tooltips import attach

# The step scripts live next to this file; resolve them here so the GUI also works when started from another directory.
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from config import NORMALIZATION_PRESETS, PIPELINE_CONFIG as D  # noqa: E402  (initial widget values: the pipeline's defaults)

class AnalysisGUI:
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

    def create_ui(self):
        """Create the main user interface."""
        # Menu bar (Help menu with the Analysis Guide)
        self.create_menubar()

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)

        # Tab 1: Setup & Run
        self.setup_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.setup_tab, text="Setup & Run")
        self.create_setup_tab()

        # Tab 2: Results Viewer
        self.results_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.results_tab, text="Results Viewer")
        self.create_results_tab()

        # Tab 3: Statistics
        self.stats_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.stats_tab, text="Statistics")
        self.create_stats_tab()

        # Tab 4: Correlation Analysis
        self.correlation_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.correlation_tab, text="Correlation Analysis")
        self.create_correlation_tab()

    def create_menubar(self):
        """Create the top menu bar with a Help menu."""
        menubar = tk.Menu(self.root)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Analysis Guide (steps & math)...",
                              command=lambda: gui_help.show_help_window(self.root))
        help_menu.add_separator()
        help_menu.add_command(label="About...",
                              command=lambda: gui_help.show_about(self.root))
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    def _apply_preset(self, preset):
        """Set the Step 1 variables named in a config.NORMALIZATION_PRESETS entry."""
        for key, value in preset.items():
            getattr(self, key).set(value)

    def apply_robust_normalization_preset(self):
        """Set a robust, time-consistent normalization (percentile / in-mask / global)."""
        self._apply_preset(NORMALIZATION_PRESETS['robust'])
        self.log("Applied ROBUST normalization preset: percentile 99.9, in-mask, "
                 "global scope. (Re-run Step 1 onward; values are not comparable "
                 "to runs made with the default preset.)")
        # Rebuild Step 1 controls so the comboboxes reflect the new values
        if "Step 1" in self.step_var.get():
            self.create_step1_params()

    def apply_default_normalization_preset(self):
        """Restore the original normalization (max / whole-frame / per-frame)."""
        self._apply_preset(NORMALIZATION_PRESETS['default'])
        self.log("Restored DEFAULT normalization preset: brightest-pixel reference, "
                 "whole frame, per-frame scope.")
        if "Step 1" in self.step_var.get():
            self.create_step1_params()

    def create_setup_tab(self):
        """Create the setup and run tab."""
        # Main container with scrollbar
        canvas = tk.Canvas(self.setup_tab)
        scrollbar = ttk.Scrollbar(self.setup_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # File Selection Section
        file_frame = ttk.LabelFrame(scrollable_frame, text="Input Files", padding=10)
        file_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(file_frame, text="Image Stack:").grid(row=0, column=0, sticky='w', pady=2)
        attach(ttk.Entry(file_frame, textvariable=self.image_stack_path, width=60),
               'image_stack').grid(row=0, column=1, padx=5)
        attach(ttk.Button(file_frame, text="Browse", command=self.browse_image_stack),
               'image_stack').grid(row=0, column=2)

        ttk.Label(file_frame, text="Mask Stack:").grid(row=1, column=0, sticky='w', pady=2)
        attach(ttk.Entry(file_frame, textvariable=self.mask_stack_path, width=60),
               'mask_stack').grid(row=1, column=1, padx=5)
        attach(ttk.Button(file_frame, text="Browse", command=self.browse_mask_stack),
               'mask_stack').grid(row=1, column=2)

        ttk.Label(file_frame, text="Output Directory:").grid(row=2, column=0, sticky='w', pady=2)
        attach(ttk.Entry(file_frame, textvariable=self.output_base_dir, width=60),
               'output_dir').grid(row=2, column=1, padx=5)
        attach(ttk.Button(file_frame, text="Browse", command=self.browse_output_dir),
               'output_dir').grid(row=2, column=2)

        # Parameters Section
        self.create_parameters_section(scrollable_frame)

        # Control Buttons
        control_frame = ttk.Frame(scrollable_frame)
        control_frame.pack(fill='x', padx=10, pady=10)

        attach(ttk.Button(control_frame, text="Run All Steps", command=self.run_all_steps,
                  style='Accent.TButton'), 'run_all').pack(side='left', padx=5)
        attach(ttk.Button(control_frame, text="Run Selected Step", command=self.run_selected_step),
               'run_step').pack(side='left', padx=5)
        attach(ttk.Button(control_frame, text="Load Results", command=self.load_results),
               'load_results').pack(side='left', padx=5)
        attach(ttk.Button(control_frame, text="Clear Log", command=self.clear_log),
               'clear_log').pack(side='left', padx=5)

        # Progress Bar
        self.progress = ttk.Progressbar(scrollable_frame, mode='indeterminate')
        self.progress.pack(fill='x', padx=10, pady=5)

        # Log Output
        log_frame = ttk.LabelFrame(scrollable_frame, text="Analysis Log", padding=10)
        log_frame.pack(fill='both', expand=True, padx=10, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, wrap=tk.WORD)
        self.log_text.pack(fill='both', expand=True)

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def create_parameters_section(self, parent):
        """Create parameter configuration section."""
        params_frame = ttk.LabelFrame(parent, text="Analysis Parameters", padding=10)
        params_frame.pack(fill='x', padx=10, pady=5)

        # Step selector
        step_frame = ttk.Frame(params_frame)
        step_frame.pack(fill='x', pady=5)
        ttk.Label(step_frame, text="Configure Step:").pack(side='left', padx=5)

        self.step_var = tk.StringVar(value="Step 1: Data Loading")
        steps = [
            "Step 1: Data Loading",
            "Step 2: Edge Detection",
            "Step 3: Displacement Calculation",
            "Step 4: Movement Classification",
            "Step 5: Edge Sampling",
            "Step 6: Sampling Rectangles",
            "Step 7: Intensity Extraction",
            "Step 8: Movement Assignment",
            "Step 9: Correlation Analysis"
        ]

        step_combo = ttk.Combobox(step_frame, textvariable=self.step_var, values=steps,
                                 state='readonly', width=40)
        step_combo.pack(side='left', padx=5)
        step_combo.bind('<<ComboboxSelected>>', self.on_step_selected)
        attach(step_combo, 'step_selector')

        # Parameter container
        self.param_container = ttk.Frame(params_frame)
        self.param_container.pack(fill='both', expand=True, pady=5)

        # Initialize with Step 1 parameters
        self.create_step1_params()

    def create_step1_params(self):
        """Create Step 1 parameter controls."""
        self.clear_param_container()
        c = self.param_container

        attach(ttk.Checkbutton(c, text="Normalize Frames", variable=self.normalize_frames),
               'normalize_frames').grid(row=0, column=0, sticky='w', pady=2)

        ttk.Label(c, text="Normalization Scale:").grid(row=1, column=0, sticky='w', pady=2)
        attach(ttk.Entry(c, textvariable=self.normalization_scale, width=15),
               'normalization_scale').grid(row=1, column=1, sticky='w', padx=5)

        ttk.Label(c, text="Norm. Reference:").grid(row=2, column=0, sticky='w', pady=2)
        attach(ttk.Combobox(c, textvariable=self.normalization_method, values=["max", "percentile"],
                            state='readonly', width=13), 'normalization_method').grid(row=2, column=1, sticky='w', padx=5)

        ttk.Label(c, text="Norm. Percentile:").grid(row=3, column=0, sticky='w', pady=2)
        attach(ttk.Entry(c, textvariable=self.normalization_percentile, width=15),
               'normalization_percentile').grid(row=3, column=1, sticky='w', padx=5)

        ttk.Label(c, text="Norm. Region:").grid(row=4, column=0, sticky='w', pady=2)
        attach(ttk.Combobox(c, textvariable=self.normalization_region, values=["frame", "mask"],
                            state='readonly', width=13), 'normalization_region').grid(row=4, column=1, sticky='w', padx=5)

        ttk.Label(c, text="Norm. Scope:").grid(row=5, column=0, sticky='w', pady=2)
        attach(ttk.Combobox(c, textvariable=self.normalization_scope, values=["per_frame", "global"],
                            state='readonly', width=13), 'normalization_scope').grid(row=5, column=1, sticky='w', padx=5)

        attach(ttk.Checkbutton(c, text="Subtract Background", variable=self.subtract_background),
               'subtract_background').grid(row=6, column=0, sticky='w', pady=2)

        ttk.Label(c, text="Background Percentile:").grid(row=7, column=0, sticky='w', pady=2)
        attach(ttk.Entry(c, textvariable=self.background_percentile, width=15),
               'background_percentile').grid(row=7, column=1, sticky='w', padx=5)

        # Normalization presets
        preset_frame = ttk.Frame(c)
        preset_frame.grid(row=8, column=0, columnspan=2, sticky='w', pady=(8, 0))
        attach(ttk.Button(preset_frame, text="Robust preset",
                         command=self.apply_robust_normalization_preset),
               'robust_preset').pack(side='left', padx=(0, 5))
        attach(ttk.Button(preset_frame, text="Default preset",
                         command=self.apply_default_normalization_preset),
               'default_preset').pack(side='left')

        ttk.Label(c, text="Reference = value mapped to the scale (what '100' means). "
                          "See Help -> Analysis Guide.",
                 foreground='gray').grid(row=9, column=0, columnspan=2, sticky='w', pady=(6, 0))

    def create_step2_params(self):
        """Create Step 2 parameter controls."""
        self.clear_param_container()

        # Use pre-initialized variables
        ttk.Checkbutton(self.param_container, text="Smooth Edges",
                       variable=self.smooth_edges).grid(row=0, column=0, sticky='w', pady=2)

        ttk.Label(self.param_container, text="Smoothing Sigma:").grid(row=1, column=0, sticky='w', pady=2)
        ttk.Entry(self.param_container, textvariable=self.smoothing_sigma, width=15).grid(row=1, column=1, sticky='w', padx=5)

    def create_step3_params(self):
        """Create Step 3 parameter controls."""
        self.clear_param_container()

        # Use pre-initialized variables
        ttk.Label(self.param_container, text="Min Movement Pixels:").grid(row=0, column=0, sticky='w', pady=2)
        ttk.Entry(self.param_container, textvariable=self.min_movement_pixels, width=15).grid(row=0, column=1, sticky='w', padx=5)

        ttk.Label(self.param_container, text="Arrow Scale:").grid(row=1, column=0, sticky='w', pady=2)
        ttk.Entry(self.param_container, textvariable=self.arrow_scale, width=15).grid(row=1, column=1, sticky='w', padx=5)

    def create_step4_params(self):
        """Create Step 4 parameter controls."""
        self.clear_param_container()

        # Use pre-initialized variables
        ttk.Label(self.param_container, text="Movement Threshold (pixels):").grid(row=0, column=0, sticky='w', pady=2)
        ttk.Entry(self.param_container, textvariable=self.movement_threshold, width=15).grid(row=0, column=1, sticky='w', padx=5)

    def create_step5_params(self):
        """Create Step 5 parameter controls."""
        self.clear_param_container()

        # Use pre-initialized variables
        ttk.Label(self.param_container, text="Sampling Method:").grid(row=0, column=0, sticky='w', pady=2)
        methods = ["per_frame", "fixed_x", "dense", "displacement_like"]
        ttk.Combobox(self.param_container, textvariable=self.sampling_method, values=methods,
                    state='readonly', width=20).grid(row=0, column=1, sticky='w', padx=5)

        ttk.Label(self.param_container, text="Number of Points:").grid(row=1, column=0, sticky='w', pady=2)
        ttk.Entry(self.param_container, textvariable=self.n_points, width=15).grid(row=1, column=1, sticky='w', padx=5)

        ttk.Label(self.param_container, text="Target Points (displacement):").grid(row=2, column=0, sticky='w', pady=2)
        ttk.Entry(self.param_container, textvariable=self.target_points_displacement, width=15).grid(row=2, column=1, sticky='w', padx=5)

    def create_step7_params(self):
        """Create Step 7 parameter controls."""
        self.clear_param_container()

        ttk.Label(self.param_container, text="Intensity Statistic:").grid(row=0, column=0, sticky='w', pady=2)
        attach(ttk.Combobox(self.param_container, textvariable=self.intensity_statistic,
                    values=["mean", "max", "percentile"], state='readonly', width=20),
               'intensity_statistic').grid(row=0, column=1, sticky='w', padx=5)

        ttk.Label(self.param_container, text="Intensity Percentile:").grid(row=1, column=0, sticky='w', pady=2)
        attach(ttk.Entry(self.param_container, textvariable=self.intensity_percentile, width=15),
               'intensity_percentile').grid(row=1, column=1, sticky='w', padx=5)

        ttk.Label(self.param_container,
                 text="How pixels inside each sampling rectangle are aggregated.",
                 foreground='gray').grid(row=2, column=0, columnspan=2, sticky='w', pady=(6, 0))

    def clear_param_container(self):
        """Clear all widgets from parameter container."""
        for widget in self.param_container.winfo_children():
            widget.destroy()

    def on_step_selected(self, event=None):
        """Handle step selection change."""
        step = self.step_var.get()

        if "Step 1" in step:
            self.create_step1_params()
        elif "Step 2" in step:
            self.create_step2_params()
        elif "Step 3" in step:
            self.create_step3_params()
        elif "Step 4" in step:
            self.create_step4_params()
        elif "Step 5" in step:
            self.create_step5_params()
        elif "Step 7" in step:
            self.create_step7_params()
        else:
            self.clear_param_container()
            ttk.Label(self.param_container, text="No configurable parameters for this step").pack(pady=10)

    def create_results_tab(self):
        """Create the results viewer tab."""
        # Control frame
        control_frame = ttk.Frame(self.results_tab)
        control_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(control_frame, text="View:").pack(side='left', padx=5)

        self.view_var = tk.StringVar(value="Overview")
        views = ["Overview", "Edge Detection", "Displacement", "Classification",
                "Sampling", "Intensity"]
        attach(ttk.Combobox(control_frame, textvariable=self.view_var, values=views,
                    state='readonly', width=20), 'view_selector').pack(side='left', padx=5)
        attach(ttk.Button(control_frame, text="Update View", command=self.update_results_view),
               'update_view').pack(side='left', padx=5)

        # Frame navigation
        nav_frame = ttk.Frame(control_frame)
        nav_frame.pack(side='left', padx=20)

        ttk.Button(nav_frame, text="◄◄", command=self.first_frame, width=4).pack(side='left', padx=2)
        ttk.Button(nav_frame, text="◄", command=self.prev_frame, width=4).pack(side='left', padx=2)

        self.frame_label = ttk.Label(nav_frame, text="Frame: 0 / 0")
        self.frame_label.pack(side='left', padx=10)
        attach(self.frame_label, 'frame_nav')

        ttk.Button(nav_frame, text="►", command=self.next_frame, width=4).pack(side='left', padx=2)
        ttk.Button(nav_frame, text="►►", command=self.last_frame, width=4).pack(side='left', padx=2)

        # Matplotlib figure
        self.fig = Figure(figsize=(12, 8))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.results_tab)
        self.canvas.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=5)

        # Toolbar
        toolbar_frame = ttk.Frame(self.results_tab)
        toolbar_frame.pack(fill='x', padx=10, pady=5)
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.update()

    def create_stats_tab(self):
        """Create the statistics summary tab."""
        # Stats text widget
        self.stats_text = scrolledtext.ScrolledText(self.stats_tab, wrap=tk.WORD, font=('Courier', 10))
        self.stats_text.pack(fill='both', expand=True, padx=10, pady=10)

        # Refresh button
        ttk.Button(self.stats_tab, text="Refresh Statistics",
                  command=self.update_statistics).pack(pady=5)

    def create_correlation_tab(self):
        """Create the correlation analysis tab with final summary plots."""
        # Control frame at top
        control_frame = ttk.Frame(self.correlation_tab)
        control_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(control_frame, text="Correlation Analysis - Final Summary Plots",
                 font=('TkDefaultFont', 12, 'bold')).pack(side='left', padx=5)

        attach(ttk.Button(control_frame, text="Load Correlation Results",
                  command=self.load_correlation_plots), 'correlation_load').pack(side='right', padx=5)

        # Figure selection frame
        fig_frame = ttk.Frame(self.correlation_tab)
        fig_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(fig_frame, text="Select Plot:").pack(side='left', padx=5)
        self.correlation_fig_var = tk.StringVar(value="Scatter Plot")
        fig_options = ["Scatter Plot", "Binned Analysis", "Summary Statistics"]
        attach(ttk.Combobox(fig_frame, textvariable=self.correlation_fig_var, values=fig_options,
                    state='readonly', width=25), 'correlation_figure').pack(side='left', padx=5)
        ttk.Button(fig_frame, text="Update",
                  command=self.update_correlation_view).pack(side='left', padx=5)

        # Matplotlib figure for displaying correlation plots
        self.corr_fig = Figure(figsize=(12, 8))
        self.corr_canvas = FigureCanvasTkAgg(self.corr_fig, self.correlation_tab)
        self.corr_canvas.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=5)

        # Matplotlib toolbar
        toolbar_frame = ttk.Frame(self.correlation_tab)
        toolbar_frame.pack(fill='x', padx=10, pady=2)
        NavigationToolbar2Tk(self.corr_canvas, toolbar_frame)

        # Initialize correlation figure storage
        self.correlation_figures = {}

    # File browser methods
    def browse_image_stack(self):
        filename = filedialog.askopenfilename(
            title="Select Image Stack",
            filetypes=[("TIFF files", "*.tif *.tiff"), ("All files", "*.*")]
        )
        if filename:
            self.image_stack_path.set(filename)

    def browse_mask_stack(self):
        filename = filedialog.askopenfilename(
            title="Select Mask Stack",
            filetypes=[("TIFF files", "*.tif *.tiff"), ("All files", "*.*")]
        )
        if filename:
            self.mask_stack_path.set(filename)

    def browse_output_dir(self):
        dirname = filedialog.askdirectory(title="Select Output Directory")
        if dirname:
            self.output_base_dir.set(dirname)

    # Analysis execution methods
    def run_all_steps(self):
        """Run all analysis steps sequentially."""
        if not self.validate_inputs():
            return

        self.log("=" * 60)
        self.log("Starting full analysis pipeline...")
        self.log("=" * 60)

        # Run in separate thread to keep GUI responsive
        thread = threading.Thread(target=self._run_all_steps_thread)
        thread.daemon = True
        thread.start()

    def _run_all_steps_thread(self):
        """Thread worker for running all steps."""
        self.progress.start()

        try:
            # Create output directories
            os.makedirs(self.output_base_dir.get(), exist_ok=True)

            # Run each step
            steps = [
                ("step1_data_loading.py", "Data Loading"),
                ("step2_edge_detection.py", "Edge Detection"),
                ("step3_displacement_calculation.py", "Displacement Calculation"),
                ("step4_movement_classification.py", "Movement Classification"),
                ("step5_edge_sampling.py", "Edge Sampling"),
                ("step6_sampling_rectangles.py", "Sampling Rectangles"),
                ("step7_intensity_extraction.py", "Intensity Extraction"),
                ("step8_movement_assignment.py", "Movement Assignment"),
                ("step9_correlation_analysis.py", "Correlation Analysis")
            ]

            for script, name in steps:
                self.log(f"\n{'='*60}")
                self.log(f"Running: {name}")
                self.log(f"{'='*60}")

                success = self.run_step(script, name)

                if not success:
                    self.log(f"ERROR: {name} failed!")
                    break

                self.log(f"✓ {name} completed successfully")

            self.log("\n" + "="*60)
            self.log("Analysis pipeline completed!")
            self.log("="*60)

            # Auto-load results
            self.root.after(0, self.load_results)

        except Exception as e:
            self.log(f"ERROR: {str(e)}")
            messagebox.showerror("Error", f"Analysis failed:\n{str(e)}")
        finally:
            self.progress.stop()

    def run_selected_step(self):
        """Run only the selected step."""
        if not self.validate_inputs():
            return

        step = self.step_var.get()
        step_num = int(step.split(":")[0].split()[1])

        script = f"step{step_num}_{step.split(':')[1].strip().lower().replace(' ', '_')}.py"

        self.log(f"\n{'='*60}")
        self.log(f"Running: {step}")
        self.log(f"{'='*60}")

        thread = threading.Thread(target=self._run_step_thread, args=(script, step))
        thread.daemon = True
        thread.start()

    def _run_step_thread(self, script, name):
        """Thread worker for running a single step."""
        self.progress.start()

        try:
            success = self.run_step(script, name)

            if success:
                self.log(f"✓ {name} completed successfully")
                self.root.after(0, self.load_results)
            else:
                self.log(f"ERROR: {name} failed!")

        except Exception as e:
            self.log(f"ERROR: {str(e)}")
            messagebox.showerror("Error", f"Step failed:\n{str(e)}")
        finally:
            self.progress.stop()

    def run_step(self, script, name):
        """Execute a single analysis step."""
        try:
            # Build command with parameters
            cmd = [sys.executable, str(SCRIPT_DIR / script)]

            # Extract step number from script name
            step_num = script.split('step')[1].split('_')[0]
            output_dir = os.path.join(self.output_base_dir.get(), f"step{step_num}_results")

            # Add output directory parameter (all steps support this)
            cmd.extend(['--output-dir', output_dir])

            # Add step-specific parameters
            if "step1" in script:
                # Step 1 needs image and mask paths
                cmd.extend([
                    '--image-stack-path', self.image_stack_path.get(),
                    '--mask-stack-path', self.mask_stack_path.get(),
                    '--normalize-frames', str(self.normalize_frames.get()).lower(),
                    '--normalization-scale', str(self.normalization_scale.get()),
                    '--normalization-method', self.normalization_method.get(),
                    '--normalization-percentile', str(self.normalization_percentile.get()),
                    '--normalization-region', self.normalization_region.get(),
                    '--normalization-scope', self.normalization_scope.get(),
                    '--subtract-background', str(self.subtract_background.get()).lower(),
                    '--background-percentile', str(self.background_percentile.get())
                ])
            elif "step2" in script:
                # Step 2 needs step1 results (uses generic --input-dir)
                input_dir = os.path.join(self.output_base_dir.get(), "step1_results")
                cmd.extend(['--input-dir', input_dir])
                cmd.extend([
                    '--smooth-edges', str(self.smooth_edges.get()).lower(),
                    '--smoothing-sigma', str(self.smoothing_sigma.get())
                ])
            elif "step3" in script:
                # Step 3 needs step1 (images/masks) and step2 (edges)
                input_dir_step1 = os.path.join(self.output_base_dir.get(), "step1_results")
                input_dir_step2 = os.path.join(self.output_base_dir.get(), "step2_results")
                cmd.extend(['--input-dir-step1', input_dir_step1])
                cmd.extend(['--input-dir-step2', input_dir_step2])
                cmd.extend([
                    '--min-movement-pixels', str(self.min_movement_pixels.get()),
                    '--arrow-scale', str(self.arrow_scale.get())
                ])
            elif "step4" in script:
                # Step 4 needs step1 (images), step2 (edges), and step3 (displacement) - multiple inputs!
                input_dir_step1 = os.path.join(self.output_base_dir.get(), "step1_results")
                input_dir_step2 = os.path.join(self.output_base_dir.get(), "step2_results")
                input_dir_step3 = os.path.join(self.output_base_dir.get(), "step3_results")
                cmd.extend(['--input-dir-step1', input_dir_step1])
                cmd.extend(['--input-dir-step2', input_dir_step2])
                cmd.extend(['--input-dir-step3', input_dir_step3])
                cmd.extend([
                    '--movement-threshold', str(self.movement_threshold.get())
                ])
            elif "step5" in script:
                # Step 5 needs multiple input directories
                input_dir_step1 = os.path.join(self.output_base_dir.get(), "step1_results")
                input_dir_step2 = os.path.join(self.output_base_dir.get(), "step2_results")
                cmd.extend(['--input-dir-step1', input_dir_step1])
                cmd.extend(['--input-dir-step2', input_dir_step2])
                cmd.extend([
                    '--sampling-method', self.sampling_method.get(),
                    '--n-points', str(self.n_points.get()),
                    '--target-points-displacement', str(self.target_points_displacement.get())
                ])
            elif "step6" in script:
                # Step 6 needs step1 (images), step2 (edges), and step5 (sampling points)
                input_dir_step1 = os.path.join(self.output_base_dir.get(), "step1_results")
                input_dir_step2 = os.path.join(self.output_base_dir.get(), "step2_results")
                input_dir_step5 = os.path.join(self.output_base_dir.get(), "step5_results")
                cmd.extend(['--input-dir-step1', input_dir_step1])
                cmd.extend(['--input-dir-step2', input_dir_step2])
                cmd.extend(['--input-dir-step5', input_dir_step5])
            elif "step7" in script:
                # Step 7 needs step1 (images), step2 (edges), and step6 (rectangles)
                input_dir_step1 = os.path.join(self.output_base_dir.get(), "step1_results")
                input_dir_step2 = os.path.join(self.output_base_dir.get(), "step2_results")
                input_dir_step6 = os.path.join(self.output_base_dir.get(), "step6_results")
                cmd.extend(['--input-dir-step1', input_dir_step1])
                cmd.extend(['--input-dir-step2', input_dir_step2])
                cmd.extend(['--input-dir-step6', input_dir_step6])
                cmd.extend([
                    '--intensity-statistic', self.intensity_statistic.get(),
                    '--intensity-percentile', str(self.intensity_percentile.get())
                ])
            elif "step8" in script:
                # Step 8 needs step3 (displacement/movement) and step7 (intensities)
                input_dir_step3 = os.path.join(self.output_base_dir.get(), "step3_results")
                input_dir_step7 = os.path.join(self.output_base_dir.get(), "step7_results")
                cmd.extend(['--input-dir-step3', input_dir_step3])
                cmd.extend(['--input-dir-step7', input_dir_step7])
            elif "step9" in script:
                # Step 9 needs step4 (classifications) and step8 (combined data)
                input_dir_step4 = os.path.join(self.output_base_dir.get(), "step4_results")
                input_dir_step8 = os.path.join(self.output_base_dir.get(), "step8_results")
                cmd.extend(['--input-dir-step4', input_dir_step4])
                cmd.extend(['--input-dir-step8', input_dir_step8])

            # Execute the command
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            # Stream output to log
            for line in process.stdout:
                self.log(line.rstrip())

            process.wait()

            return process.returncode == 0

        except Exception as e:
            self.log(f"Exception in run_step: {str(e)}")
            return False

    def validate_inputs(self):
        """Validate that required inputs are provided."""
        if not self.image_stack_path.get():
            messagebox.showerror("Error", "Please select an image stack")
            return False

        if not self.mask_stack_path.get():
            messagebox.showerror("Error", "Please select a mask stack")
            return False

        if not os.path.exists(self.image_stack_path.get()):
            messagebox.showerror("Error", "Image stack file not found")
            return False

        if not os.path.exists(self.mask_stack_path.get()):
            messagebox.showerror("Error", "Mask stack file not found")
            return False

        return True

    def log(self, message):
        """Add message to log output."""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def clear_log(self):
        """Clear the log output."""
        self.log_text.delete(1.0, tk.END)

    # Results loading and viewing methods
    def load_results(self):
        """Load analysis results from output directory."""
        try:
            self.log("\nLoading results...")

            # Use the configured output base directory
            base_dir = self.output_base_dir.get()
            self.log(f"Looking for results in: {base_dir}/")

            # Load Step 1 results
            try:
                step1_dir = os.path.join(base_dir, "step1_results")
                if os.path.exists(step1_dir):
                    self.images = np.load(os.path.join(step1_dir, 'images.npy'))
                    self.masks = np.load(os.path.join(step1_dir, 'masks.npy'))
                    self.total_frames = len(self.images)
                    self.log(f"  ✓ Loaded {self.total_frames} frames")
                else:
                    self.log(f"  ✗ Step 1 results not found at {step1_dir}")
            except Exception as e:
                self.log(f"  ✗ Error loading Step 1: {str(e)}")

            # Load Step 2 results
            try:
                step2_dir = os.path.join(base_dir, "step2_results")
                if os.path.exists(step2_dir):
                    with open(os.path.join(step2_dir, 'edges.pkl'), 'rb') as f:
                        self.edges = pickle.load(f)
                    self.log("  ✓ Loaded edge data")
                else:
                    self.log(f"  ✗ Step 2 results not found at {step2_dir}")
            except Exception as e:
                self.log(f"  ✗ Error loading Step 2: {str(e)}")

            # Load Step 3 results
            try:
                step3_dir = os.path.join(base_dir, "step3_results")
                if os.path.exists(step3_dir):
                    with open(os.path.join(step3_dir, 'displacement_data.pkl'), 'rb') as f:
                        self.displacement_data = pickle.load(f)
                    self.log("  ✓ Loaded displacement data")
                else:
                    self.log(f"  ✗ Step 3 results not found at {step3_dir}")
            except Exception as e:
                self.log(f"  ✗ Error loading Step 3: {str(e)}")

            # Load Step 4 results
            try:
                step4_dir = os.path.join(base_dir, "step4_results")
                if os.path.exists(step4_dir):
                    with open(os.path.join(step4_dir, 'movement_classifications.pkl'), 'rb') as f:
                        self.classifications = pickle.load(f)
                    self.log("  ✓ Loaded movement classifications")
                else:
                    self.log(f"  ✗ Step 4 results not found at {step4_dir}")
            except Exception as e:
                self.log(f"  ✗ Error loading Step 4: {str(e)}")

            # Load Step 6 results
            try:
                step6_dir = os.path.join(base_dir, "step6_results")
                if os.path.exists(step6_dir):
                    with open(os.path.join(step6_dir, 'sampling_rectangles.pkl'), 'rb') as f:
                        self.sampling_rectangles = pickle.load(f)
                    self.log("  ✓ Loaded sampling rectangles")
                else:
                    self.log(f"  Note: Step 6 results not found at {step6_dir}")
            except Exception as e:
                self.log(f"  Note: Error loading Step 6: {str(e)}")

            # Load Step 7 results
            try:
                step7_dir = os.path.join(base_dir, "step7_results")
                if os.path.exists(step7_dir):
                    with open(os.path.join(step7_dir, 'intensity_data.pkl'), 'rb') as f:
                        self.intensity_data = pickle.load(f)
                    self.log("  ✓ Loaded intensity data")
                    # Pick up the intensity axis label (reflects normalization + statistic)
                    try:
                        with open(os.path.join(step7_dir, 'intensity_statistics.json')) as f:
                            self.intensity_label = json.load(f).get(
                                'intensity_label', self.intensity_label)
                    except (FileNotFoundError, json.JSONDecodeError):
                        pass
                else:
                    self.log(f"  Note: Step 7 results not found at {step7_dir}")
            except Exception as e:
                self.log(f"  Note: Error loading Step 7: {str(e)}")

            # Load Step 8 results
            try:
                step8_dir = os.path.join(base_dir, "step8_results")
                if os.path.exists(step8_dir):
                    # Try common filenames for step 8
                    step8_files = [
                        'movement_assignments.pkl',
                        'combined_data.pkl',
                        'assignments.pkl'
                    ]
                    loaded = False
                    for fname in step8_files:
                        fpath = os.path.join(step8_dir, fname)
                        if os.path.exists(fpath):
                            with open(fpath, 'rb') as f:
                                self.movement_assignments = pickle.load(f)
                            self.log(f"  ✓ Loaded movement assignments from {fname}")
                            loaded = True
                            break
                    if not loaded:
                        self.log(f"  Note: Step 8 results directory exists but no data file found")
                else:
                    self.log(f"  Note: Step 8 results not found at {step8_dir}")
            except Exception as e:
                self.log(f"  Note: Error loading Step 8: {str(e)}")

            # Load Step 9 results (optional - mainly for verification)
            try:
                step9_dir = os.path.join(base_dir, "step9_results")
                if os.path.exists(step9_dir):
                    # Try to load correlation pickle file
                    step9_files = [
                        'correlation_results.pkl',
                        'correlation_analysis.pkl',
                        'results.pkl'
                    ]
                    loaded = False
                    for fname in step9_files:
                        fpath = os.path.join(step9_dir, fname)
                        if os.path.exists(fpath):
                            with open(fpath, 'rb') as f:
                                self.correlation_results = pickle.load(f)
                            self.log(f"  ✓ Loaded correlation results from {fname}")
                            loaded = True
                            break

                    # Check if verification figures exist (for Correlation Analysis tab)
                    fig_dir = os.path.join(step9_dir, "verification_figures")
                    if os.path.exists(fig_dir):
                        fig_files = os.listdir(fig_dir)
                        if fig_files:
                            self.log(f"  ✓ Found {len(fig_files)} correlation figures (use Correlation Analysis tab to view)")

                    if not loaded:
                        self.log(f"  Note: Correlation pickle file not found (figures available in Correlation Analysis tab)")
                else:
                    self.log(f"  Note: Step 9 results not found at {step9_dir}")
            except Exception as e:
                self.log(f"  Note: Error loading Step 9: {str(e)}")

            # Check if we loaded minimum required data
            if self.images is None:
                raise Exception("Could not load images from step1_results. Please run analysis first.")

            self.results_loaded = True
            self.current_frame = 0
            self.update_frame_label()
            self.update_results_view()
            self.update_statistics()

            self.log("Results loaded successfully!")
            messagebox.showinfo("Success", "Results loaded successfully!")

        except Exception as e:
            self.log(f"Error loading results: {str(e)}")
            messagebox.showerror("Error", f"Failed to load results:\n{str(e)}")

    def update_results_view(self):
        """Update the results visualization."""
        if not self.results_loaded:
            messagebox.showwarning("Warning", "No results loaded. Please run analysis or load results first.")
            return

        view = self.view_var.get()

        try:
            if view == "Overview":
                self.show_overview()
            elif view == "Edge Detection":
                self.show_edge_detection()
            elif view == "Displacement":
                self.show_displacement()
            elif view == "Classification":
                self.show_classification()
            elif view == "Sampling":
                self.show_sampling()
            elif view == "Intensity":
                self.show_intensity()

            self.canvas.draw()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to update view:\n{str(e)}")

    def show_overview(self):
        """Show overview of current frame."""
        self.fig.clear()

        if self.images is None:
            return

        frame = self.current_frame

        # Create subplots
        if self.edges is not None:
            axes = self.fig.subplots(1, 3)
        else:
            axes = self.fig.subplots(1, 2)

        # Calculate contrast limits
        vmin = np.percentile(self.images[frame], 1)
        vmax = np.percentile(self.images[frame], 99.5)

        # Raw image
        axes[0].imshow(self.images[frame], cmap='gray', vmin=vmin, vmax=vmax)
        axes[0].set_title(f'Frame {frame}: PIEZO1 Image')
        axes[0].axis('off')

        # Mask
        axes[1].imshow(self.masks[frame], cmap='gray')
        axes[1].set_title(f'Frame {frame}: Cell Mask')
        axes[1].axis('off')

        # Edge overlay
        if self.edges is not None and len(axes) > 2:
            axes[2].imshow(self.images[frame], cmap='gray', vmin=vmin, vmax=vmax)
            if len(self.edges[frame]) > 0:
                axes[2].plot(self.edges[frame][:, 1], self.edges[frame][:, 0], 'r-', linewidth=2)
            axes[2].set_title(f'Frame {frame}: Edge Detection')
            axes[2].axis('off')

        self.fig.tight_layout()

    def show_edge_detection(self):
        """Show edge detection results."""
        self.fig.clear()

        if self.edges is None:
            return

        frame = self.current_frame
        axes = self.fig.subplots(1, 2)

        vmin = np.percentile(self.images[frame], 1)
        vmax = np.percentile(self.images[frame], 99.5)

        # Edge on mask
        axes[0].imshow(self.masks[frame], cmap='gray')
        if len(self.edges[frame]) > 0:
            axes[0].plot(self.edges[frame][:, 1], self.edges[frame][:, 0], 'r-', linewidth=2)
        axes[0].set_title(f'Frame {frame}: Edge on Mask ({len(self.edges[frame])} points)')
        axes[0].axis('off')

        # Edge on image
        axes[1].imshow(self.images[frame], cmap='gray', vmin=vmin, vmax=vmax)
        if len(self.edges[frame]) > 0:
            axes[1].plot(self.edges[frame][:, 1], self.edges[frame][:, 0], 'r-', linewidth=2)
        axes[1].set_title(f'Frame {frame}: Edge on Image')
        axes[1].axis('off')

        self.fig.tight_layout()

    def show_displacement(self):
        """Show displacement analysis."""
        self.fig.clear()

        if self.displacement_data is None or self.current_frame >= len(self.displacement_data):
            return

        frame = self.current_frame
        data = self.displacement_data[frame]

        axes = self.fig.subplots(2, 2)

        # Frame pair overlay
        vmin = np.percentile(self.images[frame], 1)
        vmax = np.percentile(self.images[frame], 99.5)

        axes[0, 0].imshow(self.images[frame], cmap='gray', alpha=0.5, vmin=vmin, vmax=vmax)
        if len(self.edges[frame]) > 0:
            axes[0, 0].plot(self.edges[frame][:, 1], self.edges[frame][:, 0], 'b-', linewidth=2, label=f'Frame {frame}')
        if frame + 1 < len(self.edges) and len(self.edges[frame+1]) > 0:
            axes[0, 0].plot(self.edges[frame+1][:, 1], self.edges[frame+1][:, 0], 'r-', linewidth=2, label=f'Frame {frame+1}')
        axes[0, 0].set_title(f'Frame Pair {frame}→{frame+1}')
        axes[0, 0].legend()
        axes[0, 0].axis('off')

        # Displacement map
        x_pos = data['x_positions']
        disp = data['displacements']
        valid_mask = ~np.isnan(disp)

        if np.any(valid_mask):
            scatter = axes[0, 1].scatter(x_pos[valid_mask], disp[valid_mask],
                                        c=disp[valid_mask], cmap='RdBu_r',
                                        vmin=-5, vmax=5, s=20)
            axes[0, 1].axhline(y=0, color='k', linestyle='--', linewidth=1)
            axes[0, 1].set_xlabel('X Position (pixels)')
            axes[0, 1].set_ylabel('Vertical Displacement (pixels)')
            axes[0, 1].set_title(f'Avg: {data["avg_displacement"]:.2f}px')
            self.fig.colorbar(scatter, ax=axes[0, 1], label='Displacement (px)')
            axes[0, 1].grid(True, alpha=0.3)

        # Histogram
        if np.any(valid_mask):
            axes[1, 0].hist(disp[valid_mask], bins=30, edgecolor='black', alpha=0.7)
            axes[1, 0].axvline(x=data['avg_displacement'], color='r', linestyle='--', linewidth=2)
            axes[1, 0].set_xlabel('Displacement (pixels)')
            axes[1, 0].set_ylabel('Count')
            axes[1, 0].set_title('Distribution')
            axes[1, 0].grid(True, alpha=0.3)

        # Statistics
        axes[1, 1].axis('off')
        stats_text = f"Displacement Statistics\n\n"
        stats_text += f"Mean: {data['avg_displacement']:.3f} px\n"
        stats_text += f"Std: {data['std_displacement']:.3f} px\n"
        stats_text += f"Valid points: {data['n_valid']}\n"
        axes[1, 1].text(0.1, 0.5, stats_text, fontsize=12, verticalalignment='center', family='monospace')

        self.fig.tight_layout()

    def show_classification(self):
        """Show movement classification."""
        self.fig.clear()

        if self.classifications is None or self.current_frame >= len(self.classifications):
            return

        frame = self.current_frame
        cls = self.classifications[frame]

        axes = self.fig.subplots(1, 2)

        # Image with classification
        vmin = np.percentile(self.images[frame+1], 1)
        vmax = np.percentile(self.images[frame+1], 99.5)

        axes[0].imshow(self.images[frame+1], cmap='gray', vmin=vmin, vmax=vmax)
        if len(self.edges[frame]) > 0:
            axes[0].plot(self.edges[frame][:, 1], self.edges[frame][:, 0], 'b-', linewidth=2, alpha=0.7)
        if len(self.edges[frame+1]) > 0:
            axes[0].plot(self.edges[frame+1][:, 1], self.edges[frame+1][:, 0], 'r-', linewidth=2, alpha=0.7)
        axes[0].set_title(f'Frame {frame}→{frame+1}')
        axes[0].axis('off')

        # Classification info
        color_map = {'extruding': 'blue', 'retracting': 'red', 'stable': 'gray'}
        color = color_map[cls['movement_type']]

        axes[1].axis('off')
        axes[1].set_xlim(0, 1)
        axes[1].set_ylim(0, 1)

        info_text = f"Movement Type:\n{cls['movement_type'].upper()}\n\n"
        info_text += f"Avg Displacement:\n{cls['avg_displacement']:.3f} px\n\n"
        info_text += f"Std Displacement:\n{cls['std_displacement']:.3f} px\n\n"
        info_text += f"Valid Points: {cls['n_valid']}"

        axes[1].text(0.5, 0.5, info_text, ha='center', va='center', fontsize=14,
                    bbox=dict(boxstyle='round', facecolor=color, alpha=0.3))

        self.fig.tight_layout()

    def show_sampling(self):
        """Show sampling rectangles."""
        self.fig.clear()

        if self.sampling_rectangles is None or self.current_frame >= len(self.sampling_rectangles):
            return

        frame = self.current_frame
        rectangles = self.sampling_rectangles[frame]

        ax = self.fig.add_subplot(111)

        vmin = np.percentile(self.images[frame], 1)
        vmax = np.percentile(self.images[frame], 99.5)

        ax.imshow(self.images[frame], cmap='gray', vmin=vmin, vmax=vmax)

        if len(self.edges[frame]) > 0:
            ax.plot(self.edges[frame][:, 1], self.edges[frame][:, 0], 'r-', linewidth=1.5, alpha=0.6)

        # Draw rectangles
        for rect in rectangles:
            if rect['accepted']:
                corners = rect['corners']
                poly = plt.Polygon(corners[:, [1, 0]], fill=False, edgecolor='lime', linewidth=2)
                ax.add_patch(poly)

        ax.set_title(f'Frame {frame}: Sampling Rectangles ({sum(1 for r in rectangles if r["accepted"])} accepted)')
        ax.axis('off')

        self.fig.tight_layout()

    def show_intensity(self):
        """Show intensity extraction results."""
        self.fig.clear()

        if self.intensity_data is None or self.current_frame >= len(self.intensity_data):
            return

        frame = self.current_frame
        frame_data = self.intensity_data[frame]

        if len(frame_data) == 0:
            return

        axes = self.fig.subplots(1, 2)

        # Image with intensity values
        vmin = np.percentile(self.images[frame], 1)
        vmax = np.percentile(self.images[frame], 99.5)

        axes[0].imshow(self.images[frame], cmap='gray', vmin=vmin, vmax=vmax)

        if len(self.edges[frame]) > 0:
            axes[0].plot(self.edges[frame][:, 1], self.edges[frame][:, 0], 'r-', linewidth=1.5, alpha=0.6)

        # Draw rectangles with intensity colors
        valid_intensities = [p['intensity'] for p in frame_data if p['accepted'] and not np.isnan(p['intensity'])]

        if valid_intensities:
            int_vmin, int_vmax = np.min(valid_intensities), np.max(valid_intensities)

            for j, point_data in enumerate(frame_data):
                if point_data['accepted'] and not np.isnan(point_data['intensity']):
                    rect = self.sampling_rectangles[frame][j]
                    corners = rect['corners']

                    if int_vmax > int_vmin:
                        normalized = (point_data['intensity'] - int_vmin) / (int_vmax - int_vmin)
                    else:
                        normalized = 0.5

                    color = plt.cm.viridis(normalized)
                    poly = plt.Polygon(corners[:, [1, 0]], fill=True, facecolor=color,
                                     edgecolor='white', alpha=0.5, linewidth=1)
                    axes[0].add_patch(poly)

        axes[0].set_title(f'Frame {frame}: Intensity Values')
        axes[0].axis('off')

        # Intensity distribution
        if valid_intensities:
            axes[1].hist(valid_intensities, bins=15, edgecolor='black', alpha=0.7)
            axes[1].axvline(x=np.mean(valid_intensities), color='r', linestyle='--', linewidth=2, label='Mean')
            axes[1].set_xlabel(self.intensity_label)
            axes[1].set_ylabel('Count')
            axes[1].set_title(f'Distribution (Mean: {np.mean(valid_intensities):.1f})')
            axes[1].legend()
            axes[1].grid(True, alpha=0.3)

        self.fig.tight_layout()

    def show_correlation(self):
        """Show correlation analysis results.

        Note: This method is deprecated. Correlation visualization is now
        handled by the dedicated "Correlation Analysis" tab.
        """
        # This method is no longer used - correlation viewing moved to dedicated tab
        return

    def update_statistics(self):
        """Update the statistics display."""
        self.stats_text.delete(1.0, tk.END)

        if not self.results_loaded:
            self.stats_text.insert(tk.END, "No results loaded.\n")
            return

        stats = "="*60 + "\n"
        stats += "ANALYSIS STATISTICS SUMMARY\n"
        stats += "="*60 + "\n\n"

        # Dataset info
        if self.images is not None:
            stats += f"Dataset Information:\n"
            stats += f"  Total frames: {len(self.images)}\n"
            stats += f"  Image size: {self.images.shape[1]} x {self.images.shape[2]}\n"
            stats += f"  Data type: {self.images.dtype}\n\n"

        # Edge detection
        if self.edges is not None:
            edge_points = [len(e) for e in self.edges]
            stats += f"Edge Detection:\n"
            stats += f"  Mean edge points: {np.mean(edge_points):.1f}\n"
            stats += f"  Std edge points: {np.std(edge_points):.1f}\n\n"

        # Displacement
        if self.displacement_data is not None:
            displacements = [d['avg_displacement'] for d in self.displacement_data]
            stats += f"Displacement Analysis:\n"
            stats += f"  Mean displacement: {np.mean(displacements):.3f} px\n"
            stats += f"  Std displacement: {np.std(displacements):.3f} px\n"
            stats += f"  Min displacement: {np.min(displacements):.3f} px\n"
            stats += f"  Max displacement: {np.max(displacements):.3f} px\n\n"

        # Classification
        if self.classifications is not None:
            movement_types = [c['movement_type'] for c in self.classifications]
            extruding = movement_types.count('extruding')
            retracting = movement_types.count('retracting')
            stable = movement_types.count('stable')
            total = len(movement_types)

            stats += f"Movement Classification:\n"
            stats += f"  Extruding: {extruding} ({extruding/total*100:.1f}%)\n"
            stats += f"  Retracting: {retracting} ({retracting/total*100:.1f}%)\n"
            stats += f"  Stable: {stable} ({stable/total*100:.1f}%)\n\n"

        # Intensity
        if self.intensity_data is not None:
            all_intensities = []
            for frame_data in self.intensity_data:
                all_intensities.extend([p['intensity'] for p in frame_data
                                       if p['accepted'] and not np.isnan(p['intensity'])])

            if all_intensities:
                stats += f"Intensity Measurements:\n"
                stats += f"  Total valid: {len(all_intensities)}\n"
                stats += f"  Mean: {np.mean(all_intensities):.1f}\n"
                stats += f"  Std: {np.std(all_intensities):.1f}\n"
                stats += f"  Min: {np.min(all_intensities):.1f}\n"
                stats += f"  Max: {np.max(all_intensities):.1f}\n\n"

        # Correlation
        if self.correlation_results is not None:
            stats += f"Correlation Analysis:\n"
            # Handle new pickle format from step 9
            if 'by_movement_type' in self.correlation_results:
                # New format
                if 'overall' in self.correlation_results:
                    stats += f"  Overall correlation: r={self.correlation_results['overall']['pearson_r']:.4f}\n"
                    stats += f"  R²={self.correlation_results['overall']['r_squared']:.4f}\n"
                    stats += f"  p-value={self.correlation_results['overall']['p_value']:.3e}\n\n"

                for movement_type in ['extruding', 'retracting', 'stable']:
                    data = self.correlation_results['by_movement_type'][movement_type]
                    if data['n'] > 0:
                        stats += f"  {movement_type.capitalize()}:\n"
                        stats += f"    Samples: {data['n']}\n"
                        stats += f"    Mean intensity: {data['mean_intensity']:.1f}\n"
                        stats += f"    Mean displacement: {data['mean_displacement']:.2f} px\n"
            else:
                # Old format (for backward compatibility)
                for movement_type in ['extruding', 'retracting', 'stable']:
                    if movement_type in self.correlation_results:
                        data = self.correlation_results[movement_type]
                        if len(data.get('intensities', [])) > 0:
                            stats += f"  {movement_type.capitalize()}:\n"
                            stats += f"    Samples: {len(data['intensities'])}\n"
                            stats += f"    Mean intensity: {np.mean(data['intensities']):.1f}\n"
                            stats += f"    Mean displacement: {np.mean(data['displacements']):.2f} px\n"

        self.stats_text.insert(tk.END, stats)

    # Frame navigation methods
    def first_frame(self):
        """Go to first frame."""
        self.current_frame = 0
        self.update_frame_label()
        self.update_results_view()

    def prev_frame(self):
        """Go to previous frame."""
        if self.current_frame > 0:
            self.current_frame -= 1
            self.update_frame_label()
            self.update_results_view()

    def next_frame(self):
        """Go to next frame."""
        if self.current_frame < self.total_frames - 1:
            self.current_frame += 1
            self.update_frame_label()
            self.update_results_view()

    def last_frame(self):
        """Go to last frame."""
        self.current_frame = self.total_frames - 1
        self.update_frame_label()
        self.update_results_view()

    def update_frame_label(self):
        """Update frame counter label."""
        self.frame_label.config(text=f"Frame: {self.current_frame} / {self.total_frames - 1}")

    def load_correlation_plots(self):
        """Load the correlation analysis summary figures from step 9."""
        try:
            base_dir = self.output_base_dir.get()
            step9_dir = os.path.join(base_dir, "step9_results", "verification_figures")

            if not os.path.exists(step9_dir):
                messagebox.showinfo("Info",
                    f"Step 9 results not found at:\n{step9_dir}\n\n"
                    "Please run the complete analysis first.\n\n"
                    "The analysis must complete all 9 steps to generate correlation plots.")
                return

            # Load the three summary figures
            # Figure names from step 9: scatter_plot.png, binned_analysis.png, summary_statistics.png
            figure_files = {
                "Scatter Plot": "scatter_plot.png",
                "Binned Analysis": "binned_analysis.png",
                "Summary Statistics": "summary_statistics.png"
            }

            self.correlation_figures = {}
            loaded_count = 0

            for fig_name, filename in figure_files.items():
                fig_path = os.path.join(step9_dir, filename)
                if os.path.exists(fig_path):
                    # Load image using PIL
                    from PIL import Image
                    img = Image.open(fig_path)
                    self.correlation_figures[fig_name] = np.array(img)
                    loaded_count += 1
                else:
                    self.log(f"  Note: {filename} not found")

            if loaded_count > 0:
                self.log(f"Loaded {loaded_count} correlation plot(s) from step 9")
                self.update_correlation_view()
                messagebox.showinfo("Success",
                    f"Loaded {loaded_count} correlation plot(s)\n\n"
                    f"Use the dropdown menu to view different plots:\n"
                    f"• Scatter Plot\n"
                    f"• Binned Analysis\n"
                    f"• Summary Statistics")
            else:
                messagebox.showwarning("Warning",
                    "No correlation plots found in step 9 results.\n\n"
                    "Make sure the complete analysis has been run.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load correlation plots:\n{str(e)}")
            self.log(f"Error loading correlation plots: {str(e)}")

    def update_correlation_view(self):
        """Update the correlation plot display."""
        if not hasattr(self, 'correlation_figures') or not self.correlation_figures:
            self.corr_fig.clear()
            ax = self.corr_fig.add_subplot(111)
            ax.text(0.5, 0.5, 'Click "Load Correlation Results" to view plots',
                   ha='center', va='center', fontsize=14, transform=ax.transAxes)
            ax.axis('off')
            self.corr_canvas.draw()
            return

        selected_fig = self.correlation_fig_var.get()

        if selected_fig not in self.correlation_figures:
            self.corr_fig.clear()
            ax = self.corr_fig.add_subplot(111)
            ax.text(0.5, 0.5, f'Plot "{selected_fig}" not available\n\nAvailable plots:\n' +
                   '\n'.join(self.correlation_figures.keys()),
                   ha='center', va='center', fontsize=12, transform=ax.transAxes)
            ax.axis('off')
            self.corr_canvas.draw()
            return

        # Clear and display the selected figure
        self.corr_fig.clear()
        ax = self.corr_fig.add_subplot(111)
        ax.imshow(self.correlation_figures[selected_fig])
        ax.axis('off')
        self.corr_fig.tight_layout()
        self.corr_canvas.draw()


def main():
    root = tk.Tk()
    app = AnalysisGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
