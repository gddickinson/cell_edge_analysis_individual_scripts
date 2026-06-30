#!/usr/bin/env python3
"""
Master Script: Run All Analysis Steps
Executes the complete movement analysis pipeline sequentially.
Supports both single dataset and batch processing of multiple datasets.
"""

import subprocess
import sys
import time
import os
import glob
from pathlib import Path
import argparse

# ============================================================================
# PIPELINE CONFIGURATION
# ============================================================================

PIPELINE_CONFIG = {
    # Data paths (for single dataset mode)
    'DATA_DIR': 'data',
    'RESULTS_DIR': 'results',

    # File pattern matching
    'IMAGE_PATTERNS': ['*piezo1.tif', '*Piezo1.tif', '*PIEZO1.tif'],
    'MASK_PATTERNS': ['*Mask.tif', '*mask.tif', '*MASK.tif'],

    # Step 1: Data Loading
    'step1': {
        'normalize_frames': True,
        'normalization_scale': 100.0,  # Scaling factor after normalization
        'normalization_method': 'max',        # 'max' or 'percentile' (robust to hot pixels)
        'normalization_percentile': 99.9,     # used when normalization_method='percentile'
        'normalization_region': 'frame',      # 'frame' (whole image) or 'mask' (in-cell only)
        'normalization_scope': 'per_frame',   # 'per_frame' or 'global' (one ref for the stack)
        'subtract_background': True,  # Subtract background before normalization
        'background_percentile': 10,  # Percentile for background (0-100)
        'create_verification_figures': True
    },

    # Step 2: Edge Detection
    'step2': {
        'smooth_edges': True,  # Apply Gaussian smoothing to edges
        'smoothing_sigma': 20.0,  # Sigma for Gaussian smoothing (higher = more smoothing)
        'create_verification_figures': True
    },

    # Step 3: Displacement Calculation
    'step3': {
        'min_movement_pixels': 5,
        'arrow_scale': 1,
        'arrow_head_width': 40,
        'arrow_head_length': 15,
        'arrow_point_forward': True,
        'create_verification_figures': True
    },

    # Step 4: Movement Classification
    'step4': {
        'movement_threshold': 5,
        'show_edges': True,
        'show_arrows': True,
        'arrow_scale': 1,
        'arrow_head_width': 20,
        'arrow_head_length': 10,
        'arrow_point_forward': True,
        'create_verification_figures': True
    },

    # Step 5: Edge Sampling
    'step5': {
        'n_points': 12, # for per_frame and fixed_x
        'exclude_endpoints': True,
        'sampling_method': 'displacement_like',  # Options: per_frame, fixed_x, dense, displacement_like
        'target_points_displacement': 20,
        'y_selection': 'uppermost',  # Options: uppermost, lowermost
        'create_verification_figures': True
    },

    # Step 6: Sampling Rectangles
    'step6': {
        'depth': 50,
        'width': 25,
        'min_cell_coverage': 0.8,
        'rotation_method': 'vertical',  # Options: none, flip, search, vertical
        'rotation_search_angles': 18,
        'create_verification_figures': True
    },

    # Step 7: Intensity Extraction
    'step7': {
        'show_edge': True,
        'intensity_statistic': 'mean',   # 'mean', 'max' or 'percentile' per sampling rectangle
        'intensity_percentile': 95,      # used when intensity_statistic='percentile'
        'create_verification_figures': True
    },

    # Step 8: Movement Assignment
    'step8': {
        'temporal_direction': 'future',  # Options: past, future
        'create_verification_figures': True
    },

    # Step 9: Correlation Analysis
    'step9': {
        'binning_method': 'equal_count',  # Options: equal_count, equal_width, dynamic
        'n_bins': 10,
        'min_bin_count': 5,
        'create_verification_figures': True
    }
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def find_files_in_dataset(dataset_dir, patterns):
    """Find files matching any of the given patterns in the dataset directory."""
    for pattern in patterns:
        matches = glob.glob(os.path.join(dataset_dir, pattern))
        if matches:
            return matches[0]  # Return first match
    return None

def discover_datasets(data_dir):
    """
    Discover all dataset directories in the data folder.
    Returns list of (dataset_name, dataset_path, image_file, mask_file) tuples.
    """
    datasets = []

    if not os.path.exists(data_dir):
        print(f"Error: Data directory '{data_dir}' not found!")
        return datasets

    # Find all subdirectories
    subdirs = [d for d in os.listdir(data_dir)
               if os.path.isdir(os.path.join(data_dir, d))]

    for subdir in sorted(subdirs):
        dataset_path = os.path.join(data_dir, subdir)

        # Find image and mask files
        image_file = find_files_in_dataset(dataset_path, PIPELINE_CONFIG['IMAGE_PATTERNS'])
        mask_file = find_files_in_dataset(dataset_path, PIPELINE_CONFIG['MASK_PATTERNS'])

        if image_file and mask_file:
            datasets.append((subdir, dataset_path, image_file, mask_file))
        else:
            print(f"Warning: Skipping '{subdir}' - missing required files")
            if not image_file:
                print(f"  Missing image file (patterns: {PIPELINE_CONFIG['IMAGE_PATTERNS']})")
            if not mask_file:
                print(f"  Missing mask file (patterns: {PIPELINE_CONFIG['MASK_PATTERNS']})")

    return datasets

def build_command_args(step_name, step_config, dataset_output_dir=None, prev_output_dirs=None):
    """Build command-line arguments for a step based on configuration."""
    args = []

    # Add input directories for steps that need them
    if prev_output_dirs:
        if step_name == 'step2' and 'step1' in prev_output_dirs:
            args.extend(['--input-dir', prev_output_dirs['step1']])
        elif step_name == 'step3':
            if 'step1' in prev_output_dirs:
                args.extend(['--input-dir-step1', prev_output_dirs['step1']])
            if 'step2' in prev_output_dirs:
                args.extend(['--input-dir-step2', prev_output_dirs['step2']])
        elif step_name == 'step4':
            if 'step1' in prev_output_dirs:
                args.extend(['--input-dir-step1', prev_output_dirs['step1']])
            if 'step2' in prev_output_dirs:
                args.extend(['--input-dir-step2', prev_output_dirs['step2']])
            if 'step3' in prev_output_dirs:
                args.extend(['--input-dir-step3', prev_output_dirs['step3']])
        elif step_name == 'step5':
            if 'step1' in prev_output_dirs:
                args.extend(['--input-dir-step1', prev_output_dirs['step1']])
            if 'step2' in prev_output_dirs:
                args.extend(['--input-dir-step2', prev_output_dirs['step2']])
        elif step_name == 'step6':
            if 'step1' in prev_output_dirs:
                args.extend(['--input-dir-step1', prev_output_dirs['step1']])
            if 'step2' in prev_output_dirs:
                args.extend(['--input-dir-step2', prev_output_dirs['step2']])
            if 'step5' in prev_output_dirs:
                args.extend(['--input-dir-step5', prev_output_dirs['step5']])
        elif step_name == 'step7':
            if 'step1' in prev_output_dirs:
                args.extend(['--input-dir-step1', prev_output_dirs['step1']])
            if 'step2' in prev_output_dirs:
                args.extend(['--input-dir-step2', prev_output_dirs['step2']])
            if 'step6' in prev_output_dirs:
                args.extend(['--input-dir-step6', prev_output_dirs['step6']])
        elif step_name == 'step8':
            if 'step3' in prev_output_dirs:
                args.extend(['--input-dir-step3', prev_output_dirs['step3']])
            if 'step7' in prev_output_dirs:
                args.extend(['--input-dir-step7', prev_output_dirs['step7']])
        elif step_name == 'step9':
            if 'step4' in prev_output_dirs:
                args.extend(['--input-dir-step4', prev_output_dirs['step4']])
            if 'step8' in prev_output_dirs:
                args.extend(['--input-dir-step8', prev_output_dirs['step8']])

    # Add output directory
    if dataset_output_dir:
        args.extend(['--output-dir', dataset_output_dir])

    # Add step-specific configuration parameters
    for key, value in step_config.items():
        # Convert Python key to command-line argument
        arg_name = '--' + key.replace('_', '-')

        # Handle boolean values
        if isinstance(value, bool):
            args.extend([arg_name, 'true' if value else 'false'])
        # Handle other values
        else:
            args.extend([arg_name, str(value)])

    return args

def run_step(step_num, script_name, description, extra_args=None):
    """Run a single analysis step."""
    print("\n" + "="*70)
    print(f"STEP {step_num}: {description}")
    print("="*70)

    cmd = [sys.executable, script_name]
    if extra_args:
        cmd.extend(extra_args)

    print(f"Executing: {' '.join(cmd)}")
    print("-"*70)

    start_time = time.time()

    try:
        result = subprocess.run(cmd,
                              capture_output=False,
                              text=True,
                              check=True)

        elapsed = time.time() - start_time
        print("-"*70)
        print(f"✓ Step {step_num} completed successfully in {elapsed:.1f} seconds")
        return True

    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        print("-"*70)
        print(f"✗ Step {step_num} FAILED after {elapsed:.1f} seconds")
        print(f"Error: {e}")
        return False

def run_dataset_pipeline(dataset_name, image_file, mask_file, results_base_dir):
    """Run complete pipeline for a single dataset."""
    print("\n" + "="*70)
    print(f"PROCESSING DATASET: {dataset_name}")
    print("="*70)
    print(f"Image file: {image_file}")
    print(f"Mask file:  {mask_file}")
    print(f"Results:    {results_base_dir}")
    print("="*70)

    # Create results directory
    os.makedirs(results_base_dir, exist_ok=True)

    # Track output directories for each step
    output_dirs = {}

    # Define pipeline steps
    steps = [
        (1, 'step1_data_loading.py', 'Data Loading and Initialization', 'step1'),
        (2, 'step2_edge_detection.py', 'Cell Edge Detection', 'step2'),
        (3, 'step3_displacement_calculation.py', 'Vertical Displacement Calculation', 'step3'),
        (4, 'step4_movement_classification.py', 'Movement Classification', 'step4'),
        (5, 'step5_edge_sampling.py', 'Edge Point Sampling', 'step5'),
        (6, 'step6_sampling_rectangles.py', 'Sampling Rectangle Creation', 'step6'),
        (7, 'step7_intensity_extraction.py', 'PIEZO1 Intensity Extraction', 'step7'),
        (8, 'step8_movement_assignment.py', 'Local Movement Assignment', 'step8'),
        (9, 'step9_correlation_analysis.py', 'Correlation Analysis and Summary', 'step9')
    ]

    completed = []
    failed = []

    for step_num, script, description, step_key in steps:
        # Create step output directory
        step_output_dir = os.path.join(results_base_dir, f'{step_key}_results')
        output_dirs[step_key] = step_output_dir

        # Build command arguments
        step_config = PIPELINE_CONFIG.get(step_key, {})
        args = build_command_args(step_key, step_config, step_output_dir, output_dirs)

        # Add image and mask paths for step 1
        if step_key == 'step1':
            args.extend(['--image-stack-path', image_file])
            args.extend(['--mask-stack-path', mask_file])

        # Run the step
        success = run_step(step_num, script, description, args)

        if success:
            completed.append(step_num)
        else:
            failed.append(step_num)
            print(f"\n{'='*70}")
            print(f"DATASET '{dataset_name}' STOPPED: Step {step_num} failed")
            print(f"{'='*70}")
            break

    return completed, failed

def run_batch_mode(data_dir, results_dir):
    """Run pipeline for all datasets in batch mode."""
    print("\n" + "="*70)
    print("BATCH PROCESSING MODE")
    print("="*70)

    # Discover datasets
    datasets = discover_datasets(data_dir)

    if not datasets:
        print(f"\nNo valid datasets found in '{data_dir}'")
        print("Each dataset directory should contain:")
        print(f"  - Image file matching: {PIPELINE_CONFIG['IMAGE_PATTERNS']}")
        print(f"  - Mask file matching: {PIPELINE_CONFIG['MASK_PATTERNS']}")
        return

    print(f"\nFound {len(datasets)} dataset(s):")
    for i, (name, path, img, mask) in enumerate(datasets, 1):
        print(f"  {i}. {name}")

    print("\n" + "="*70)
    response = input(f"Process all {len(datasets)} datasets? [y/N]: ").strip().lower()
    if response not in ['y', 'yes']:
        print("Batch processing cancelled.")
        return

    batch_start = time.time()

    # Process each dataset
    all_results = {}
    for dataset_name, dataset_path, image_file, mask_file in datasets:
        dataset_results_dir = os.path.join(results_dir, dataset_name)
        completed, failed = run_dataset_pipeline(dataset_name, image_file, mask_file, dataset_results_dir)
        all_results[dataset_name] = {'completed': completed, 'failed': failed}

    batch_elapsed = time.time() - batch_start

    # Print batch summary
    print("\n" + "="*70)
    print("BATCH PROCESSING SUMMARY")
    print("="*70)
    print(f"Total execution time: {batch_elapsed/60:.1f} minutes")
    print(f"Datasets processed: {len(datasets)}")
    print()

    successful_datasets = []
    failed_datasets = []

    for dataset_name, results in all_results.items():
        if len(results['completed']) == 9:
            successful_datasets.append(dataset_name)
            print(f"✓ {dataset_name}: All steps completed")
        else:
            failed_datasets.append(dataset_name)
            print(f"✗ {dataset_name}: Failed at step {results['failed'][0] if results['failed'] else 'unknown'}")

    print("\n" + "="*70)
    if failed_datasets:
        print(f"⚠ {len(failed_datasets)}/{len(datasets)} datasets had errors")
        print(f"✓ {len(successful_datasets)}/{len(datasets)} datasets completed successfully")
    else:
        print(f"🎉 ALL {len(datasets)} DATASETS COMPLETED SUCCESSFULLY!")
    print("="*70)

    print(f"\nResults saved to: {results_dir}/")
    print("Directory structure mirrors the data directory.")

def run_single_mode():
    """Run pipeline for a single dataset using default paths."""
    print("\n" + "="*70)
    print("SINGLE DATASET MODE")
    print("="*70)
    print("Running pipeline with default configuration from PIPELINE_CONFIG")
    print("="*70)

    input("\nPress Enter to start the analysis pipeline...")

    pipeline_start = time.time()

    steps = [
        (1, 'step1_data_loading.py', 'Data Loading and Initialization'),
        (2, 'step2_edge_detection.py', 'Cell Edge Detection'),
        (3, 'step3_displacement_calculation.py', 'Vertical Displacement Calculation'),
        (4, 'step4_movement_classification.py', 'Movement Classification'),
        (5, 'step5_edge_sampling.py', 'Edge Point Sampling'),
        (6, 'step6_sampling_rectangles.py', 'Sampling Rectangle Creation'),
        (7, 'step7_intensity_extraction.py', 'PIEZO1 Intensity Extraction'),
        (8, 'step8_movement_assignment.py', 'Local Movement Assignment'),
        (9, 'step9_correlation_analysis.py', 'Correlation Analysis and Summary')
    ]

    completed = []
    failed = []

    for step_num, script, description in steps:
        success = run_step(step_num, script, description)

        if success:
            completed.append(step_num)
        else:
            failed.append(step_num)
            print(f"\n{'='*70}")
            print(f"PIPELINE STOPPED: Step {step_num} failed")
            print(f"{'='*70}")
            break

    pipeline_elapsed = time.time() - pipeline_start

    # Final summary
    print("\n" + "="*70)
    print("PIPELINE EXECUTION SUMMARY")
    print("="*70)
    print(f"Total execution time: {pipeline_elapsed/60:.1f} minutes")
    print(f"Completed steps: {len(completed)}/{len(steps)}")

    if completed:
        print(f"\n✓ Successfully completed steps: {', '.join(map(str, completed))}")

    if failed:
        print(f"\n✗ Failed steps: {', '.join(map(str, failed))}")
        print("\nTo resume, you can run the failed step script individually:")
        for step_num, script, _ in steps:
            if step_num in failed:
                print(f"  python {script}")
    else:
        print("\n" + "="*70)
        print("🎉 ALL STEPS COMPLETED SUCCESSFULLY!")
        print("="*70)
        print_results_summary()

def print_results_summary():
    """Print summary of results locations."""
    print("\nResults are organized in the following directories:")
    print("  step1_results/ - Loaded data")
    print("  step2_results/ - Edge detection")
    print("  step3_results/ - Displacement maps")
    print("  step4_results/ - Movement classification")
    print("  step5_results/ - Edge sampling")
    print("  step6_results/ - Sampling rectangles")
    print("  step7_results/ - Intensity extraction")
    print("  step8_results/ - Combined movement-intensity data")
    print("  step9_results/ - Final correlation analysis")
    print("\nCheck the 'verification_figures' subfolder in each directory")
    print("for detailed visualizations of each step.")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Run cell edge movement analysis pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run single dataset with scripts in current directory (uses config in scripts)
  python run_all_steps.py

  # Run batch processing on all datasets in data/ folder
  python run_all_steps.py --batch

  # Run batch processing with custom data and results directories
  python run_all_steps.py --batch --data-dir /path/to/data --results-dir /path/to/results

  # Run specific dataset from data folder
  python run_all_steps.py --batch --dataset test_1

Configuration:
  Edit PIPELINE_CONFIG at the top of this script to change analysis parameters.
  All parameters will be passed to the individual step scripts via command-line arguments.
        """
    )

    parser.add_argument('--batch', action='store_true',
                       help='Run in batch mode, processing all datasets in data directory')
    parser.add_argument('--data-dir', type=str, default='data',
                       help='Data directory containing dataset subdirectories (default: data)')
    parser.add_argument('--results-dir', type=str, default='results',
                       help='Results directory (default: results)')
    parser.add_argument('--dataset', type=str,
                       help='Process only this specific dataset (requires --batch)')

    args = parser.parse_args()

    # Update config with command-line arguments
    if args.data_dir:
        PIPELINE_CONFIG['DATA_DIR'] = args.data_dir
    if args.results_dir:
        PIPELINE_CONFIG['RESULTS_DIR'] = args.results_dir

    print("\n" + "="*70)
    print("CELL EDGE MOVEMENT ANALYSIS - COMPLETE PIPELINE")
    print("="*70)

    if args.batch:
        if args.dataset:
            # Process single dataset from data directory
            dataset_path = os.path.join(PIPELINE_CONFIG['DATA_DIR'], args.dataset)
            if not os.path.exists(dataset_path):
                print(f"Error: Dataset '{args.dataset}' not found in {PIPELINE_CONFIG['DATA_DIR']}")
                return

            image_file = find_files_in_dataset(dataset_path, PIPELINE_CONFIG['IMAGE_PATTERNS'])
            mask_file = find_files_in_dataset(dataset_path, PIPELINE_CONFIG['MASK_PATTERNS'])

            if not image_file or not mask_file:
                print(f"Error: Required files not found in {dataset_path}")
                return

            results_dir = os.path.join(PIPELINE_CONFIG['RESULTS_DIR'], args.dataset)
            run_dataset_pipeline(args.dataset, image_file, mask_file, results_dir)
        else:
            # Process all datasets
            run_batch_mode(PIPELINE_CONFIG['DATA_DIR'], PIPELINE_CONFIG['RESULTS_DIR'])
    else:
        # Single dataset mode
        run_single_mode()

if __name__ == "__main__":
    main()
