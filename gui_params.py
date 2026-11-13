"""Per-step parameter panels of the Tk GUI and the Step 1 normalisation presets (config.NORMALIZATION_PRESETS).

Mixin of cell_edge_analysis_gui.AnalysisGUI (methods moved verbatim from that file)."""
from tkinter import ttk
from gui_tooltips import attach
from config import NORMALIZATION_PRESETS


class ParamsMixin:
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

