#!/usr/bin/env python3
"""
Batch Results Summary
Extracts and summarizes correlation statistics from all processed datasets.
"""

import os
import json
import sys
import argparse
from pathlib import Path

def load_statistics(results_dir, dataset_name):
    """Load statistics from a processed dataset."""
    stats = {}
    
    # Step 9: Correlation statistics
    step9_file = os.path.join(results_dir, dataset_name, 
                              'step9_results/correlation_statistics.json')
    if os.path.exists(step9_file):
        with open(step9_file) as f:
            step9_data = json.load(f)
            stats['correlation_coefficient'] = step9_data.get('correlation_coefficient', None)
            stats['p_value'] = step9_data.get('p_value', None)
            stats['r_squared'] = step9_data.get('r_squared', None)
            stats['n_points'] = step9_data.get('total_valid_points', 0)
    
    # Step 8: Combined data statistics
    step8_file = os.path.join(results_dir, dataset_name,
                              'step8_results/combined_statistics.json')
    if os.path.exists(step8_file):
        with open(step8_file) as f:
            step8_data = json.load(f)
            stats['mean_displacement'] = step8_data.get('mean_displacement', None)
            stats['std_displacement'] = step8_data.get('std_displacement', None)
            stats['mean_intensity'] = step8_data.get('mean_intensity', None)
            stats['std_intensity'] = step8_data.get('std_intensity', None)
    
    # Step 4: Movement classification
    step4_file = os.path.join(results_dir, dataset_name,
                              'step4_results/classification_statistics.json')
    if os.path.exists(step4_file):
        with open(step4_file) as f:
            step4_data = json.load(f)
            stats['extruding_percent'] = step4_data.get('extruding_percent', None)
            stats['retracting_percent'] = step4_data.get('retracting_percent', None)
            stats['stable_percent'] = step4_data.get('stable_percent', None)
    
    return stats

def print_summary_table(datasets_stats):
    """Print formatted summary table."""
    if not datasets_stats:
        print("No datasets with statistics found.")
        return
    
    # Print header
    print("\n" + "="*120)
    print("BATCH PROCESSING RESULTS SUMMARY")
    print("="*120)
    print()
    
    # Correlation table
    print("Correlation Analysis:")
    print("-"*120)
    print(f"{'Dataset':<20} {'N Points':>10} {'Pearson r':>12} {'R²':>12} {'p-value':>15} {'Significance':>15}")
    print("-"*120)
    
    for dataset, stats in sorted(datasets_stats.items()):
        n_points = stats.get('n_points', 0)
        r = stats.get('correlation_coefficient')
        r2 = stats.get('r_squared')
        p = stats.get('p_value')
        
        # Determine significance
        if p is not None:
            if p < 0.001:
                sig = "***"
            elif p < 0.01:
                sig = "**"
            elif p < 0.05:
                sig = "*"
            else:
                sig = "n.s."
        else:
            sig = "N/A"
        
        r_str = f"{r:.4f}" if r is not None else "N/A"
        r2_str = f"{r2:.4f}" if r2 is not None else "N/A"
        p_str = f"{p:.3e}" if p is not None else "N/A"
        
        print(f"{dataset:<20} {n_points:>10} {r_str:>12} {r2_str:>12} {p_str:>15} {sig:>15}")
    
    print("-"*120)
    print("Significance: *** p<0.001, ** p<0.01, * p<0.05, n.s. not significant")
    print()
    
    # Movement classification table
    print("Movement Classification:")
    print("-"*120)
    print(f"{'Dataset':<20} {'Extruding %':>15} {'Retracting %':>15} {'Stable %':>15}")
    print("-"*120)
    
    for dataset, stats in sorted(datasets_stats.items()):
        ext = stats.get('extruding_percent')
        ret = stats.get('retracting_percent')
        stb = stats.get('stable_percent')
        
        ext_str = f"{ext:.1f}%" if ext is not None else "N/A"
        ret_str = f"{ret:.1f}%" if ret is not None else "N/A"
        stb_str = f"{stb:.1f}%" if stb is not None else "N/A"
        
        print(f"{dataset:<20} {ext_str:>15} {ret_str:>15} {stb_str:>15}")
    
    print("-"*120)
    print()
    
    # Displacement and Intensity statistics
    print("Displacement and Intensity Statistics:")
    print("-"*120)
    print(f"{'Dataset':<20} {'Mean Disp (px)':>18} {'Std Disp (px)':>18} {'Mean Intensity':>18} {'Std Intensity':>18}")
    print("-"*120)
    
    for dataset, stats in sorted(datasets_stats.items()):
        mean_d = stats.get('mean_displacement')
        std_d = stats.get('std_displacement')
        mean_i = stats.get('mean_intensity')
        std_i = stats.get('std_intensity')
        
        mean_d_str = f"{mean_d:.3f}" if mean_d is not None else "N/A"
        std_d_str = f"{std_d:.3f}" if std_d is not None else "N/A"
        mean_i_str = f"{mean_i:.1f}" if mean_i is not None else "N/A"
        std_i_str = f"{std_i:.1f}" if std_i is not None else "N/A"
        
        print(f"{dataset:<20} {mean_d_str:>18} {std_d_str:>18} {mean_i_str:>18} {std_i_str:>18}")
    
    print("-"*120)
    print()

def export_csv(datasets_stats, output_file):
    """Export summary to CSV file."""
    import csv
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow([
            'Dataset',
            'N_Points',
            'Pearson_r',
            'R_squared',
            'P_value',
            'Mean_Displacement_px',
            'Std_Displacement_px',
            'Mean_Intensity',
            'Std_Intensity',
            'Extruding_Percent',
            'Retracting_Percent',
            'Stable_Percent'
        ])
        
        # Write data
        for dataset, stats in sorted(datasets_stats.items()):
            writer.writerow([
                dataset,
                stats.get('n_points', ''),
                stats.get('correlation_coefficient', ''),
                stats.get('r_squared', ''),
                stats.get('p_value', ''),
                stats.get('mean_displacement', ''),
                stats.get('std_displacement', ''),
                stats.get('mean_intensity', ''),
                stats.get('std_intensity', ''),
                stats.get('extruding_percent', ''),
                stats.get('retracting_percent', ''),
                stats.get('stable_percent', '')
            ])
    
    print(f"Exported to: {output_file}")

def main():
    parser = argparse.ArgumentParser(
        description='Summarize batch processing results',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('results_dir', nargs='?', default='results',
                       help='Results directory (default: results)')
    parser.add_argument('--csv', type=str,
                       help='Export summary to CSV file')
    parser.add_argument('--dataset', type=str,
                       help='Show only specific dataset')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.results_dir):
        print(f"Error: Results directory '{args.results_dir}' not found")
        return 1
    
    # Discover processed datasets
    datasets_stats = {}
    
    if args.dataset:
        # Single dataset
        if os.path.exists(os.path.join(args.results_dir, args.dataset)):
            stats = load_statistics(args.results_dir, args.dataset)
            if stats:
                datasets_stats[args.dataset] = stats
        else:
            print(f"Error: Dataset '{args.dataset}' not found in {args.results_dir}")
            return 1
    else:
        # All datasets
        for item in os.listdir(args.results_dir):
            item_path = os.path.join(args.results_dir, item)
            if os.path.isdir(item_path):
                stats = load_statistics(args.results_dir, item)
                if stats:
                    datasets_stats[item] = stats
    
    if not datasets_stats:
        print(f"No processed datasets found in '{args.results_dir}'")
        print("Make sure datasets have been analyzed with the complete pipeline.")
        return 1
    
    # Print summary table
    print_summary_table(datasets_stats)
    
    # Export to CSV if requested
    if args.csv:
        export_csv(datasets_stats, args.csv)
    
    # Summary statistics across all datasets
    if len(datasets_stats) > 1:
        print("\nOverall Statistics Across All Datasets:")
        print("-"*60)
        
        # Correlation coefficients
        r_values = [s['correlation_coefficient'] for s in datasets_stats.values() 
                   if s.get('correlation_coefficient') is not None]
        if r_values:
            import statistics
            print(f"Mean correlation coefficient: {statistics.mean(r_values):.4f} ± {statistics.stdev(r_values) if len(r_values) > 1 else 0:.4f}")
            print(f"Range: [{min(r_values):.4f}, {max(r_values):.4f}]")
        
        print("-"*60)
        print(f"Total datasets analyzed: {len(datasets_stats)}")
        
        # Count significant correlations
        sig_count = sum(1 for s in datasets_stats.values() 
                       if s.get('p_value') is not None and s['p_value'] < 0.05)
        print(f"Datasets with significant correlation (p<0.05): {sig_count}/{len(datasets_stats)}")
        print()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
