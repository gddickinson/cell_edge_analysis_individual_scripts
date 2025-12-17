# Cell Edge Movement Analysis GUI - User Guide

## Overview

This GUI application provides a user-friendly interface for running and viewing cell edge movement analysis. It supports:

- **Complete workflow execution**: Run all 9 analysis steps with one click
- **Individual step execution**: Run specific steps with custom parameters
- **Interactive results viewer**: Navigate through results frame-by-frame
- **Real-time progress monitoring**: View analysis logs in real-time
- **Statistical summaries**: View comprehensive analysis statistics

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
- Normalize Frames: Scale each frame to its brightest pixel
- Normalization Scale: Multiplier after normalization (default: 100.0)
- Subtract Background: Remove background using percentile method
- Background Percentile: Percentile to use as background (default: 10)

**Step 2 - Edge Detection:**
- Smooth Edges: Apply Gaussian smoothing to detected edges
- Smoothing Sigma: Amount of smoothing (higher = smoother, default: 20.0)

**Step 3 - Displacement Calculation:**
- Min Movement Pixels: Minimum valid displacement points required
- Arrow Scale: Scale factor for visualization arrows

**Step 4 - Movement Classification:**
- Movement Threshold: Threshold in pixels to classify as moving (default: 5.0)

**Step 5 - Edge Sampling:**
- Sampling Method: Choose "displacement", "dense", or "per_frame"
- Displacement Threshold: Minimum displacement for sampling
- Number of Samples: Target number of samples per frame

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
   - **Intensity**: PIEZO1 intensity measurements
   - **Correlation**: Intensity vs movement correlation

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

## Understanding the Analysis Workflow

### Step 1: Data Loading
- Loads image and mask stacks
- Optionally subtracts background
- Optionally normalizes frames
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
- Extracts mean PIEZO1 intensity from each rectangle
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
1. Check the Analysis Log for error messages
2. Review verification figures for quality control
3. Verify input files are in correct format
4. Try running individual steps to isolate problems

## Citation

If you use this software in your research, please cite:
[Your citation information here]

## License

[Your license information here]
