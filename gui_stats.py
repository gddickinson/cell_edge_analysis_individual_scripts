"""The Tk GUI statistics tab, frame navigation and the correlation-figure tab.

Mixin of cell_edge_analysis_gui.AnalysisGUI (methods moved verbatim from that file)."""
import os
import tkinter as tk
from tkinter import messagebox
import numpy as np


class StatsMixin:
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

