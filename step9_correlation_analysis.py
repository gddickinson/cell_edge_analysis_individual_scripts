#!/usr/bin/env python3
"""
Step 9: Correlation Analysis and Final Summary
Performs comprehensive correlation analysis and creates final summary plots.
Saves to step9_results/
"""

import os
import sys
import argparse
import numpy as np
import pickle
import json
from scipy import stats

from intensity_labels import load_intensity_label, DEFAULT_LABEL
import step9_figures  # verification figures (split out to keep this file under 500 lines)

# Configuration
CONFIG = {
    'INPUT_DIR_STEP4': "step4_results",
    'INPUT_DIR_STEP8': "step8_results",
    'OUTPUT_DIR': "step9_results",
    'binning_method': 'equal_count',
    'n_bins': 10,
    'min_bin_count': 5,
    'movement_threshold': 5,  # Threshold for separating extruding vs retracting
    'CREATE_VERIFICATION_FIGURES': True  # Create verification figures
}

def load_previous_results():
    """Load data from previous steps."""
    print("Loading previous results...")

    with open(os.path.join(CONFIG['INPUT_DIR_STEP4'], 'movement_classifications.pkl'), 'rb') as f:
        classifications = pickle.load(f)

    with open(os.path.join(CONFIG['INPUT_DIR_STEP8'], 'combined_data.pkl'), 'rb') as f:
        combined_data = pickle.load(f)

    return classifications, combined_data


def parse_arguments():
    """Parse command line arguments to override CONFIG."""
    parser = argparse.ArgumentParser(description='Step 9: Correlation Analysis')

    parser.add_argument('--input-dir-step4', type=str,
                        help='Input directory from step 4')
    parser.add_argument('--input-dir-step8', type=str,
                        help='Input directory from step 8')
    parser.add_argument('--output-dir', type=str,
                        help='Output directory for results')
    parser.add_argument('--binning-method', type=str,
                        choices=['equal_count', 'equal_width', 'dynamic'],
                        help='Binning method')
    parser.add_argument('--n-bins', type=int,
                        help='Number of bins')
    parser.add_argument('--min-bin-count', type=int,
                        help='Minimum count per bin')
    parser.add_argument('--movement-threshold', type=float,
                        help='Threshold for separating extruding vs retracting (pixels)')
    parser.add_argument('--create-verification-figures', type=lambda x: x.lower() == 'true',
                        help='Create verification figures (true/false)')

    args = parser.parse_args()

    # Override CONFIG with command line arguments
    if args.input_dir_step4 is not None:
        CONFIG['INPUT_DIR_STEP4'] = args.input_dir_step4
    if args.input_dir_step8 is not None:
        CONFIG['INPUT_DIR_STEP8'] = args.input_dir_step8
    if args.output_dir is not None:
        CONFIG['OUTPUT_DIR'] = args.output_dir
    if args.binning_method is not None:
        CONFIG['binning_method'] = args.binning_method
    if args.n_bins is not None:
        CONFIG['n_bins'] = args.n_bins
    if args.min_bin_count is not None:
        CONFIG['min_bin_count'] = args.min_bin_count
    if args.movement_threshold is not None:
        CONFIG['movement_threshold'] = args.movement_threshold
    if args.create_verification_figures is not None:
        CONFIG['CREATE_VERIFICATION_FIGURES'] = args.create_verification_figures

    return args

def perform_correlation_analysis(combined_data):
    """Perform detailed correlation analysis."""
    print("Performing correlation analysis...")

    # Flatten all valid data
    all_valid = []
    for frame_data in combined_data:
        all_valid.extend([p for p in frame_data if p['valid']])

    if len(all_valid) < 3:
        print("  Insufficient data for correlation analysis")
        return None

    displacements = np.array([p['displacement'] for p in all_valid])
    intensities = np.array([p['intensity'] for p in all_valid])

    # Overall correlation
    r, p_value = stats.pearsonr(displacements, intensities)
    r_squared = r ** 2

    # Linear regression
    slope, intercept, _, _, std_err = stats.linregress(displacements, intensities)

    # Separate by movement type
    extruding_mask = displacements < -CONFIG['movement_threshold']
    retracting_mask = displacements > CONFIG['movement_threshold']
    stable_mask = np.abs(displacements) <= CONFIG['movement_threshold']

    extruding_intensities = intensities[extruding_mask]
    retracting_intensities = intensities[retracting_mask]
    stable_intensities = intensities[stable_mask]

    # Test if extruding vs retracting have different intensities
    if len(extruding_intensities) > 0 and len(retracting_intensities) > 0:
        t_stat, t_pvalue = stats.ttest_ind(extruding_intensities, retracting_intensities)
        mann_whitney_stat, mann_whitney_p = stats.mannwhitneyu(extruding_intensities,
                                                                retracting_intensities,
                                                                alternative='two-sided')
    else:
        t_stat, t_pvalue = np.nan, np.nan
        mann_whitney_stat, mann_whitney_p = np.nan, np.nan

    results = {
        'n_points': len(all_valid),
        'overall': {
            'pearson_r': float(r),
            'r_squared': float(r_squared),
            'p_value': float(p_value),
            'slope': float(slope),
            'intercept': float(intercept),
            'std_err': float(std_err)
        },
        'by_movement_type': {
            'extruding': {
                'n': int(np.sum(extruding_mask)),
                'mean_intensity': float(np.mean(extruding_intensities)) if len(extruding_intensities) > 0 else np.nan,
                'std_intensity': float(np.std(extruding_intensities)) if len(extruding_intensities) > 0 else np.nan,
                'mean_displacement': float(np.mean(displacements[extruding_mask])) if np.sum(extruding_mask) > 0 else np.nan
            },
            'retracting': {
                'n': int(np.sum(retracting_mask)),
                'mean_intensity': float(np.mean(retracting_intensities)) if len(retracting_intensities) > 0 else np.nan,
                'std_intensity': float(np.std(retracting_intensities)) if len(retracting_intensities) > 0 else np.nan,
                'mean_displacement': float(np.mean(displacements[retracting_mask])) if np.sum(retracting_mask) > 0 else np.nan
            },
            'stable': {
                'n': int(np.sum(stable_mask)),
                'mean_intensity': float(np.mean(stable_intensities)) if len(stable_intensities) > 0 else np.nan,
                'std_intensity': float(np.std(stable_intensities)) if len(stable_intensities) > 0 else np.nan,
                'mean_displacement': float(np.mean(displacements[stable_mask])) if np.sum(stable_mask) > 0 else np.nan
            }
        },
        'comparison_tests': {
            'extruding_vs_retracting': {
                't_statistic': float(t_stat),
                't_pvalue': float(t_pvalue),
                'mann_whitney_u': float(mann_whitney_stat),
                'mann_whitney_p': float(mann_whitney_p)
            }
        }
    }

    print(f"  Correlation: r={r:.3f}, R²={r_squared:.3f}, p={p_value:.3e}")
    print(f"  Extruding: n={results['by_movement_type']['extruding']['n']}, " +
          f"mean_intensity={results['by_movement_type']['extruding']['mean_intensity']:.1f}")
    print(f"  Retracting: n={results['by_movement_type']['retracting']['n']}, " +
          f"mean_intensity={results['by_movement_type']['retracting']['mean_intensity']:.1f}")

    return results

def save_analysis_results(correlation_results, classifications, combined_data, output_dir):
    """Save comprehensive analysis results."""
    os.makedirs(output_dir, exist_ok=True)

    # Save correlation results as pickle file for GUI loading
    with open(os.path.join(output_dir, 'correlation_results.pkl'), 'wb') as f:
        pickle.dump(correlation_results, f)
    print(f"Saved correlation_results.pkl")

    # Compile final summary
    summary = {
        'correlation_analysis': correlation_results,
        'movement_classifications': {
            'n_frame_pairs': len(classifications),
            'extruding': sum(1 for c in classifications if c['movement_type'] == 'extruding'),
            'retracting': sum(1 for c in classifications if c['movement_type'] == 'retracting'),
            'stable': sum(1 for c in classifications if c['movement_type'] == 'stable')
        },
        'data_summary': {
            'n_frames_with_data': len(combined_data),
            'total_valid_points': sum(len([p for p in frame if p['valid']]) for frame in combined_data)
        }
    }

    with open(os.path.join(output_dir, 'final_analysis_summary.json'), 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"Saved analysis results to {output_dir}")

def create_final_figures(combined_data, correlation_results, classifications, output_dir,
                         intensity_label=DEFAULT_LABEL):
    """Create comprehensive final figures. (Drawn by step9_figures.py.)"""
    return step9_figures.create_final_figures(CONFIG, combined_data, correlation_results, classifications, output_dir, intensity_label)

def main():
    # Parse command line arguments
    parse_arguments()

    # Load previous results
    classifications, combined_data = load_previous_results()

    # Propagate the intensity axis label produced upstream (step 7 -> step 8)
    intensity_label = load_intensity_label(
        CONFIG['INPUT_DIR_STEP8'], 'combined_statistics.json')

    # Perform correlation analysis
    correlation_results = perform_correlation_analysis(combined_data)

    # Save results
    save_analysis_results(correlation_results, classifications, combined_data,
                         CONFIG['OUTPUT_DIR'])

    # Create final figures
    create_final_figures(combined_data, correlation_results, classifications,
                        CONFIG['OUTPUT_DIR'], intensity_label)

    print("\n" + "="*60)
    print("STEP 9 COMPLETE - ANALYSIS FINISHED")
    print("="*60)

    if correlation_results:
        print(f"\nFinal Results:")
        print(f"  Sample size: {correlation_results['n_points']} points")
        print(f"  Pearson correlation: r = {correlation_results['overall']['pearson_r']:.4f}")
        print(f"  R² = {correlation_results['overall']['r_squared']:.4f}")
        print(f"  p-value = {correlation_results['overall']['p_value']:.3e}")

    print(f"\nResults saved to: {CONFIG['OUTPUT_DIR']}")

if __name__ == "__main__":
    main()
