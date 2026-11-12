"""
Help content for the Cell Edge Movement Analysis GUI.

Pure data module: ``HELP_SECTIONS`` is an ordered list of ``(title, body)``
tuples rendered by ``gui_help.show_help_window``. Kept separate from the GUI so
the (large) explanatory text does not bloat the GUI module. Edit the prose here;
the window layout lives in ``gui_help.py``.

The descriptions below match the algorithms implemented in step1..step9 and the
defaults in ``config.py`` / ``run_all_steps.py``.
"""

_OVERVIEW = """\
WHAT THIS PIPELINE MEASURES
===========================
It quantifies the relationship between cell-edge MOVEMENT and PIEZO1
fluorescence INTENSITY at the edge. The headline result (step 9) is a Pearson
correlation between local edge displacement and local PIEZO1 intensity, plus a
comparison of intensity between extruding vs. retracting edge regions.

INPUT
  Two aligned TIFF stacks per dataset, same height/width/frame-count:
    * a PIEZO1 fluorescence stack  (filename contains 'piezo1')
    * a binary cell Mask stack     (filename contains 'Mask')

DATA FLOW (each step writes a folder the next one reads)
    step1 -> step2 -> step3 -> step4 -\\
                          \\-> step5 -> step6 -> step7 -> step8 -> step9
  step1 load/normalize | step2 edges | step3 displacement | step4 classify
  step5 sample points  | step6 rectangles | step7 intensity
  step8 pair movement+intensity | step9 correlation & plots

RUNNING FROM THIS GUI
  1. Setup & Run tab: pick the PIEZO1 image, the Mask, and an output folder.
  2. Choose parameters under "Configure Step" (Step 1 and Step 7 have options;
     use the Robust preset on Step 1 for a more artifact-resistant default).
  3. "Run All Steps" runs 1->9; "Run Selected Step" re-runs just one (and the
     steps after it must be re-run too if their inputs changed).
  4. Results load automatically; browse them in Results Viewer / Statistics /
     Correlation Analysis.

WHERE RESULTS GO
  <output folder>/stepN_results/ contains the data files, a *_statistics.json,
  and a verification_figures/ subfolder. The key file is
  step9_results/ (correlation result + scatter_plot.png)."""

_STEP1 = """\
STEP 1 - DATA LOADING & PREPROCESSING
=====================================
PURPOSE  Load the stacks, make the mask binary, optionally subtract background,
         optionally normalize intensities, and save images.npy / masks.npy.

MATH
  Background subtraction (per frame, if enabled):
      B = percentile(frame, p)           # p = background percentile
      frame = max(frame - B, 0)          # clip negatives to 0
  Normalization (if enabled):
      R = reference value (see below)
      frame = (frame / R) * scale        # scale maps R -> 'scale' (e.g. 100)
  The reference R is chosen by three independent options:
      method : 'max'        -> brightest single pixel
               'percentile' -> a high percentile (robust to hot pixels)
      region : 'frame'      -> over the whole image
               'mask'       -> only pixels inside the cell mask
      scope  : 'per_frame'  -> each frame uses its own R
               'global'     -> one R for the whole stack (frame-to-frame
                               consistent; the only mode comparable across time)

DEFAULTS & WHY
  normalize = ON, scale = 100, method = max, region = frame, scope = per_frame,
  subtract background = ON, background percentile = 10.
  These reproduce the original behaviour. NOTE the consequence: 'max'/'frame'
  means a single hot pixel sets the 100 ceiling, so edge values can sit low on
  the scale and vary frame-to-frame.

HOW TO CHANGE
  Configure Step -> Step 1. For a robust, time-comparable reference click
  "Robust preset" (percentile 99.9 / in-mask / global). "Default preset"
  restores the original. See the "Normalization & Intensity options" section."""

_STEP2 = """\
STEP 2 - CELL EDGE DETECTION
============================
PURPOSE  Trace the cell boundary from each binary mask.

MATH
  * Marching-squares contour of the mask at the 0.5 iso-level
    (skimage.measure.find_contours). The LONGEST contour is taken as the cell
    edge, stored as an ordered list of (y, x) points.
  * Optional smoothing: a 1-D Gaussian filter is applied along the contour to
    the y and x coordinate sequences separately, with standard deviation
    'smoothing_sigma'. Closed contours use wrap mode; open contours use reflect
    mode with the two endpoints pinned to avoid shrinking artifacts.

DEFAULTS & WHY
  smooth edges = ON, smoothing_sigma = 20.0. Masks are often pixelated/stair-
  stepped; sigma ~20 removes that jitter so the edge normals and displacements
  are stable. Lower sigma (2-5) preserves fine detail; higher over-smooths.

HOW TO CHANGE
  Configure Step -> Step 2 (Smooth Edges, Smoothing Sigma)."""

_STEP3 = """\
STEP 3 - VERTICAL DISPLACEMENT
==============================
PURPOSE  Measure how far the edge moved between consecutive frames, per column.

MATH  For each frame pair (i, i+1) and each integer x across the edge:
      y_prev = uppermost edge y at x in frame i      (min y within 0.5 px)
      y_curr = uppermost edge y at x in frame i+1
      displacement(x) = y_curr - y_prev
  Sign: image rows increase downward, so
      negative = edge moved UP / outward,  positive = moved DOWN / inward.
  avg_displacement = mean over valid x (set to 0 if fewer than
  'min_movement_pixels' valid columns).

LIMITATION  This tracks only VERTICAL motion of the uppermost edge per column
  (not full 2-D optical flow). It suits a roughly horizontal edge moving up/down
  (e.g. a scratch-assay front), which is what the sampling geometry assumes.

DEFAULTS & WHY
  min_movement_pixels = 5: ignore pairs with too few valid columns to be
  meaningful. Arrow_* settings only affect the verification figures.

HOW TO CHANGE
  Configure Step -> Step 3 (Min Movement Pixels)."""

_STEP4 = """\
STEP 4 - MOVEMENT CLASSIFICATION
================================
PURPOSE  Label each frame pair from its average displacement.

MATH  With threshold T = movement_threshold:
      avg < -T  -> 'extruding'   (edge moved up / out)
      avg > +T  -> 'retracting'  (edge moved down / in)
      |avg| <= T -> 'stable'

DEFAULTS & WHY
  movement_threshold = 5 px. Below this, motion is treated as noise/stable.
  This SAME threshold is reused in step 9 to split the scatter into groups, so
  the two MUST use the same value (both default to 5; keep them equal manually).

HOW TO CHANGE
  Configure Step -> Step 4 (Movement Threshold). If you change it, set the same
  value for step 9 and re-run step 4 AND step 9."""

_STEP5 = """\
STEP 5 - EDGE POINT SAMPLING
============================
PURPOSE  Choose the points along the edge where intensity will be measured.

MATH  At each chosen x, pick one edge point by 'y_selection':
      'uppermost' = min y (top of cell)  |  'lowermost' = max y.
  Methods for choosing the x's:
      per_frame        : n_points evenly spaced across each frame's own x-range
      fixed_x          : n_points fixed across ALL frames (common x-overlap =
                         max of mins .. min of maxs) - best for tracking the
                         same columns over time
      dense            : every unique x on the edge
      displacement_like: integer x's (matching step 3), optionally subsampled to
                         ~target_points_displacement points  [DEFAULT]
  'exclude_endpoints' trims a small margin so the noisy contour ends are skipped.

DEFAULTS & WHY
  method = displacement_like, target ~ 20 pts/frame, y_selection = uppermost,
  exclude_endpoints = ON. displacement_like makes the sampled x's line up with
  the displacement columns from step 3, so movement and intensity are measured
  at the same places.

HOW TO CHANGE
  Configure Step -> Step 5 (Sampling Method, Number of Points, Target Points)."""

_STEP6 = """\
STEP 6 - SAMPLING RECTANGLES
============================
PURPOSE  Build a small rectangle at each sampled point, reaching into the cell,
         over which PIEZO1 intensity is averaged.

MATH  Each rectangle is width W (along the edge) x depth D (into the cell):
      corners = point +/- perp*(W/2), and the far edge + normal*D.
  The 'normal' (into-cell direction) depends on rotation_method:
      vertical : normal = straight down (+y); no normal calculation  [DEFAULT]
      none     : local inward normal = perpendicular to the edge tangent
                 (tangent from neighbours +/-2 pts), flipped toward the centroid
      flip     : as 'none', but try a 180 deg flip if coverage is too low
      search   : try 'rotation_search_angles' orientations, keep the best
  Coverage = (rectangle pixels inside the mask) / (theoretical area W*D), via a
  cross-product point-in-polygon test. A rectangle is ACCEPTED only if
  coverage >= min_cell_coverage; rejected ones get no intensity (NaN).

DEFAULTS & WHY
  depth = 50, width = 25, min_cell_coverage = 0.8, rotation_method = vertical.
  'vertical' matches the uppermost-edge / vertical-displacement convention used
  upstream. Deeper/wider rectangles average more pixels (steadier but less
  local). 0.8 coverage keeps rectangles that sit mostly inside the cell.

HOW TO CHANGE
  Edit step6 in PIPELINE_CONFIG / pass --depth, --width, --min-cell-coverage,
  --rotation-method (not exposed as GUI controls yet)."""

_STEP7 = """\
STEP 7 - PIEZO1 INTENSITY EXTRACTION
====================================
PURPOSE  Reduce the pixels inside each accepted rectangle to one number.

MATH  For the pixels inside a rectangle, the reported value is:
      'mean'       -> average intensity                       [DEFAULT]
      'max'        -> brightest pixel (captures puncta)
      'percentile' -> the given percentile (robust 'bright' readout)
  Rejected rectangles (step 6) are recorded as NaN.

WHAT THE NUMBER MEANS
  It inherits step 1's scale. With the default 'max' frame normalization, 100 =
  the brightest pixel in the frame, so mean rectangle values are a small % of
  that. The plot axis is labelled to say exactly what was used, e.g.
  "PIEZO1 intensity (mean, % of per-frame max)".

DEFAULTS & WHY
  statistic = mean (average local intensity). Choose 'max'/'percentile' if you
  care about bright PIEZO1 puncta rather than the average.

HOW TO CHANGE
  Configure Step -> Step 7 (Intensity Statistic, Intensity Percentile)."""

_STEP8 = """\
STEP 8 - MOVEMENT ASSIGNMENT
============================
PURPOSE  Pair each sampled intensity point with a local displacement value.

MATH  For each intensity point, the displacement from step 3 at the nearest x
  is assigned. 'temporal_direction' sets which frame pair is used:
      'past'   : intensity at frame i paired with movement (i-1 -> i)
      'future' : intensity at frame i paired with movement (i -> i+1)
  The output is a list of (displacement, intensity) pairs - the raw material for
  the correlation.

DEFAULTS & WHY
  The default (config.py, used by the batch pipeline and the GUI) is
  temporal_direction = 'future' (does present intensity predict the NEXT move?).
  'past' asks whether intensity followed the last move.
  Configurable via --temporal-direction (not a GUI control)."""

_STEP9 = """\
STEP 9 - CORRELATION ANALYSIS
=============================
PURPOSE  Combine all (displacement, intensity) pairs and test the relationship.

MATH
  * Pearson correlation r and p-value over all valid points; least-squares line
    (slope, intercept); R^2 = r^2.
  * Groups by the SAME threshold T as step 4:
      extruding (disp < -T), retracting (disp > +T), stable (|disp| <= T)
    and compares extruding vs. retracting intensities with a t-test and a
    Mann-Whitney U test.
  The main figure (scatter_plot.png) shows intensity vs. displacement coloured
  by group, the regression line, and per-group box/mean plots. Its y-axis is
  labelled with the exact normalization + statistic used.

DEFAULTS & WHY
  movement_threshold = 5 (must match step 4). n_bins / binning_method exist in
  the config for future binned summaries but the current analysis reports the
  correlation and the group comparisons above.

HOW TO CHANGE
  Configure Step -> (threshold lives on Step 4). Re-run step 9 after changes."""

_NORM_OPTIONS = """\
NORMALIZATION & INTENSITY OPTIONS (and the Robust preset)
=========================================================
WHY VALUES CAN LOOK LOW
  Default normalization divides each frame by its single brightest pixel
  ('max' / 'frame' / 'per_frame') and rectangles report the 'mean'. So:
    * one hot pixel anywhere (even outside the cell) sets the 100 ceiling;
    * dim edge means then land low on the scale (e.g. 2-14, not 0-100);
    * each frame has its own reference, so the same brightness maps to
      different numbers across frames - which can confound an across-time
      correlation.

THE FOUR NORMALIZATION OPTIONS (step 1)
  method   max | percentile     - percentile (e.g. 99.9) ignores hot pixels
  percent  99.9                 - used when method = percentile
  region   frame | mask         - 'mask' ignores bright debris outside the cell
  scope    per_frame | global   - 'global' = one reference for the whole stack,
                                  the only setting comparable frame-to-frame
  PLUS the per-rectangle statistic (step 7): mean | max | percentile.

ROBUST PRESET (button on the Step 1 panel)
  Sets method=percentile, percentile=99.9, region=mask, scope=global. This gives
  a stable, cell-based, time-consistent reference. Trade-offs:
    * the numbers will differ from older runs (not back-comparable);
    * a few pixels above the percentile map slightly above the scale (no clip).
  "Default preset" restores max / frame / per_frame.

RECOMMENDATION
  Keep defaults to stay comparable with existing results. For NEW analyses where
  you compare intensity across frames/time, prefer the Robust preset and leave
  the statistic = mean unless you specifically want bright puncta."""

_CONVENTIONS = """\
SIGN CONVENTIONS & GLOSSARY
===========================
COORDINATES  Points are (y, x) = (row, col). Image rows increase DOWNWARD, so
  smaller y is higher on screen ('uppermost' = top of the cell).

DISPLACEMENT SIGN
  displacement = y_current - y_previous
    negative -> edge moved UP / outward   -> EXTRUDING
    positive -> edge moved DOWN / inward   -> RETRACTING
    near zero (|avg| <= threshold)         -> STABLE

GLOSSARY
  Edge / contour : ordered boundary points of the cell mask.
  Normal         : direction perpendicular to the edge, pointing into the cell.
  Coverage       : fraction of a sampling rectangle lying inside the mask.
  Reference (R)  : the intensity value mapped to the normalization scale.
  Statistic      : how a rectangle's pixels are reduced to one number.
  Pearson r      : linear correlation in [-1, 1]; p-value = significance.

RE-RUN RULE  If you change a step's settings, re-run that step AND every step
  after it (their inputs changed). 'Run All Steps' is the safe option."""

HELP_SECTIONS = [
    ("Overview & Pipeline", _OVERVIEW),
    ("Step 1 - Loading & Preprocessing", _STEP1),
    ("Step 2 - Edge Detection", _STEP2),
    ("Step 3 - Displacement", _STEP3),
    ("Step 4 - Classification", _STEP4),
    ("Step 5 - Edge Sampling", _STEP5),
    ("Step 6 - Sampling Rectangles", _STEP6),
    ("Step 7 - Intensity Extraction", _STEP7),
    ("Step 8 - Movement Assignment", _STEP8),
    ("Step 9 - Correlation Analysis", _STEP9),
    ("Normalization & Intensity Options", _NORM_OPTIONS),
    ("Sign Conventions & Glossary", _CONVENTIONS),
]

ABOUT_TEXT = (
    "Cell Edge Movement Analysis\n\n"
    "A 9-step pipeline relating cell-edge movement to PIEZO1 intensity.\n"
    "Use Help -> Analysis Guide for the math and settings behind each step.\n\n"
    "Built with assistance from Claude (Anthropic)."
)
