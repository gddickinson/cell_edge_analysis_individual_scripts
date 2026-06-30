# Cell Edge Analysis (Individual Scripts) - Interface Map

## Pipeline Steps

| File | Purpose | Input | Output |
|------|---------|-------|--------|
| `step1_data_loading.py` | Load and validate TIFF stacks, normalize, background subtract | `.tif` files | `step1_results/` (.npy, .json) |
| `step2_edge_detection.py` | Detect cell edges from masks | `step1_results/` | `step2_results/` (.pkl, .npy) |
| `step3_displacement_calculation.py` | Calculate edge displacement between frames | `step2_results/` | `step3_results/` (.pkl, .npy) |
| `step4_movement_classification.py` | Classify frames as extruding/retracting/stable | `step1-3_results/` | `step4_results/` (.pkl) |
| `step5_edge_sampling.py` | Sample points along cell edge | `step2_results/` | `step5_results/` (.pkl) |
| `step6_sampling_rectangles.py` | Generate sampling rectangles at edge points | `step5_results/` | `step6_results/` (.pkl) |
| `step7_intensity_extraction.py` | Extract fluorescence intensities in rectangles | `step1,6_results/` | `step7_results/` (.pkl) |
| `step8_movement_assignment.py` | Combine intensity and movement data | `step4,7_results/` | `step8_results/` (.pkl) |
| `step9_correlation_analysis.py` | Correlation analysis and final plots | `step4,8_results/` | `step9_results/` (.json, .png) |

## Orchestration & Utilities

| File | Purpose |
|------|---------|
| `run_all_steps.py` | Master script: runs all 9 steps sequentially or in batch |
| `config.py` | **Shared** pipeline configuration (centralized `PIPELINE_CONFIG`) |
| `intensity_labels.py` | Builds self-describing intensity axis labels from the normalization (step 1) and per-rectangle statistic (step 7) choices; label is threaded step7→step8→step9 |
| `combined_batch_analysis.py` | Cross-dataset correlation analysis |
| `summarize_batch_results.py` | Summary statistics from batch runs |

## Intensity normalization & aggregation options

The plotted PIEZO1 intensity depends on two independent sets of choices, all
surfaced as CLI args (and in the GUI / `PIPELINE_CONFIG`). Defaults reproduce the
original behaviour exactly.

| Stage | Option | Values (default first) | Effect |
|-------|--------|------------------------|--------|
| step1 | `--normalization-method` | `max`, `percentile` | What value maps to the scale; `percentile` is robust to hot pixels |
| step1 | `--normalization-percentile` | `99.9` | Percentile used when method=`percentile` |
| step1 | `--normalization-region` | `frame`, `mask` | Reference over the whole frame or only in-cell pixels |
| step1 | `--normalization-scope` | `per_frame`, `global` | Per-frame reference, or one stack-wide reference (frame-to-frame consistent) |
| step7 | `--intensity-statistic` | `mean`, `max`, `percentile` | How pixels inside each sampling rectangle are aggregated |
| step7 | `--intensity-percentile` | `95` | Percentile used when statistic=`percentile` |

All figure axis labels/titles (step7, step8, step9, and the GUI) reflect the
chosen options, e.g. `PIEZO1 intensity (mean, % of per-frame max)`.

## GUI

| File | Purpose |
|------|---------|
| `cell_edge_analysis_gui.py` | Tkinter GUI for interactive pipeline execution |
| `launch_gui.py` | Thin launcher with dependency checks |
| `gui_help_content.py` | Help text (one section per step + math, defaults, conventions); pure data |
| `gui_help.py` | Builds the **Help → Analysis Guide** window from `gui_help_content` |
| `gui_tooltips.py` | `ToolTip` hover widget + `TOOLTIPS` text + `attach()` helper used across the GUI |

The GUI has a **Help menu** (Analysis Guide + About), hover **tooltips** on the
main controls, and **Robust / Default normalization preset** buttons on the
Step 1 panel (Robust = percentile 99.9 / in-mask / global).

## Tests

| File | Purpose |
|------|---------|
| `tests/test_config.py` | Configuration validation and threshold sync tests |
| `tests/test_step1.py` | Data loading, validation, and preprocessing tests |
| `tests/test_step2.py` | Edge detection smoke tests |

## Data Flow

```
step1 --> step2 --> step3 --> step4 --> step8 --> step9
                         \-> step5 --> step6 --> step7 --/
```

Each step reads `.pkl`/`.npy` files from previous step directories and
writes results to its own `step{N}_results/` directory.
