"""Loading step results into the Tk GUI and switching the results view.

Mixin of cell_edge_analysis_gui.AnalysisGUI (methods moved verbatim from that file)."""
import os
import json
import pickle
from tkinter import messagebox
import numpy as np


class ResultsMixin:
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

