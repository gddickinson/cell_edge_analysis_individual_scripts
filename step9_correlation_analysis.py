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
import matplotlib.pyplot as plt
import pickle
import json
from scipy import stats

from intensity_labels import load_intensity_label, DEFAULT_LABEL

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
    """Create comprehensive final figures."""
    print("Creating final figures...")

    fig_dir = os.path.join(output_dir, 'verification_figures')
    os.makedirs(fig_dir, exist_ok=True)

    # Flatten data
    all_valid = []
    for frame_data in combined_data:
        all_valid.extend([p for p in frame_data if p['valid']])

    if len(all_valid) == 0:
        print("  No valid data for visualization")
        return

    displacements = np.array([p['displacement'] for p in all_valid])
    intensities = np.array([p['intensity'] for p in all_valid])

    # Classify points
    extruding_mask = displacements < -CONFIG['movement_threshold']
    retracting_mask = displacements > CONFIG['movement_threshold']
    stable_mask = np.abs(displacements) <= CONFIG['movement_threshold']

    # Figure 1: Main correlation plot with box plots
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

    # Main scatter plot
    ax_main = fig.add_subplot(gs[1:, :2])

    # Color by movement type
    colors = np.empty(len(displacements), dtype='U10')
    colors[extruding_mask] = 'blue'
    colors[retracting_mask] = 'red'
    colors[stable_mask] = 'gray'

    ax_main.scatter(displacements, intensities, c=colors, s=20, alpha=0.4, edgecolors='none')

    # Add regression line
    if correlation_results:
        slope = correlation_results['overall']['slope']
        intercept = correlation_results['overall']['intercept']
        x_line = np.linspace(displacements.min(), displacements.max(), 100)
        ax_main.plot(x_line, slope * x_line + intercept, 'k--', linewidth=2,
                    label=f'Linear fit (R²={correlation_results["overall"]["r_squared"]:.3f})')

    ax_main.axvline(x=-CONFIG['movement_threshold'], color='k', linestyle=':', alpha=0.5)
    ax_main.axvline(x=CONFIG['movement_threshold'], color='k', linestyle=':', alpha=0.5)
    ax_main.axvline(x=0, color='k', linestyle='-', linewidth=1, alpha=0.3)

    ax_main.set_xlabel('Displacement (pixels)', fontsize=12)
    ax_main.set_ylabel(intensity_label, fontsize=12)
    ax_main.set_title(f'Movement vs Intensity Correlation (n={len(all_valid)} points)', fontsize=14)
    ax_main.legend()
    ax_main.grid(True, alpha=0.3)

    # Top histogram (displacement) - use consistent bins for all movement types
    ax_top = fig.add_subplot(gs[0, :2], sharex=ax_main)
    # Create explicit bin edges spanning the full data range to ensure consistent binning
    hist_bins = np.linspace(displacements.min(), displacements.max(), 51)  # 50 bins
    ax_top.hist(displacements[extruding_mask], bins=hist_bins, color='blue', alpha=0.5, label='Extruding')
    ax_top.hist(displacements[retracting_mask], bins=hist_bins, color='red', alpha=0.5, label='Retracting')
    ax_top.hist(displacements[stable_mask], bins=hist_bins, color='gray', alpha=0.5, label='Stable')
    ax_top.axvline(x=0, color='k', linestyle='-', linewidth=1)
    ax_top.set_ylabel('Count')
    ax_top.legend()
    ax_top.tick_params(labelbottom=False)

    # Top-right: Mean intensity plot with SD error bars
    ax_top_right = fig.add_subplot(gs[0, 2])

    # Prepare data for mean plot
    mean_plot_data = []
    mean_plot_labels = []
    mean_plot_colors = []
    mean_plot_means = []
    mean_plot_stds = []

    if np.sum(extruding_mask) > 0:
        mean_plot_data.append(intensities[extruding_mask])
        mean_plot_labels.append('Ext')
        mean_plot_colors.append('blue')
        mean_plot_means.append(np.mean(intensities[extruding_mask]))
        mean_plot_stds.append(np.std(intensities[extruding_mask]))

    if np.sum(stable_mask) > 0:
        mean_plot_data.append(intensities[stable_mask])
        mean_plot_labels.append('Stab')
        mean_plot_colors.append('gray')
        mean_plot_means.append(np.mean(intensities[stable_mask]))
        mean_plot_stds.append(np.std(intensities[stable_mask]))

    if np.sum(retracting_mask) > 0:
        mean_plot_data.append(intensities[retracting_mask])
        mean_plot_labels.append('Ret')
        mean_plot_colors.append('red')
        mean_plot_means.append(np.mean(intensities[retracting_mask]))
        mean_plot_stds.append(np.std(intensities[retracting_mask]))

    # Plot means with SD error bars
    x_positions = np.arange(1, len(mean_plot_means) + 1)
    ax_top_right.errorbar(x_positions, mean_plot_means, yerr=mean_plot_stds,
                          fmt='o', markersize=8, capsize=5, capthick=2,
                          elinewidth=2, alpha=0.8)

    # Color the markers
    for i, (x, y, color) in enumerate(zip(x_positions, mean_plot_means, mean_plot_colors)):
        ax_top_right.plot(x, y, 'o', markersize=8, color=color, alpha=0.8, zorder=3)

    ax_top_right.set_xticks(x_positions)
    ax_top_right.set_xticklabels(mean_plot_labels)
    ax_top_right.set_ylabel(intensity_label)
    ax_top_right.set_title('Mean Intensity\n(±SD)', fontsize=10)
    ax_top_right.grid(True, alpha=0.3, axis='y')

    # Right box plots
    ax_right = fig.add_subplot(gs[1:, 2])

    box_data = []
    box_labels = []
    box_colors = []

    if np.sum(extruding_mask) > 0:
        box_data.append(intensities[extruding_mask])
        box_labels.append(f'Extruding\n(n={np.sum(extruding_mask)})')
        box_colors.append('blue')

    if np.sum(stable_mask) > 0:
        box_data.append(intensities[stable_mask])
        box_labels.append(f'Stable\n(n={np.sum(stable_mask)})')
        box_colors.append('gray')

    if np.sum(retracting_mask) > 0:
        box_data.append(intensities[retracting_mask])
        box_labels.append(f'Retracting\n(n={np.sum(retracting_mask)})')
        box_colors.append('red')

    bp = ax_right.boxplot(box_data, tick_labels=box_labels, patch_artist=True, showfliers=False)
    for patch, color in zip(bp['boxes'], box_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.5)

    # Overlay individual data points with jitter
    np.random.seed(42)  # For reproducible jitter
    for i, (data, color) in enumerate(zip(box_data, box_colors), start=1):
        # Add horizontal jitter to x-positions
        x_jitter = np.random.normal(i, 0.04, size=len(data))
        ax_right.scatter(x_jitter, data, c=color, s=8, alpha=0.3, edgecolors='none', zorder=3)

        # Add mean and error text
        mean_val = np.mean(data)
        std_val = np.std(data)
        sem_val = std_val / np.sqrt(len(data))

        # Position text at the top of the plot
        y_pos = ax_right.get_ylim()[1] * 0.95
        text_str = f'Mean: {mean_val:.2f}\n±SEM: {sem_val:.2f}\n±SD: {std_val:.2f}'
        ax_right.text(i, y_pos, text_str, ha='center', va='top',
                     fontsize=8, bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))

    ax_right.set_ylabel(intensity_label)
    ax_right.set_title('Intensity by\nMovement Type')
    ax_right.grid(True, alpha=0.3, axis='y')

    plt.savefig(os.path.join(fig_dir, 'scatter_plot.png'),
               dpi=300, bbox_inches='tight')
    plt.close()

    # Figure 2: Movement over time
    fig, axes = plt.subplots(2, 1, figsize=(14, 8))

    frame_nums = [c['frame_pair'][0] for c in classifications]
    avg_displacements = [c['avg_displacement'] for c in classifications]
    movement_types = [c['movement_type'] for c in classifications]

    color_map = {'extruding': 'blue', 'retracting': 'red', 'stable': 'gray'}
    frame_colors = [color_map[mt] for mt in movement_types]

    axes[0].scatter(frame_nums, avg_displacements, c=frame_colors, s=50, alpha=0.6)
    axes[0].axhline(y=CONFIG['movement_threshold'], color='k', linestyle='--', linewidth=1)
    axes[0].axhline(y=-CONFIG['movement_threshold'], color='k', linestyle='--', linewidth=1)
    axes[0].axhline(y=0, color='k', linestyle='-', linewidth=0.5)
    axes[0].set_xlabel('Frame Number')
    axes[0].set_ylabel('Average Displacement (pixels)')
    axes[0].set_title('Cell Edge Movement Over Time')
    axes[0].grid(True, alpha=0.3)

    # Movement type counts
    type_counts = {
        'Extruding': movement_types.count('extruding'),
        'Stable': movement_types.count('stable'),
        'Retracting': movement_types.count('retracting')
    }

    bars = axes[1].bar(type_counts.keys(), type_counts.values(),
                      color=['blue', 'gray', 'red'], alpha=0.6)
    axes[1].set_ylabel('Count')
    axes[1].set_title('Movement Type Distribution')
    axes[1].grid(True, alpha=0.3, axis='y')

    for bar in bars:
        height = bar.get_height()
        axes[1].text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}\n({height/len(movement_types)*100:.1f}%)',
                    ha='center', va='bottom')

    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, 'binned_analysis.png'),
               dpi=300, bbox_inches='tight')
    plt.close()

    # Figure 3: Statistical summary
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Displacement distribution
    axes[0, 0].hist(displacements, bins=40, edgecolor='black', alpha=0.7, color='steelblue')
    axes[0, 0].axvline(x=0, color='k', linestyle='-', linewidth=2)
    axes[0, 0].axvline(x=np.mean(displacements), color='r', linestyle='--', linewidth=2, label='Mean')
    axes[0, 0].axvline(x=np.median(displacements), color='g', linestyle='--', linewidth=2, label='Median')
    axes[0, 0].set_xlabel('Displacement (pixels)')
    axes[0, 0].set_ylabel('Count')
    axes[0, 0].set_title('Overall Displacement Distribution')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3, axis='y')

    # Intensity distribution
    axes[0, 1].hist(intensities, bins=40, edgecolor='black', alpha=0.7, color='coral')
    axes[0, 1].axvline(x=np.mean(intensities), color='r', linestyle='--', linewidth=2, label='Mean')
    axes[0, 1].axvline(x=np.median(intensities), color='g', linestyle='--', linewidth=2, label='Median')
    axes[0, 1].set_xlabel(intensity_label)
    axes[0, 1].set_ylabel('Count')
    axes[0, 1].set_title('Overall Intensity Distribution')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3, axis='y')

    # Residuals plot
    if correlation_results:
        slope = correlation_results['overall']['slope']
        intercept = correlation_results['overall']['intercept']
        predicted = slope * displacements + intercept
        residuals = intensities - predicted

        axes[1, 0].scatter(displacements, residuals, c=colors, s=20, alpha=0.4, edgecolors='none')
        axes[1, 0].axhline(y=0, color='k', linestyle='-', linewidth=1)
        axes[1, 0].set_xlabel('Displacement (pixels)')
        axes[1, 0].set_ylabel('Residuals')
        axes[1, 0].set_title('Residuals Plot')
        axes[1, 0].grid(True, alpha=0.3)

    # Statistics text
    axes[1, 1].axis('off')

    if correlation_results:
        stats_text = "FINAL ANALYSIS SUMMARY\n"
        stats_text += "="*40 + "\n\n"
        stats_text += f"Sample Size: {correlation_results['n_points']} valid points\n"
        stats_text += f"Frames: {len(combined_data)}\n"
        stats_text += f"Intensity metric: {intensity_label}\n\n"

        stats_text += "CORRELATION:\n"
        stats_text += f"  Pearson r: {correlation_results['overall']['pearson_r']:.4f}\n"
        stats_text += f"  R²: {correlation_results['overall']['r_squared']:.4f}\n"
        stats_text += f"  p-value: {correlation_results['overall']['p_value']:.3e}\n"
        stats_text += f"  Slope: {correlation_results['overall']['slope']:.4f}\n\n"

        stats_text += "BY MOVEMENT TYPE:\n"
        for mtype in ['extruding', 'retracting', 'stable']:
            data = correlation_results['by_movement_type'][mtype]
            stats_text += f"  {mtype.upper()}:\n"
            stats_text += f"    n: {data['n']}\n"
            if not np.isnan(data['mean_intensity']):
                stats_text += f"    Mean intensity: {data['mean_intensity']:.1f}\n"
                stats_text += f"    Mean displacement: {data['mean_displacement']:.3f}\n"

        stats_text += "\nCOMPARISON TEST:\n"
        comp = correlation_results['comparison_tests']['extruding_vs_retracting']
        if not np.isnan(comp['t_pvalue']):
            stats_text += f"  t-test p: {comp['t_pvalue']:.3e}\n"
            stats_text += f"  Mann-Whitney p: {comp['mann_whitney_p']:.3e}\n"

        axes[1, 1].text(0.05, 0.95, stats_text, fontsize=9, verticalalignment='top',
                       family='monospace', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, 'summary_statistics.png'),
               dpi=300, bbox_inches='tight')
    plt.close()

    print(f"Saved 3 final summary figures")

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
