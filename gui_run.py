"""Running pipeline steps from the Tk GUI: the step scripts are started with subprocess (resolved next to this file) on a worker thread, with input validation and the log.

Mixin of cell_edge_analysis_gui.AnalysisGUI (methods moved verbatim from that file)."""
import os
import sys
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

# The step scripts live next to this file; resolve them here so the GUI also works from another directory.
SCRIPT_DIR = Path(__file__).resolve().parent


class RunMixin:
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

