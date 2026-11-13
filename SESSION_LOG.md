# Session Log — cell_edge_analysis_individual_scripts

## 2026-06-30 — Configurable intensity normalization & aggregation options

**Motivation:** In the GUI's correlation tab, PIEZO1 intensities plotted as ~2–14
despite normalization scale = 100. Diagnosis (confirmed against `data/test_1`
results): not a bug — each frame is normalized so its *single brightest pixel* =
scale, and each rectangle reports its *mean*, so dim edge means land low on the
scale. The behaviour is fragile (one hot pixel sets the ceiling; per-frame
references vary frame-to-frame).

**Added options (defaults reproduce original behaviour exactly):**
- step1 normalization: `--normalization-method` (`max`|`percentile`),
  `--normalization-percentile`, `--normalization-region` (`frame`|`mask`),
  `--normalization-scope` (`per_frame`|`global`).
- step7 aggregation: `--intensity-statistic` (`mean`|`max`|`percentile`),
  `--intensity-percentile`.

**Plot/label updates:** new shared module `intensity_labels.py` builds a
self-describing axis label (e.g. `PIEZO1 intensity (mean, % of per-frame max)`)
from the step1 metadata + step7 statistic. The label is threaded
step7 → step8 → step9 via the per-step JSON result files and used on all
intensity axes/titles. The GUI's Correlation tab renders step9's PNGs, so it
inherits the labels automatically; the GUI Intensity view reads the label from
`step7_results/intensity_statistics.json`.

**Surfaces wired:** individual scripts (CLI), `run_all_steps.py` + `config.py`
(`PIPELINE_CONFIG`), and the GUI (Configure Step → Step 1 / Step 7 controls,
subprocess arg passing, label loading).

**Tests:** added `tests/test_intensity_labels.py` and normalization-option tests
in `tests/test_step1.py`. Full suite: 25 passed. Verified end-to-end on
`data/test_1` (step7 `max` → step8 → step9 scatter renders the new label;
step1 robust percentile/mask/global runs on the real TIFFs).

**Known follow-ups (pre-existing, not addressed here):**
- `config.py` is still not imported by `run_all_steps.py` (duplicate `PIPELINE_CONFIG`).
- `step9_correlation_analysis.py` (535) and `cell_edge_analysis_gui.py` (~1440)
  exceed the 500-line guideline and are candidates for splitting.

## 2026-06-30 — GUI Help menu, tooltips, and Robust normalization preset

**Added:**
- **Robust preset** button on the Step 1 panel (sets percentile 99.9 / in-mask /
  global) + a **Default preset** button to restore the original.
- **Help → Analysis Guide** menu: a sectioned window documenting all 9 steps
  (purpose, the actual math, defaults + reasoning, how to change), plus
  Normalization & Intensity options and a Sign-conventions/Glossary section.
  Content matches the implemented algorithms (verified by reading step1–step9).
- **Hover tooltips** on the main controls (file pickers, run buttons, step
  selector, all Step 1 + Step 7 params, presets, viewer/correlation selectors).

**New modules (keep GUI logic thin):**
- `gui_help_content.py` — help text (pure data, 341 lines).
- `gui_help.py` — Help window builder (list + text pane).
- `gui_tooltips.py` — `ToolTip` widget, `TOOLTIPS` dict, `attach()` helper.

**Verified:** all files compile; 25 tests pass; headless GUI instantiation smoke
test passes (menubar, tabs, presets toggle the vars, Help window builds, Step 7
params build).

## 2026-06-30 — Documentation refresh

Updated every doc to reflect the new options, GUI Help/tooltips/presets, and
labels:
- `GUI_USER_GUIDE.md` — Step 1/5/7 parameter lists corrected & extended; new
  "Help, Tooltips & Normalization Options" section; workflow + tips updated.
- `QUICK_REFERENCE.txt` — regenerated (aligned boxes) with the new Step 1/7
  options, a normalization explainer, Help/tooltips box, and new CLI flags.
- `ROADMAP.md` — "Recently Completed" entry; corrected the GUI tech-debt note
  (verified it shells out via subprocess, not duplicated logic; size is the real
  issue).
- `README.md` — fixed two dead links (`STEP1/2_ENHANCEMENTS.md`) and corrected
  the example config defaults that contradicted `config.py`
  (normalization_scale 1.0→100.0, smoothing_sigma 2.0→20.0).
- `INTERFACE.md` — already lists the new modules and options.

## 2026-11-12 — Fixes ported from the sibling repo, web interface and static site

**Fixes (each with a failing-first regression test, separate commits):** the same bugs as in the sibling repo
cell_edge_analysis were present here:
- step scripts not found when `run_all_steps.py` / the GUI start from another directory (now resolved next to the file);
- `summarize_batch_results.py` read `correlation_statistics.json`, which no step writes (now `final_analysis_summary.json`);
- step 6 crashed on the `[nan, x]` points `fixed_x` sampling writes (now a rejected rectangle);
- step 6 `search` chose among equal-coverage angles by rounding noise (smallest angle within 1e-9 now wins);
- defaults had drifted: `run_all_steps.py` kept its own `PIPELINE_CONFIG` copy (config.py unused), the GUI started with
  n_points 10 / target_points_displacement 5 (pipeline 12 / 20) and step 8 alone used temporal_direction 'past'
  (pipeline 'future'). `config.py` is now the single source; batch values kept, so batch results are unchanged.
- Docs: README pointed to the never-written step 9 file and to editing run_all_steps.py; CLI help / README gave
  normalization scale 1.0 and smoothing sigma 2.0 (code 100.0 / 20.0).
Verified end-to-end: `run_all_steps.py --batch` on the synthetic demo from another directory, all 9 steps, and the summary.

**Web interface** (`web/`, `python run_web.py`, port 8173) and static GitHub Pages site (`.github/workflows/pages.yml`),
focused on what this repo adds over the sibling (whose site has the full step 1-7 analyser and is linked):
Intensity scale (step 1 normalisation + step 7 statistic vs defaults), Fluorescence edge (tuned detector on every
frame, gap, errors vs labels; seven methods from Python), Guide (GUI help text), About. JS ports
(`intensity_engine.js`, `fluor_engine.js`, + `edge_engine.js`/`contours.js` from the sibling) agree with the Python
on the fixture (node tests: 6822 and 8541 checks). The normalisation presets moved to `config.NORMALIZATION_PRESETS`
(the GUI's preset buttons use them). Demo data are synthetic (`scripts/make_demo_data.py`); the 2 GB `data/` and the
real `labeled_mask.tif` are not used by the site.
