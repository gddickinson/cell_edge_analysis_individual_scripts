# Cell Edge Movement Analysis GUI - User Guide

## Overview

This GUI application provides a user-friendly interface for running and viewing cell edge movement analysis. It supports:

- **Complete workflow execution**: Run all 9 analysis steps with one click
- **Individual step execution**: Run specific steps with custom parameters
- **Interactive results viewer**: Navigate through results frame-by-frame
- **Real-time progress monitoring**: View analysis logs in real-time
- **Statistical summaries**: View comprehensive analysis statistics
- **Built-in Analysis Guide & tooltips**: A Help menu explains every step, the
  math behind it, and the settings; hover tooltips describe each control
- **Normalization presets**: One-click "Robust" vs "Default" intensity normalization

## Installation & Requirements

### Required Python Packages
```bash
pip install numpy matplotlib scipy scikit-image tifffile
```

### Starting the Application
```bash
python cell_edge_analysis_gui.py
```

Or use the launcher:
```bash
python launch_gui.py
```

## Quick Start Guide

### 1. Setup Input Files

**Setup & Run Tab:**
1. Click "Browse" next to "Image Stack" and select your PIEZO1 TIFF file
2. Click "Browse" next to "Mask Stack" and select your cell mask TIFF file
3. Optionally change the output directory (default: `analysis_results`)

### 2. Configure Parameters

1. Use the "Configure Step" dropdown to select which step to configure
2. Adjust parameters as needed for your analysis:

**Step 1 - Data Loading:**
- Normalize Frames: rescale intensities so a reference value maps to the scale
- Normalization Scale: value the reference maps to (default: 100.0)
- Norm. Reference: `max` (brightest pixel) or `percentile` (robust to hot pixels)
- Norm. Percentile: percentile used when reference = percentile (default: 99.9)
- Norm. Region: `frame` (whole image) or `mask` (in-cell pixels only)
- Norm. Scope: `per_frame` (each frame to itself) or `global` (one reference for the stack)
- Subtract Background: remove background using a per-frame percentile
- Background Percentile: percentile used as background (default: 10)
- **Robust preset / Default preset** buttons: one-click switch between a robust
  (percentile / in-mask / global) and the original (max / frame / per_frame)
  normalization — see "Help, Tooltips & Normalization Options" below.

**Step 2 - Edge Detection:**
- Smooth Edges: Apply Gaussian smoothing to detected edges
- Smoothing Sigma: Amount of smoothing (higher = smoother, default: 20.0)

**Step 3 - Displacement Calculation:**
- Min Movement Pixels: Minimum valid displacement points required
- Arrow Scale: Scale factor for visualization arrows

**Step 4 - Movement Classification:**
- Movement Threshold: Threshold in pixels to classify as moving (default: 5.0)

**Step 5 - Edge Sampling:**
- Sampling Method: `displacement_like` (default), `fixed_x`, `dense`, or `per_frame`
- Number of Points: points per frame for `per_frame` / `fixed_x` (default: 12)
- Target Points (displacement): approx points/frame for `displacement_like` (default: 20)

**Step 7 - Intensity Extraction:**
- Intensity Statistic: how each rectangle's pixels become one value —
  `mean` (default), `max` (brightest), or `percentile`
- Intensity Percentile: percentile used when statistic = percentile (default: 95)

### 3. Run Analysis

**Option A - Run Complete Pipeline:**
1. Click "Run All Steps" button
2. Monitor progress in the Analysis Log
3. Wait for completion message

**Option B - Run Individual Steps:**
1. Select the desired step in "Configure Step" dropdown
2. Adjust parameters if needed
3. Click "Run Selected Step"
4. Monitor progress in the Analysis Log

### 4. View Results

After analysis completes, results automatically load. You can also manually load results:

1. Switch to the "Results Viewer" tab
2. Select view type from dropdown:
   - **Overview**: Raw image, mask, and edge overlay
   - **Edge Detection**: Detected cell edges
   - **Displacement**: Displacement maps and statistics
   - **Classification**: Movement type classification
   - **Sampling**: Sampling rectangle locations
   - **Intensity**: PIEZO1 intensity measurements (axis labelled with the
     normalization + statistic used, e.g. "intensity (mean, % of per-frame max)")

   The intensity-vs-movement correlation plots live in their own
   **Correlation Analysis** tab (see below), not in this dropdown.

3. Use navigation buttons to move between frames:
   - **◄◄**: First frame
   - **◄**: Previous frame
   - **►**: Next frame
   - **►►**: Last frame

4. Click "Update View" to refresh visualization

### 5. Review Statistics

Switch to the "Statistics" tab to see:
- Dataset information
- Edge detection statistics
- Displacement statistics
- Movement classification breakdown
- Intensity measurement summaries
- Correlation analysis results

Click "Refresh Statistics" to update after loading new results.

## Help, Tooltips & Normalization Options

### Built-in Analysis Guide (Help menu)
The menu bar has **Help → Analysis Guide…**, which opens a sectioned reference
covering every step: its purpose, the **math** behind it, the **default
settings and why** they were chosen, and how to change them. It also includes a
**Normalization & Intensity Options** section and a **Sign Conventions &
Glossary** (e.g. why a *negative* displacement means the edge moved *up/out* =
extruding). **Help → About** shows version information.

### Tooltips
Hover the mouse over a control — file pickers, run buttons, the "Configure Step"
selector, every Step 1 and Step 7 parameter, the preset buttons, and the viewer
selectors — to see a short explanation of what it does.

### Normalization presets (Step 1 panel)
By default each frame is normalized to its single brightest pixel, so one hot
pixel can set the "100" and push edge values low on the scale (and the reference
varies frame-to-frame). Two buttons switch reference strategy:

- **Robust preset** — `percentile` (99.9), `in-mask`, `global` scope. A stable,
  cell-based reference that is consistent frame-to-frame; recommended when
  comparing intensities across time. Note: numbers differ from default-preset
  runs (not back-comparable), and a few pixels can map slightly above the scale.
- **Default preset** — restores the original `max` / `frame` / `per_frame`.

After changing normalization, re-run **Step 1 onward** (or "Run All Steps").

### Self-describing plot labels
Every intensity axis states exactly what was measured, e.g.
`PIEZO1 intensity (mean, % of per-frame max)` or, with the Robust preset and a
percentile statistic, `PIEZO1 intensity (95th pct, % of stack in-mask 99.9th pct)`.

## Understanding the Analysis Workflow

### Step 1: Data Loading
- Loads image and mask stacks
- Optionally subtracts a per-frame background
- Optionally normalizes frames to a reference value (brightest pixel or a robust
  percentile; whole-frame or in-mask; per-frame or one global reference)
- Saves preprocessed data

### Step 2: Edge Detection
- Detects cell edges from masks
- Optionally applies Gaussian smoothing
- Saves edge coordinates

### Step 3: Displacement Calculation
- Calculates vertical displacement at every x-position
- Computes statistics per frame pair
- Creates displacement maps

### Step 4: Movement Classification
- Classifies each frame pair as:
  - **Extruding**: Edge moving outward (negative displacement)
  - **Retracting**: Edge moving inward (positive displacement)
  - **Stable**: Minimal movement

### Step 5: Edge Sampling
- Selects edge points for intensity sampling
- Multiple sampling methods available
- Filters based on displacement or density

### Step 6: Sampling Rectangles
- Creates rectangular sampling regions at edge points
- Validates regions are within cell
- Prepares for intensity extraction

### Step 7: Intensity Extraction
- Reduces the pixels in each accepted rectangle to one value — `mean` (default),
  `max`, or a `percentile` (set on the Step 7 panel)
- Computes intensity statistics
- Links intensities to edge locations

### Step 8: Movement Assignment
- Assigns movement type to each intensity sample
- Links PIEZO1 intensity to cell edge movement

### Step 9: Correlation Analysis
- Analyzes correlation between intensity and movement
- Groups data by movement type
- Generates statistical summaries

## Tips & Best Practices

### Parameter Optimization

**Edge Smoothing:**
- Start with sigma=20 for typical cell edges
- Increase for very noisy edges (30-40)
- Decrease for fine edge features (10-15)

**Movement Threshold:**
- Default 5 pixels works for most cases
- Increase for faster-moving cells
- Decrease for subtle movements

**Background Subtraction:**
- Use 10th percentile for typical data
- Increase (15-20) for high background
- Decrease (5) for low background

**Normalization reference:**
- The default (brightest-pixel, per-frame) can make edge values look low and
  vary between frames. Click **Robust preset** (percentile / in-mask / global)
  for a stable, time-comparable reference — recommended for new analyses.
- Choose the Step 7 **Intensity Statistic** = `max`/`percentile` if you care
  about bright PIEZO1 puncta rather than the average inside each rectangle.

### Troubleshooting

**"No valid displacements" warnings:**
- Edge detection may be failing
- Try adjusting smoothing parameters
- Check mask quality

**Empty results:**
- Verify input file paths are correct
- Check that TIFF files are readable
- Look for error messages in Analysis Log

**GUI not responding during analysis:**
- This is normal - analysis runs in background
- Monitor progress in Analysis Log
- Wait for completion message

**Verification figures:**
- Each step creates verification figures in subdirectories
- Use these to validate analysis quality
- Located in: `{output_dir}/step{N}_results/verification_figures/`

## Output Structure

```
analysis_results/
├── step1_results/
│   ├── images.npy
│   ├── masks.npy
│   ├── metadata.json
│   └── verification_figures/
├── step2_results/
│   ├── edges.pkl
│   ├── edge_statistics.json
│   └── verification_figures/
├── step3_results/
│   ├── displacement_data.pkl
│   ├── displacement_statistics.json
│   └── verification_figures/
... (continues for all steps)
```

## Advanced Features

### Batch Processing
For processing multiple datasets:
1. Use `combined_batch_analysis.py` script
2. Or run GUI analysis for each dataset sequentially

### Custom Parameters
All parameters can be adjusted via GUI before running each step.

### Result Export
Results are saved in standard formats:
- NumPy arrays (.npy) for images
- Pickle files (.pkl) for complex data structures
- JSON files (.json) for statistics
- PNG images for visualizations

## Keyboard Shortcuts

- **Tab**: Switch between tabs
- **Arrow keys**: Navigate within active control

## Getting Help

If you encounter issues:
1. Open **Help → Analysis Guide…** for step-by-step explanations, the math, and
   the meaning of each setting (and hover any control for a tooltip)
2. Check the Analysis Log for error messages
3. Review verification figures for quality control
4. Verify input files are in correct format
5. Try running individual steps to isolate problems

## Citation

If you use this software in your research, please cite:
[Your citation information here]

## License

[Your license information here]
