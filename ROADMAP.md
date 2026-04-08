# Cell Edge Analysis (Individual Scripts) -- Roadmap

## Current State
A 9-step Python pipeline analyzing PIEZO1 protein localization and cell edge dynamics. Each step is a standalone script (`step1_data_loading.py` through `step9_correlation_analysis.py`) with CLI arguments. Includes batch processing (`run_all_steps.py`), a Tkinter GUI (`cell_edge_analysis_gui.py`), and result summarization tools. Well-documented with detailed README. Data passes between steps via `.npy` and `.pkl` files.

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
- [ ] GUI in `cell_edge_analysis_gui.py` likely duplicates pipeline logic from step scripts
