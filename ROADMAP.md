# Cell Edge Analysis (Individual Scripts) -- Roadmap

## Current State
A 9-step Python pipeline analyzing PIEZO1 protein localization and cell edge dynamics. Each step is a standalone script (`step1_data_loading.py` through `step9_correlation_analysis.py`) with CLI arguments. Includes batch processing (`run_all_steps.py`), a Tkinter GUI (`cell_edge_analysis_gui.py`), and result summarization tools. Well-documented with detailed README. Data passes between steps via `.npy` and `.pkl` files.

## Recently Completed (2026-06-30)
- [x] Configurable intensity **normalization** (step 1): reference `max`/`percentile`, region `frame`/`mask`, scope `per_frame`/`global` — exposed on CLI, in `PIPELINE_CONFIG`, and in the GUI, with a one-click **Robust preset**.
- [x] Configurable per-rectangle **intensity statistic** (step 7): `mean`/`max`/`percentile`.
- [x] **Self-describing plot labels** threaded step7→8→9 (`intensity_labels.py`), so every intensity axis states the normalization + statistic used.
- [x] GUI **Help → Analysis Guide** (per-step math, defaults, conventions), **tooltips**, and normalization **presets** (`gui_help_content.py`, `gui_help.py`, `gui_tooltips.py`).
- [x] Docs updated: README, INTERFACE, GUI_USER_GUIDE, QUICK_REFERENCE, SESSION_LOG.

## Short-term Improvements
- [x] Add unit tests for individual steps using synthetic test data
- [ ] Standardize error handling across all 9 step scripts (currently inconsistent)
- [x] Add input validation in `step1_data_loading.py` for image dimension mismatches
- [x] Create a shared `config.py` module instead of duplicating `PIPELINE_CONFIG` in `run_all_steps.py`
- [ ] Add type hints to function signatures across all step scripts
- [x] Validate that `movement_threshold` in step4 and step9 stay synchronized

## Feature Enhancements
- [ ] Add a progress dashboard that shows completion status across all 9 steps
- [ ] Implement `step10_visualization_report.py` that generates a combined HTML/PDF report
- [ ] Add support for multiple fluorescence channels (not just PIEZO1)
- [ ] Implement parallel batch processing using multiprocessing for independent datasets
- [ ] Add statistical power analysis to `step9_correlation_analysis.py`
- [ ] Enhance `cell_edge_analysis_gui.py` with real-time preview of intermediate results

## Long-term Vision
- [ ] Refactor into a proper Python package with `pip install` support
- [ ] Convert individual scripts into importable modules with shared base classes
- [ ] Add Nextflow/Snakemake workflow definition for HPC cluster execution
- [ ] Support OME-ZARR format for large-scale datasets
- [ ] Create a web-based dashboard for viewing batch results

## Technical Debt
- [ ] 9 separate scripts with similar boilerplate (argument parsing, directory setup) -- extract to shared utilities
- [ ] `combined_batch_analysis.py` and `summarize_batch_results.py` overlap in functionality
- [x] Intermediate `.pkl` files create implicit coupling between steps -- document the data contract (see INTERFACE.md)
- [ ] `launch_gui.py` is a thin wrapper around `cell_edge_analysis_gui.py` -- consolidate
- [ ] `setup.sh` should be replaced with proper `pyproject.toml` + pip install
- [~] GUI logic duplication: verified NOT duplicated -- `cell_edge_analysis_gui.py` shells out to the step scripts via `subprocess`. Remaining issue is size (~1440 lines): split it (run/setup, viewers, help already extracted) to meet the 500-line guideline. `step9_correlation_analysis.py` (~535) is also over.
