"""
Lightweight hover tooltips for the Cell Edge Movement Analysis GUI.

Usage:
    from gui_tooltips import attach
    attach(ttk.Button(parent, text="Run All Steps", command=...), 'run_all').pack()

``attach(widget, key)`` looks ``key`` up in ``TOOLTIPS`` (falling back to using
``key`` verbatim as the text), binds a hover tooltip, and returns the widget so
it can be chained with ``.pack()`` / ``.grid()``.
"""

import tkinter as tk


class ToolTip:
    """A small yellow popup shown after hovering over a widget."""

    def __init__(self, widget, text, delay=500, wraplength=420):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.wraplength = wraplength
        self._after_id = None
        self._tip = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event=None):
        self._cancel()
        self._after_id = self.widget.after(self.delay, self._show)

    def _cancel(self):
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None

    def _show(self):
        if self._tip is not None or not self.text:
            return
        try:
            x = self.widget.winfo_rootx() + 20
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        except tk.TclError:
            return
        self._tip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify="left",
                         background="#ffffe0", relief="solid", borderwidth=1,
                         wraplength=self.wraplength, padx=6, pady=4,
                         font=("TkDefaultFont", 9))
        label.pack()

    def _hide(self, _event=None):
        self._cancel()
        if self._tip is not None:
            try:
                self._tip.destroy()
            except tk.TclError:
                pass
            self._tip = None


# Tooltip text keyed by control. Kept short; the Help -> Analysis Guide has detail.
TOOLTIPS = {
    # File selection
    'image_stack': "Path to the PIEZO1 fluorescence TIFF stack (filename usually contains 'piezo1').",
    'mask_stack': "Path to the binary cell-mask TIFF stack (filename usually contains 'Mask'). Must match the image in size and frame count.",
    'output_dir': "Folder where stepN_results/ subfolders (data, statistics, and verification figures) are written.",
    'browse': "Browse for a file or folder.",
    # Run controls
    'run_all': "Run the full pipeline, step 1 -> 9, with the current settings. The safe choice after changing any parameter.",
    'run_step': "Run only the step selected under 'Configure Step'. Remember to re-run later steps if their inputs changed.",
    'load_results': "Load existing results from the output folder into the viewer tabs without re-running anything.",
    'clear_log': "Clear the analysis log text below.",
    'step_selector': "Pick which step's parameters to edit. Step 1 (normalization) and Step 7 (intensity) have the most options.",
    # Step 1 - normalization
    'normalize_frames': "Rescale intensities so a reference value maps to the scale below. Turn off to keep raw intensities.",
    'normalization_scale': "Value the reference maps to (e.g. 100 -> reference becomes 100, so values read as a percentage of it).",
    'normalization_method': "Reference = 'max' (brightest pixel) or 'percentile' (a high percentile, robust to hot pixels).",
    'normalization_percentile': "Percentile used when method = percentile (e.g. 99.9). Ignored when method = max.",
    'normalization_region': "'frame' uses all pixels; 'mask' uses only in-cell pixels, ignoring bright debris outside the cell.",
    'normalization_scope': "'per_frame' normalizes each frame to itself; 'global' uses one reference for the whole stack (comparable across time).",
    'subtract_background': "Subtract a per-frame background (a low percentile) before normalizing, then clip negatives to 0.",
    'background_percentile': "Percentile used as the background level (e.g. 10). Higher removes more signal.",
    'robust_preset': "Set a robust, time-consistent normalization: percentile 99.9, in-mask, global. Differs numerically from older runs.",
    'default_preset': "Restore the original normalization: max reference, whole frame, per-frame.",
    # Step 7 - intensity
    'intensity_statistic': "How pixels inside each rectangle become one value: mean (average), max (brightest), or percentile.",
    'intensity_percentile': "Percentile used when statistic = percentile (e.g. 95). Ignored otherwise.",
    # Viewer / correlation
    'view_selector': "Choose which intermediate result to display for the current frame.",
    'frame_nav': "Step through frames: |< first, < previous, > next, >| last.",
    'update_view': "Redraw the selected view for the current frame.",
    'correlation_load': "Load step 9 correlation figures from the output folder.",
    'correlation_figure': "Choose which step 9 figure to display (scatter, distributions, summary).",
}


def attach(widget, key):
    """Attach a hover tooltip to ``widget`` and return the widget for chaining."""
    text = TOOLTIPS.get(key, key)
    ToolTip(widget, text)
    return widget
