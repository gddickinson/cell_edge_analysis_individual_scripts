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
import matplotlib.pyplot as plt
import pickle
import json
from scipy import stats
from pathlib import Path

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
    """Create comprehensive verification figures."""
    print("\nCreating verification figures...")
    
    fig_dir = os.path.join(output_dir, 'verification_figures')
    os.makedirs(fig_dir, exist_ok=True)
    
    displacements = np.array([p['displacement'] for p in all_combined_data])
    intensities = np.array([p['intensity'] for p in all_combined_data])
    datasets = [p['dataset'] for p in all_combined_data]
    
    # Figure 1: Main correlation plot with all datasets
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # Overall scatter
    scatter = axes[0, 0].scatter(displacements, intensities, 
                                c=displacements, cmap='RdBu_r',
                                s=10, alpha=0.3, edgecolors='none',
                                vmin=-10, vmax=10)
    
    # Add regression line
    if correlation_results:
        x_line = np.linspace(np.min(displacements), np.max(displacements), 100)
        y_line = correlation_results['slope'] * x_line + correlation_results['intercept']
        axes[0, 0].plot(x_line, y_line, 'r--', linewidth=2, alpha=0.8, 
                       label=f'y = {correlation_results["slope"]:.3f}x + {correlation_results["intercept"]:.3f}')
    
    axes[0, 0].axvline(x=0, color='k', linestyle='--', linewidth=1, alpha=0.5)
    axes[0, 0].set_xlabel('Displacement (pixels)', fontsize=12)
    axes[0, 0].set_ylabel('Intensity', fontsize=12)
    axes[0, 0].set_title(f'Combined Analysis: All {len(datasets_info)} Datasets\n' +
                        f'n={len(all_combined_data)} points, r={correlation_results["correlation_coefficient"]:.3f}, ' +
                        f'p={correlation_results["p_value"]:.2e}',
                        fontsize=14, fontweight='bold')
    axes[0, 0].legend(fontsize=10)
    axes[0, 0].grid(True, alpha=0.3)
    plt.colorbar(scatter, ax=axes[0, 0], label='Displacement (px)')
    
    # Displacement distribution
    axes[0, 1].hist(displacements, bins=50, edgecolor='black', alpha=0.7, color='coral')
    axes[0, 1].axvline(x=0, color='k', linestyle='--', linewidth=2)
    axes[0, 1].axvline(x=np.mean(displacements), color='r',
                      linestyle='--', linewidth=2, label='Mean')
    axes[0, 1].axvline(x=-CONFIG['movement_threshold'], color='b',
                      linestyle=':', linewidth=2, label='Thresholds', alpha=0.7)
    axes[0, 1].axvline(x=CONFIG['movement_threshold'], color='b',
                      linestyle=':', linewidth=2, alpha=0.7)
    axes[0, 1].set_xlabel('Displacement (pixels)', fontsize=12)
    axes[0, 1].set_ylabel('Count', fontsize=12)
    axes[0, 1].set_title('Displacement Distribution', fontsize=12, fontweight='bold')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3, axis='y')
    
    # Intensity distribution
    axes[1, 0].hist(intensities, bins=50, edgecolor='black', alpha=0.7, color='skyblue')
    axes[1, 0].axvline(x=np.mean(intensities), color='r',
                      linestyle='--', linewidth=2, label='Mean')
    axes[1, 0].set_xlabel('Intensity', fontsize=12)
    axes[1, 0].set_ylabel('Count', fontsize=12)
    axes[1, 0].set_title('Intensity Distribution', fontsize=12, fontweight='bold')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3, axis='y')
    
    # Statistics summary
    axes[1, 1].axis('off')
    if correlation_results:
        stats_text = "COMBINED ANALYSIS STATISTICS\n"
        stats_text += "="*40 + "\n\n"
        stats_text += f"Datasets: {len(datasets_info)}\n"
        stats_text += f"Total Points: {correlation_results['total_points']}\n\n"
        stats_text += f"CORRELATION:\n"
        stats_text += f"  Pearson r: {correlation_results['correlation_coefficient']:.4f}\n"
        stats_text += f"  R²: {correlation_results['r_squared']:.4f}\n"
        stats_text += f"  p-value: {correlation_results['p_value']:.3e}\n"
        
        if correlation_results['p_value'] < 0.001:
            sig = "***"
        elif correlation_results['p_value'] < 0.01:
            sig = "**"
        elif correlation_results['p_value'] < 0.05:
            sig = "*"
        else:
            sig = "n.s."
        stats_text += f"  Significance: {sig}\n\n"
        
        stats_text += f"DISPLACEMENT:\n"
        stats_text += f"  Mean: {correlation_results['mean_displacement']:.3f} px\n"
        stats_text += f"  Std: {correlation_results['std_displacement']:.3f} px\n\n"
        
        stats_text += f"INTENSITY:\n"
        stats_text += f"  Mean: {correlation_results['mean_intensity']:.1f}\n"
        stats_text += f"  Std: {correlation_results['std_intensity']:.1f}\n\n"
        
        stats_text += f"MOVEMENT CLASSIFICATION:\n"
        total = correlation_results['total_points']
        stats_text += f"  Extruding: {correlation_results['extruding_count']} ({100*correlation_results['extruding_count']/total:.1f}%)\n"
        stats_text += f"  Retracting: {correlation_results['retracting_count']} ({100*correlation_results['retracting_count']/total:.1f}%)\n"
        stats_text += f"  Stable: {correlation_results['stable_count']} ({100*correlation_results['stable_count']/total:.1f}%)\n"
        
        axes[1, 1].text(0.1, 0.95, stats_text, fontsize=10,
                       verticalalignment='top', family='monospace',
                       bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
    
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, 'combined_correlation_overview.png'),
               dpi=200, bbox_inches='tight')
    plt.close()
    
    # Figure 2: Binned analysis
    if binned_results:
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        bin_centers = [b['bin_center'] for b in binned_results]
        bin_means = [b['mean_intensity'] for b in binned_results]
        bin_sems = [b['sem_intensity'] for b in binned_results]
        bin_counts = [b['count'] for b in binned_results]
        
        # Binned intensity with error bars
        axes[0, 0].errorbar(bin_centers, bin_means, yerr=bin_sems,
                           fmt='o-', capsize=5, capthick=2, markersize=8,
                           linewidth=2, color='navy', ecolor='gray')
        axes[0, 0].axvline(x=0, color='k', linestyle='--', linewidth=1, alpha=0.5)
        axes[0, 0].set_xlabel('Displacement Bin Center (pixels)', fontsize=12)
        axes[0, 0].set_ylabel('Mean Intensity ± SEM', fontsize=12)
        axes[0, 0].set_title('Binned Analysis: Intensity vs Displacement\n' +
                            f'Method: {CONFIG["binning_method"]}, {len(binned_results)} bins',
                            fontsize=14, fontweight='bold')
        axes[0, 0].grid(True, alpha=0.3)
        
        # Raw scatter with bins overlaid
        axes[0, 1].scatter(displacements, intensities, s=5, alpha=0.2, color='gray')
        axes[0, 1].errorbar(bin_centers, bin_means, yerr=bin_sems,
                           fmt='ro-', capsize=5, capthick=2, markersize=10,
                           linewidth=3, label='Binned means ± SEM')
        axes[0, 1].axvline(x=0, color='k', linestyle='--', linewidth=1, alpha=0.5)
        axes[0, 1].set_xlabel('Displacement (pixels)', fontsize=12)
        axes[0, 1].set_ylabel('Intensity', fontsize=12)
        axes[0, 1].set_title('Binned Overlay on Raw Data', fontsize=12, fontweight='bold')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)
        
        # Counts per bin
        axes[1, 0].bar(range(len(bin_counts)), bin_counts, alpha=0.7, color='green',
                      edgecolor='black')
        axes[1, 0].axhline(y=CONFIG['min_bin_count'], color='r', linestyle='--',
                          linewidth=2, label=f'Min count ({CONFIG["min_bin_count"]})')
        axes[1, 0].set_xlabel('Bin Index', fontsize=12)
        axes[1, 0].set_ylabel('Point Count', fontsize=12)
        axes[1, 0].set_title('Points per Bin', fontsize=12, fontweight='bold')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3, axis='y')
        
        # Bin details table
        axes[1, 1].axis('off')
        table_text = "BIN STATISTICS\n"
        table_text += "="*50 + "\n"
        table_text += f"{'Bin':<4} {'Range':<20} {'Count':<7} {'Mean Int':<10}\n"
        table_text += "-"*50 + "\n"
        for b in binned_results:
            table_text += f"{b['bin_index']:<4} "
            table_text += f"[{b['bin_left']:>6.2f}, {b['bin_right']:>6.2f}]  "
            table_text += f"{b['count']:<7} "
            table_text += f"{b['mean_intensity']:>8.1f}\n"
        
        axes[1, 1].text(0.1, 0.95, table_text, fontsize=9,
                       verticalalignment='top', family='monospace')
        
        plt.tight_layout()
        plt.savefig(os.path.join(fig_dir, 'combined_binned_analysis.png'),
                   dpi=200, bbox_inches='tight')
        plt.close()
    
    # Figure 3: Per-dataset breakdown
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # Get unique datasets and assign colors
    unique_datasets = sorted(set(datasets))
    colors = plt.cm.tab10(np.linspace(0, 1, len(unique_datasets)))
    dataset_colors = dict(zip(unique_datasets, colors))
    
    # Scatter colored by dataset
    for dataset in unique_datasets:
        mask = np.array([d == dataset for d in datasets])
        axes[0, 0].scatter(displacements[mask], intensities[mask],
                          c=[dataset_colors[dataset]], label=dataset,
                          s=20, alpha=0.5, edgecolors='none')
    
    axes[0, 0].axvline(x=0, color='k', linestyle='--', linewidth=1, alpha=0.5)
    axes[0, 0].set_xlabel('Displacement (pixels)', fontsize=12)
    axes[0, 0].set_ylabel('Intensity', fontsize=12)
    axes[0, 0].set_title('Data Colored by Dataset', fontsize=14, fontweight='bold')
    axes[0, 0].legend(fontsize=8, loc='best')
    axes[0, 0].grid(True, alpha=0.3)
    
    # Per-dataset correlation coefficients
    dataset_correlations = []
    for dataset in unique_datasets:
        mask = np.array([d == dataset for d in datasets])
        if np.sum(mask) > 2:
            r, _ = stats.pearsonr(displacements[mask], intensities[mask])
            dataset_correlations.append((dataset, r, np.sum(mask)))
    
    if dataset_correlations:
        names, rs, counts = zip(*dataset_correlations)
        x_pos = np.arange(len(names))
        colors_list = [dataset_colors[name] for name in names]
        
        bars = axes[0, 1].bar(x_pos, rs, color=colors_list, alpha=0.7, edgecolor='black')
        axes[0, 1].axhline(y=0, color='k', linestyle='-', linewidth=1)
        axes[0, 1].set_xticks(x_pos)
        axes[0, 1].set_xticklabels(names, rotation=45, ha='right')
        axes[0, 1].set_ylabel('Pearson r', fontsize=12)
        axes[0, 1].set_title('Correlation Coefficient by Dataset', fontsize=12, fontweight='bold')
        axes[0, 1].grid(True, alpha=0.3, axis='y')
        
        # Add count labels on bars
        for i, (bar, count) in enumerate(zip(bars, counts)):
            height = bar.get_height()
            axes[0, 1].text(bar.get_x() + bar.get_width()/2., height,
                           f'n={count}',
                           ha='center', va='bottom' if height >= 0 else 'top',
                           fontsize=8)
    
    # Points per dataset
    dataset_counts = {}
    for dataset in unique_datasets:
        dataset_counts[dataset] = sum(1 for d in datasets if d == dataset)
    
    axes[1, 0].bar(range(len(dataset_counts)), list(dataset_counts.values()),
                  color=[dataset_colors[d] for d in dataset_counts.keys()],
                  alpha=0.7, edgecolor='black')
    axes[1, 0].set_xticks(range(len(dataset_counts)))
    axes[1, 0].set_xticklabels(list(dataset_counts.keys()), rotation=45, ha='right')
    axes[1, 0].set_ylabel('Point Count', fontsize=12)
    axes[1, 0].set_title('Data Points per Dataset', fontsize=12, fontweight='bold')
    axes[1, 0].grid(True, alpha=0.3, axis='y')
    
    # Dataset summary table
    axes[1, 1].axis('off')
    table_text = "DATASET CONTRIBUTIONS\n"
    table_text += "="*40 + "\n"
    table_text += f"{'Dataset':<15} {'Points':<10} {'%':<8}\n"
    table_text += "-"*40 + "\n"
    total_points = len(datasets)
    for dataset, count in sorted(dataset_counts.items()):
        pct = 100 * count / total_points
        table_text += f"{dataset:<15} {count:<10} {pct:>6.1f}%\n"
    table_text += "-"*40 + "\n"
    table_text += f"{'TOTAL':<15} {total_points:<10} {100.0:>6.1f}%\n"
    
    axes[1, 1].text(0.1, 0.95, table_text, fontsize=10,
                   verticalalignment='top', family='monospace')
    
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, 'combined_per_dataset_breakdown.png'),
               dpi=200, bbox_inches='tight')
    plt.close()
    
    # Figure 4: Movement type analysis
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # Separate by movement type
    extruding_mask = displacements < -CONFIG['movement_threshold']
    retracting_mask = displacements > CONFIG['movement_threshold']
    stable_mask = ~(extruding_mask | retracting_mask)
    
    # Intensity by movement type
    movement_data = []
    movement_labels = []
    movement_colors = []
    
    if np.any(extruding_mask):
        movement_data.append(intensities[extruding_mask])
        movement_labels.append(f'Extruding\n(n={np.sum(extruding_mask)})')
        movement_colors.append('blue')
    
    if np.any(stable_mask):
        movement_data.append(intensities[stable_mask])
        movement_labels.append(f'Stable\n(n={np.sum(stable_mask)})')
        movement_colors.append('gray')
    
    if np.any(retracting_mask):
        movement_data.append(intensities[retracting_mask])
        movement_labels.append(f'Retracting\n(n={np.sum(retracting_mask)})')
        movement_colors.append('red')
    
    bp = axes[0, 0].boxplot(movement_data, labels=movement_labels,
                            patch_artist=True, widths=0.6)
    for patch, color in zip(bp['boxes'], movement_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.5)
    axes[0, 0].set_ylabel('Intensity', fontsize=12)
    axes[0, 0].set_title('Intensity Distribution by Movement Type', 
                         fontsize=14, fontweight='bold')
    axes[0, 0].grid(True, alpha=0.3, axis='y')
    
    # Scatter colored by movement type
    if np.any(extruding_mask):
        axes[0, 1].scatter(displacements[extruding_mask], intensities[extruding_mask],
                          c='blue', label='Extruding', s=20, alpha=0.5)
    if np.any(stable_mask):
        axes[0, 1].scatter(displacements[stable_mask], intensities[stable_mask],
                          c='gray', label='Stable', s=20, alpha=0.5)
    if np.any(retracting_mask):
        axes[0, 1].scatter(displacements[retracting_mask], intensities[retracting_mask],
                          c='red', label='Retracting', s=20, alpha=0.5)
    
    axes[0, 1].axvline(x=-CONFIG['movement_threshold'], color='k',
                      linestyle='--', linewidth=1, alpha=0.5)
    axes[0, 1].axvline(x=CONFIG['movement_threshold'], color='k',
                      linestyle='--', linewidth=1, alpha=0.5)
    axes[0, 1].axvline(x=0, color='k', linestyle='-', linewidth=1, alpha=0.3)
    axes[0, 1].set_xlabel('Displacement (pixels)', fontsize=12)
    axes[0, 1].set_ylabel('Intensity', fontsize=12)
    axes[0, 1].set_title('Data Colored by Movement Type', fontsize=12, fontweight='bold')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)
    
    # Mean intensity comparison
    means = []
    labels = []
    colors_bar = []
    if np.any(extruding_mask):
        means.append(np.mean(intensities[extruding_mask]))
        labels.append('Extruding')
        colors_bar.append('blue')
    if np.any(stable_mask):
        means.append(np.mean(intensities[stable_mask]))
        labels.append('Stable')
        colors_bar.append('gray')
    if np.any(retracting_mask):
        means.append(np.mean(intensities[retracting_mask]))
        labels.append('Retracting')
        colors_bar.append('red')
    
    if means:
        bars = axes[1, 0].bar(range(len(means)), means, color=colors_bar,
                             alpha=0.7, edgecolor='black')
        axes[1, 0].set_xticks(range(len(means)))
        axes[1, 0].set_xticklabels(labels)
        axes[1, 0].set_ylabel('Mean Intensity', fontsize=12)
        axes[1, 0].set_title('Mean Intensity by Movement Type',
                            fontsize=12, fontweight='bold')
        axes[1, 0].grid(True, alpha=0.3, axis='y')
        
        # Add value labels
        for bar, mean in zip(bars, means):
            axes[1, 0].text(bar.get_x() + bar.get_width()/2., mean,
                           f'{mean:.1f}',
                           ha='center', va='bottom', fontsize=10)
    
    # Movement type statistics
    axes[1, 1].axis('off')
    stats_text = "MOVEMENT TYPE ANALYSIS\n"
    stats_text += "="*45 + "\n\n"
    stats_text += f"Threshold: ±{CONFIG['movement_threshold']} pixels\n\n"
    
    if np.any(extruding_mask):
        stats_text += f"EXTRUDING (< -{CONFIG['movement_threshold']} px):\n"
        stats_text += f"  Count: {np.sum(extruding_mask)}\n"
        stats_text += f"  Percent: {100*np.sum(extruding_mask)/len(displacements):.1f}%\n"
        stats_text += f"  Mean Intensity: {np.mean(intensities[extruding_mask]):.1f}\n"
        stats_text += f"  Std Intensity: {np.std(intensities[extruding_mask]):.1f}\n\n"
    
    if np.any(stable_mask):
        stats_text += f"STABLE (±{CONFIG['movement_threshold']} px):\n"
        stats_text += f"  Count: {np.sum(stable_mask)}\n"
        stats_text += f"  Percent: {100*np.sum(stable_mask)/len(displacements):.1f}%\n"
        stats_text += f"  Mean Intensity: {np.mean(intensities[stable_mask]):.1f}\n"
        stats_text += f"  Std Intensity: {np.std(intensities[stable_mask]):.1f}\n\n"
    
    if np.any(retracting_mask):
        stats_text += f"RETRACTING (> {CONFIG['movement_threshold']} px):\n"
        stats_text += f"  Count: {np.sum(retracting_mask)}\n"
        stats_text += f"  Percent: {100*np.sum(retracting_mask)/len(displacements):.1f}%\n"
        stats_text += f"  Mean Intensity: {np.mean(intensities[retracting_mask]):.1f}\n"
        stats_text += f"  Std Intensity: {np.std(intensities[retracting_mask]):.1f}\n"
    
    axes[1, 1].text(0.1, 0.95, stats_text, fontsize=10,
                   verticalalignment='top', family='monospace',
                   bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3))
    
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, 'combined_movement_type_analysis.png'),
               dpi=200, bbox_inches='tight')
    plt.close()
    
    print(f"  Saved 4 verification figures to {fig_dir}")

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
