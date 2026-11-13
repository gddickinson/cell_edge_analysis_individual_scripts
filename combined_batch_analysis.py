#!/usr/bin/env python3
"""
Combined Batch Analysis
Performs correlation analysis across ALL datasets combined.
Similar to step9, but aggregates data from all processed datasets.
"""

import os
import sys
import argparse
import numpy as np
import pickle
import json
from scipy import stats
from pathlib import Path
import combined_batch_figures  # verification figures (split out to keep this file under 500 lines)

# Configuration
CONFIG = {
    'RESULTS_DIR': "results",
    'OUTPUT_DIR': "combined_analysis",
    'binning_method': 'equal_count',  # Options: equal_count, equal_width, dynamic
    'n_bins': 10,
    'min_bin_count': 5,
    'movement_threshold': 5,  # Threshold for separating extruding vs retracting
    'CREATE_VERIFICATION_FIGURES': True
}

def parse_arguments():
    """Parse command line arguments to override CONFIG."""
    parser = argparse.ArgumentParser(
        description='Combined Batch Correlation Analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze all datasets in results/ folder
  python combined_batch_analysis.py
  
  # Custom results directory
  python combined_batch_analysis.py --results-dir /path/to/results
  
  # Custom output directory
  python combined_batch_analysis.py --output-dir combined_results
  
  # No verification figures (faster)
  python combined_batch_analysis.py --create-verification-figures false
        """
    )
    
    parser.add_argument('--results-dir', type=str, default='results',
                        help='Results directory containing processed datasets (default: results)')
    parser.add_argument('--output-dir', type=str,
                        help='Output directory for combined analysis')
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
    parser.add_argument('--datasets', type=str, nargs='+',
                        help='Specific datasets to include (default: all)')
    
    args = parser.parse_args()
    
    # Override CONFIG with command line arguments
    if args.results_dir is not None:
        CONFIG['RESULTS_DIR'] = args.results_dir
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

def discover_datasets(results_dir, specific_datasets=None):
    """
    Discover all processed datasets in results directory.
    Returns list of (dataset_name, step4_path, step8_path) tuples.
    """
    datasets = []
    
    if not os.path.exists(results_dir):
        print(f"Error: Results directory '{results_dir}' not found!")
        return datasets
    
    # Find all subdirectories
    subdirs = [d for d in os.listdir(results_dir) 
               if os.path.isdir(os.path.join(results_dir, d))]
    
    # Filter to specific datasets if requested
    if specific_datasets:
        subdirs = [d for d in subdirs if d in specific_datasets]
    
    for subdir in sorted(subdirs):
        dataset_path = os.path.join(results_dir, subdir)
        
        # Check for required step results
        step4_path = os.path.join(dataset_path, 'step4_results')
        step8_path = os.path.join(dataset_path, 'step8_results')
        
        step4_file = os.path.join(step4_path, 'movement_classifications.pkl')
        step8_file = os.path.join(step8_path, 'combined_data.pkl')
        
        if os.path.exists(step4_file) and os.path.exists(step8_file):
            datasets.append((subdir, step4_path, step8_path))
        else:
            print(f"Warning: Skipping '{subdir}' - missing step4 or step8 results")
    
    return datasets

def load_dataset_data(step4_path, step8_path):
    """Load data from a single dataset."""
    with open(os.path.join(step4_path, 'movement_classifications.pkl'), 'rb') as f:
        classifications = pickle.load(f)
    
    with open(os.path.join(step8_path, 'combined_data.pkl'), 'rb') as f:
        combined_data = pickle.load(f)
    
    return classifications, combined_data

def aggregate_all_data(datasets_info):
    """Load and aggregate data from all datasets."""
    print("\nLoading data from all datasets...")
    
    all_combined_data = []
    all_classifications = []
    dataset_labels = []
    
    for dataset_name, step4_path, step8_path in datasets_info:
        print(f"  Loading {dataset_name}...")
        classifications, combined_data = load_dataset_data(step4_path, step8_path)
        
        # Flatten combined data and add dataset label
        for frame_data in combined_data:
            for point in frame_data:
                if point['valid']:
                    point_with_label = point.copy()
                    point_with_label['dataset'] = dataset_name
                    all_combined_data.append(point_with_label)
        
        all_classifications.extend(classifications)
    
    print(f"\nAggregated {len(all_combined_data)} valid data points from {len(datasets_info)} datasets")
    
    return all_combined_data, all_classifications, datasets_info

def perform_correlation_analysis(all_combined_data):
    """Perform detailed correlation analysis on combined data."""
    print("\nPerforming correlation analysis on combined data...")
    
    if len(all_combined_data) < 3:
        print("  Insufficient data for correlation analysis")
        return None
    
    displacements = np.array([p['displacement'] for p in all_combined_data])
    intensities = np.array([p['intensity'] for p in all_combined_data])
    
    # Overall correlation
    r, p_value = stats.pearsonr(displacements, intensities)
    r_squared = r ** 2
    
    # Linear regression
    slope, intercept, _, _, std_err = stats.linregress(displacements, intensities)
    
    # Separate by movement type
    extruding_mask = displacements < -CONFIG['movement_threshold']
    retracting_mask = displacements > CONFIG['movement_threshold']
    stable_mask = ~(extruding_mask | retracting_mask)
    
    results = {
        'total_points': len(all_combined_data),
        'correlation_coefficient': r,
        'p_value': p_value,
        'r_squared': r_squared,
        'slope': slope,
        'intercept': intercept,
        'std_err': std_err,
        'mean_displacement': float(np.mean(displacements)),
        'std_displacement': float(np.std(displacements)),
        'mean_intensity': float(np.mean(intensities)),
        'std_intensity': float(np.std(intensities)),
        'extruding_count': int(np.sum(extruding_mask)),
        'retracting_count': int(np.sum(retracting_mask)),
        'stable_count': int(np.sum(stable_mask))
    }
    
    # Per-movement-type statistics
    if np.any(extruding_mask):
        results['extruding_mean_intensity'] = float(np.mean(intensities[extruding_mask]))
        results['extruding_std_intensity'] = float(np.std(intensities[extruding_mask]))
    
    if np.any(retracting_mask):
        results['retracting_mean_intensity'] = float(np.mean(intensities[retracting_mask]))
        results['retracting_std_intensity'] = float(np.std(intensities[retracting_mask]))
    
    if np.any(stable_mask):
        results['stable_mean_intensity'] = float(np.mean(intensities[stable_mask]))
        results['stable_std_intensity'] = float(np.std(intensities[stable_mask]))
    
    print(f"  Correlation coefficient (r): {r:.4f}")
    print(f"  R-squared: {r_squared:.4f}")
    print(f"  p-value: {p_value:.3e}")
    print(f"  Total points: {len(all_combined_data)}")
    
    return results

def perform_binned_analysis(all_combined_data):
    """Perform binned analysis on displacement data."""
    print("\nPerforming binned analysis...")
    
    if len(all_combined_data) < CONFIG['n_bins'] * CONFIG['min_bin_count']:
        print(f"  Insufficient data for {CONFIG['n_bins']} bins")
        return None
    
    displacements = np.array([p['displacement'] for p in all_combined_data])
    intensities = np.array([p['intensity'] for p in all_combined_data])
    
    # Create bins based on method
    if CONFIG['binning_method'] == 'equal_count':
        # Equal number of points per bin
        sorted_indices = np.argsort(displacements)
        bin_edges = [displacements[sorted_indices[0]]]
        points_per_bin = len(displacements) // CONFIG['n_bins']
        
        for i in range(1, CONFIG['n_bins']):
            idx = i * points_per_bin
            bin_edges.append(displacements[sorted_indices[idx]])
        bin_edges.append(displacements[sorted_indices[-1]] + 0.001)
        bin_edges = np.array(bin_edges)
        
    elif CONFIG['binning_method'] == 'equal_width':
        # Equal width bins
        bin_edges = np.linspace(np.min(displacements), np.max(displacements), CONFIG['n_bins'] + 1)
    
    else:  # dynamic
        # Adaptive binning
        bin_edges = np.percentile(displacements, np.linspace(0, 100, CONFIG['n_bins'] + 1))
    
    # Compute statistics for each bin
    bin_stats = []
    for i in range(len(bin_edges) - 1):
        mask = (displacements >= bin_edges[i]) & (displacements < bin_edges[i + 1])
        
        if i == len(bin_edges) - 2:  # Last bin includes right edge
            mask = (displacements >= bin_edges[i]) & (displacements <= bin_edges[i + 1])
        
        if np.sum(mask) >= CONFIG['min_bin_count']:
            bin_displacements = displacements[mask]
            bin_intensities = intensities[mask]
            
            bin_stats.append({
                'bin_index': i,
                'bin_center': float((bin_edges[i] + bin_edges[i + 1]) / 2),
                'bin_left': float(bin_edges[i]),
                'bin_right': float(bin_edges[i + 1]),
                'count': int(np.sum(mask)),
                'mean_displacement': float(np.mean(bin_displacements)),
                'std_displacement': float(np.std(bin_displacements)),
                'mean_intensity': float(np.mean(bin_intensities)),
                'std_intensity': float(np.std(bin_intensities)),
                'sem_intensity': float(np.std(bin_intensities) / np.sqrt(len(bin_intensities)))
            })
    
    print(f"  Created {len(bin_stats)} bins with >= {CONFIG['min_bin_count']} points each")
    
    return bin_stats

def save_results(correlation_results, binned_results, datasets_info, output_dir):
    """Save analysis results."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Save correlation results
    if correlation_results:
        with open(os.path.join(output_dir, 'combined_correlation_statistics.json'), 'w') as f:
            json.dump(correlation_results, f, indent=2)
    
    # Save binned results
    if binned_results:
        with open(os.path.join(output_dir, 'combined_binned_statistics.json'), 'w') as f:
            json.dump(binned_results, f, indent=2)
    
    # Save dataset list
    dataset_info = {
        'n_datasets': len(datasets_info),
        'datasets': [name for name, _, _ in datasets_info],
        'analysis_parameters': {
            'binning_method': CONFIG['binning_method'],
            'n_bins': CONFIG['n_bins'],
            'min_bin_count': CONFIG['min_bin_count'],
            'movement_threshold': CONFIG['movement_threshold']
        }
    }
    
    with open(os.path.join(output_dir, 'dataset_info.json'), 'w') as f:
        json.dump(dataset_info, f, indent=2)
    
    print(f"\nSaved results to {output_dir}")

def create_verification_figures(all_combined_data, correlation_results, binned_results, 
                                datasets_info, output_dir):
    """Create comprehensive verification figures. (Drawn by combined_batch_figures.py.)"""
    return combined_batch_figures.create_verification_figures(CONFIG, all_combined_data, correlation_results, binned_results, datasets_info, output_dir)

def main():
    """Main execution."""
    # Parse arguments
    args = parse_arguments()
    
    print("="*70)
    print("COMBINED BATCH CORRELATION ANALYSIS")
    print("="*70)
    
    # Discover datasets
    print(f"\nSearching for processed datasets in: {CONFIG['RESULTS_DIR']}")
    datasets_info = discover_datasets(CONFIG['RESULTS_DIR'], args.datasets)
    
    if not datasets_info:
        print("\nNo valid datasets found!")
        print("Make sure datasets have been processed through steps 4 and 8.")
        return 1
    
    print(f"\nFound {len(datasets_info)} dataset(s):")
    for i, (name, _, _) in enumerate(datasets_info, 1):
        print(f"  {i}. {name}")
    
    # Load and aggregate data
    all_combined_data, all_classifications, datasets_info = aggregate_all_data(datasets_info)
    
    if not all_combined_data:
        print("\nNo valid data points found!")
        return 1
    
    # Perform analyses
    correlation_results = perform_correlation_analysis(all_combined_data)
    binned_results = perform_binned_analysis(all_combined_data)
    
    # Save results
    save_results(correlation_results, binned_results, datasets_info, CONFIG['OUTPUT_DIR'])
    
    # Create figures
    if CONFIG['CREATE_VERIFICATION_FIGURES']:
        create_verification_figures(all_combined_data, correlation_results, 
                                   binned_results, datasets_info, CONFIG['OUTPUT_DIR'])
    else:
        print("\nSkipping verification figures (CREATE_VERIFICATION_FIGURES=False)")
    
    print("\n" + "="*70)
    print("COMBINED ANALYSIS COMPLETE!")
    print("="*70)
    print(f"\nResults saved to: {CONFIG['OUTPUT_DIR']}")
    print("\nKey files:")
    print(f"  - combined_correlation_statistics.json (main results)")
    print(f"  - combined_binned_statistics.json (binned analysis)")
    print(f"  - dataset_info.json (dataset list)")
    if CONFIG['CREATE_VERIFICATION_FIGURES']:
        print(f"  - verification_figures/ (4 comprehensive plots)")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
