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
| `config.py` | **Single source** of pipeline defaults (`PIPELINE_CONFIG`, used by `run_all_steps.py` and the GUI; step scripts' CONFIG must match) and the GUI/web `NORMALIZATION_PRESETS` |
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
| `tests/test_intensity_labels.py` | Axis-label builder |
| `tests/test_defaults_single_source.py` | Step scripts, run_all_steps and GUI share config.py's defaults |
| `tests/test_script_paths.py`, `test_summarize_batch.py`, `test_step6_nan_points.py`, `test_rotation_search_ties.py` | Regression tests for fixed bugs |
| `tests/test_web.py` | Web API, static build, node tests of the JS ports (the CI suite) |
| `tests/test_web_fixture.py` | JS-vs-Python fixture and demo data are current (skipped when `CI` is set) |

## Fluorescence edge experiments (`fluorescence_edge_experiments/`, exploratory)

| File | Purpose |
|------|---------|
| `edge_methods.py` | Seven candidate edge detectors `fn(image, mask) -> y(x)` (`METHODS`), helpers |
| `detector.py` | Tuned DIC-banded blurred-blob detector `fluor_edge` (`BEST` params) |
| `run_experiments.py` | Method comparison figures + `gap_between` QC metric |
| `labeling/` | Hand-labelling app (`label_app.py`, `label_io.py`), labels |
| `tuning/tune_blob.py` | Parameter sweep vs labels (`frame_error`), RESULTS.md |
| `review/` | Run the detector over a stack and review it |

## Web interface (`web/`, `python run_web.py`, port 8173)

| File | Purpose |
|------|---------|
| `run_web.py` | Starts the FastAPI app on 127.0.0.1:8173 |
| `web/app.py` | Routes: GET `/api/info`, `/api/guide`, `/api/methods` (exported to the static site via `STATIC_ENDPOINTS`); POST `/api/tiff`, `/api/analyse`, `/api/fluor` (local app only) |
| `web/analysis.py` | Runs the step 1/2/5/6/7 functions (with normalisation + statistic options) on in-memory stacks |
| `web/fluor.py` | Runs `detector.fluor_edge`, `edge_methods`, `gap_between`, `frame_error` on in-memory stacks |
| `web/guide.py` | `gui_help_content.HELP_SECTIONS` for the Guide page |
| `web/tiff_io.py` | tifffile reader + pixel size from the file |
| `web/static/edge_engine.js`, `contours.js` | JS port of steps 2, 5, 6 (shared with the sibling repo) |
| `web/static/intensity_engine.js` | JS port of step 1 normalisation, step 7 statistic, intensity labels |
| `web/static/fluor_engine.js` | JS port of `detector.fluor_edge` and the scipy/skimage calls it uses |
| `web/static/*.test.mjs`, `testkit.mjs` | Node tests against `tests/fixtures/web_fixture.json` |
| `web/static/intensity.js`, `edges.js`, `edges_methods.js`, `guide.js`, `home.js`, `about.js` | Pages |
| `web/static/stack_io.js`, `plots.js`, `tiff.js`, `core.js`, `main.js`, `static_api.js` | Loading, drawing, router, static-site API |
| `web/static/demo/` | SYNTHETIC labelled demo (from `scripts/make_demo_data.py`) |
| `scripts/make_demo_data.py`, `make_web_fixture.py` | Demo data and JS-vs-Python fixture |
| `scripts/build_static.py`, `screenshots.py` | Static site export (Pages workflow), smoke test + README images |

## Data Flow

```
step1 --> step2 --> step3 --> step4 --> step8 --> step9
                         \-> step5 --> step6 --> step7 --/
```

Each step reads `.pkl`/`.npy` files from previous step directories and
writes results to its own `step{N}_results/` directory.
