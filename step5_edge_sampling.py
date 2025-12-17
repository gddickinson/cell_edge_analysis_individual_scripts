#!/usr/bin/env python3
"""
Step 5: Edge Point Sampling
Samples points along cell edges at regular x-intervals.
Saves to step5_results/
"""

import os
import sys
import argparse
import numpy as np
import matplotlib.pyplot as plt
import pickle
import json

# Configuration
CONFIG = {
    'INPUT_DIR_STEP1': "step1_results",
    'INPUT_DIR_STEP2': "step2_results",
    'OUTPUT_DIR': "step5_results",
    'n_points': 12,              # Number of sampling points (ignored for 'dense' method)
    'exclude_endpoints': True,   # Exclude first and last edge points
    'sampling_method': 'displacement_like', # Options: 'per_frame', 'fixed_x', 'dense', 'displacement_like'
                                    # 'per_frame': sample each frame independently at n_points
                                    # 'fixed_x': same x-positions across all frames
                                    # 'dense': sample at every unique x-position in each frame
                                    # 'displacement_like': sample at integer x-positions like step 3/4 displacement calculation
    'target_points_displacement': 20,  # Target number of points for 'displacement_like' method (None = all integer x-positions)
    'y_selection': 'uppermost',   # Options: 'uppermost' or 'lowermost'
                                    # 'uppermost': select minimum y (top of cell)
                                    # 'lowermost': select maximum y (bottom of cell)
    'CREATE_VERIFICATION_FIGURES': True  # Create verification figures
}

def parse_arguments():
    """Parse command line arguments to override CONFIG."""
    parser = argparse.ArgumentParser(description='Step 5: Edge Point Sampling')
    
    parser.add_argument('--input-dir-step1', type=str,
                        help='Input directory from step 1')
    parser.add_argument('--input-dir-step2', type=str,
                        help='Input directory from step 2')
    parser.add_argument('--output-dir', type=str,
                        help='Output directory for results')
    parser.add_argument('--n-points', type=int,
                        help='Number of sampling points')
    parser.add_argument('--exclude-endpoints', type=lambda x: x.lower() == 'true',
                        help='Exclude endpoints (true/false)')
    parser.add_argument('--sampling-method', type=str,
                        choices=['per_frame', 'fixed_x', 'dense', 'displacement_like'],
                        help='Sampling method')
    parser.add_argument('--target-points-displacement', type=int,
                        help='Target points for displacement_like method')
    parser.add_argument('--y-selection', type=str,
                        choices=['uppermost', 'lowermost'],
                        help='Y selection method')
    parser.add_argument('--create-verification-figures', type=lambda x: x.lower() == 'true',
                        help='Create verification figures (true/false)')
    
    args = parser.parse_args()
    
    # Override CONFIG with command line arguments
    if args.input_dir_step1 is not None:
        CONFIG['INPUT_DIR_STEP1'] = args.input_dir_step1
    if args.input_dir_step2 is not None:
        CONFIG['INPUT_DIR_STEP2'] = args.input_dir_step2
    if args.output_dir is not None:
        CONFIG['OUTPUT_DIR'] = args.output_dir
    if args.n_points is not None:
        CONFIG['n_points'] = args.n_points
    if args.exclude_endpoints is not None:
        CONFIG['exclude_endpoints'] = args.exclude_endpoints
    if args.sampling_method is not None:
        CONFIG['sampling_method'] = args.sampling_method
    if args.target_points_displacement is not None:
        CONFIG['target_points_displacement'] = args.target_points_displacement
    if args.y_selection is not None:
        CONFIG['y_selection'] = args.y_selection
    if args.create_verification_figures is not None:
        CONFIG['CREATE_VERIFICATION_FIGURES'] = args.create_verification_figures
    
    return args

def load_previous_results():
    """Load data from Steps 1 and 2."""
    print("Loading previous results...")

    images = np.load(os.path.join(CONFIG['INPUT_DIR_STEP1'], 'images.npy'))
    masks = np.load(os.path.join(CONFIG['INPUT_DIR_STEP1'], 'masks.npy'))

    with open(os.path.join(CONFIG['INPUT_DIR_STEP2'], 'edges.pkl'), 'rb') as f:
        edges = pickle.load(f)

    return images, masks, edges

def select_y_value(candidates):
    """
    Select either uppermost or lowermost point from candidates.
    Returns index of selected point.
    """
    if CONFIG['y_selection'] == 'uppermost':
        return np.argmin(candidates[:, 0])  # Minimum y (top)
    else:  # 'lowermost'
        return np.argmax(candidates[:, 0])  # Maximum y (bottom)

def sample_edge_points_xaxis(contour, n_points, exclude_endpoints=True):
    """
    Sample n_points along edge at regular x-coordinate intervals.
    """
    if len(contour) == 0:
        return np.array([])

    # Get x-range
    x_min = np.min(contour[:, 1])
    x_max = np.max(contour[:, 1])

    # Calculate x-positions for sampling
    if exclude_endpoints:
        # Exclude a small margin from endpoints
        margin = (x_max - x_min) * 0.05
        x_sample = np.linspace(x_min + margin, x_max - margin, n_points)
    else:
        x_sample = np.linspace(x_min, x_max, n_points)

    # For each x, find the selected (uppermost or lowermost) point on the edge
    sampled_points = []
    for x_target in x_sample:
        # Find contour points near this x
        mask = np.abs(contour[:, 1] - x_target) < (x_max - x_min) / (n_points * 2)
        if np.any(mask):
            # Get selected point (uppermost or lowermost)
            candidates = contour[mask]
            idx = select_y_value(candidates)
            sampled_points.append(candidates[idx])

    return np.array(sampled_points) if sampled_points else np.array([])

def determine_common_x_range(edges, exclude_endpoints=True):
    """
    Determine the common x-range across all frames.
    Returns the x-range that is present in all frames.
    """
    if len(edges) == 0:
        return 0, 0

    # Find the x-range for each frame
    x_mins = []
    x_maxs = []

    for edge in edges:
        if len(edge) > 0:
            x_mins.append(np.min(edge[:, 1]))
            x_maxs.append(np.max(edge[:, 1]))

    if not x_mins:
        return 0, 0

    # Common range is the intersection of all ranges
    common_x_min = np.max(x_mins)  # Maximum of minimums
    common_x_max = np.min(x_maxs)  # Minimum of maximums

    # Apply endpoint exclusion if requested
    if exclude_endpoints:
        margin = (common_x_max - common_x_min) * 0.05
        common_x_min += margin
        common_x_max -= margin

    return common_x_min, common_x_max

def sample_edge_at_fixed_x(contour, x_positions):
    """
    Sample edge at fixed x-positions, finding selected (uppermost or lowermost) point at each x.
    Returns array of sampled points (y, x) coordinates.
    """
    if len(contour) == 0:
        return np.array([])

    sampled_points = []
    x_range = np.max(contour[:, 1]) - np.min(contour[:, 1])

    for x_target in x_positions:
        # Find contour points near this x
        search_width = x_range / (len(x_positions) * 2) if len(x_positions) > 1 else x_range / 10
        mask = np.abs(contour[:, 1] - x_target) < search_width

        if np.any(mask):
            # Get selected point (uppermost or lowermost)
            candidates = contour[mask]
            idx = select_y_value(candidates)
            sampled_points.append(candidates[idx])
        else:
            # No point found at this x, record as NaN
            sampled_points.append([np.nan, x_target])

    return np.array(sampled_points) if sampled_points else np.array([])

def sample_edge_dense(contour, exclude_endpoints=True):
    """
    Sample edge at every unique x-position in the contour.
    For each unique x, selects the uppermost or lowermost point.
    Returns array of sampled points (y, x) coordinates.
    """
    if len(contour) == 0:
        return np.array([])

    # Get unique x-positions (rounded to avoid floating point issues)
    unique_x = np.unique(np.round(contour[:, 1], decimals=6))

    # Apply endpoint exclusion if requested
    if exclude_endpoints and len(unique_x) > 2:
        # Remove first and last x-positions
        unique_x = unique_x[1:-1]

    sampled_points = []
    for x_pos in unique_x:
        # Find all points at this x-position (with small tolerance)
        mask = np.abs(contour[:, 1] - x_pos) < 0.5  # Within 0.5 pixel
        if np.any(mask):
            candidates = contour[mask]
            idx = select_y_value(candidates)
            sampled_points.append(candidates[idx])

    return np.array(sampled_points) if sampled_points else np.array([])

def sample_edge_displacement_like(contour, exclude_endpoints=True):
    """
    Sample edge at integer x-positions using the same method as step 4 arrow visualization.
    This mimics the displacement calculation approach from step 3/4.
    For each integer x, finds edge points within 0.5 pixels and selects uppermost or lowermost.

    If CONFIG['target_points_displacement'] is set, samples approximately that many points
    (matching step 4's arrow subsampling approach).

    Returns array of sampled points (y, x) coordinates.
    """
    if len(contour) == 0:
        return np.array([])

    # Get x-range of the contour
    x_min = int(np.floor(np.min(contour[:, 1])))
    x_max = int(np.ceil(np.max(contour[:, 1])))

    # Apply endpoint exclusion if requested
    if exclude_endpoints:
        x_min += 1
        x_max -= 1

    # Generate all integer x-positions
    all_x_positions = list(range(x_min, x_max + 1))

    # Subsample if target_points is set (matching step 4's approach)
    if CONFIG.get('target_points_displacement') is not None:
        target_points = CONFIG['target_points_displacement']
        if len(all_x_positions) > target_points:
            step = max(1, len(all_x_positions) // target_points)
            x_positions = all_x_positions[::step]
        else:
            x_positions = all_x_positions
    else:
        x_positions = all_x_positions

    sampled_points = []
    for x_pos in x_positions:
        # Find points within 0.5 pixels of this integer x (matching step 3's tolerance)
        mask = np.abs(contour[:, 1] - x_pos) < 0.5
        if np.any(mask):
            candidates = contour[mask]
            # Select uppermost or lowermost point
            idx = select_y_value(candidates)
            sampled_points.append(candidates[idx])

    return np.array(sampled_points) if sampled_points else np.array([])

def sample_all_edges(edges):
    """Sample all edge contours using the selected method."""
    print(f"Sampling method: {CONFIG['sampling_method']}")
    print(f"Y-selection: {CONFIG['y_selection']}")

    sampled_edges = []

    if CONFIG['sampling_method'] == 'fixed_x':
        # Determine fixed x-positions from common range
        common_x_min, common_x_max = determine_common_x_range(edges, CONFIG['exclude_endpoints'])
        fixed_x_positions = np.linspace(common_x_min, common_x_max, CONFIG['n_points'])
        print(f"Using fixed x-positions from {common_x_min:.1f} to {common_x_max:.1f}")

        # Store for later reference
        CONFIG['_fixed_x_positions'] = fixed_x_positions

        # Sample each frame at these fixed x-positions
        for i, edge in enumerate(edges):
            sampled_points = sample_edge_at_fixed_x(edge, fixed_x_positions)
            sampled_edges.append(sampled_points)

            if (i + 1) % 10 == 0:
                print(f"  Processed {i+1}/{len(edges)} edges")

    elif CONFIG['sampling_method'] == 'dense':
        # Sample at every unique x-position in each frame
        print(f"Sampling at all unique x-positions in each frame...")

        for i, edge in enumerate(edges):
            sampled_points = sample_edge_dense(edge, CONFIG['exclude_endpoints'])
            sampled_edges.append(sampled_points)

            if (i + 1) % 10 == 0:
                points_in_last = len(sampled_edges[-1]) if len(sampled_edges) > 0 else 0
                print(f"  Processed {i+1}/{len(edges)} edges (last frame: {points_in_last} points)")

    elif CONFIG['sampling_method'] == 'displacement_like':
        # Sample at integer x-positions using step 3/4 displacement method
        if CONFIG.get('target_points_displacement') is not None:
            print(f"Sampling at integer x-positions (displacement-like method) with ~{CONFIG['target_points_displacement']} points per frame...")
        else:
            print(f"Sampling at integer x-positions (displacement-like method) at all integer x values...")

        for i, edge in enumerate(edges):
            sampled_points = sample_edge_displacement_like(edge, CONFIG['exclude_endpoints'])
            sampled_edges.append(sampled_points)

            if (i + 1) % 10 == 0:
                points_in_last = len(sampled_edges[-1]) if len(sampled_edges) > 0 else 0
                print(f"  Processed {i+1}/{len(edges)} edges (last frame: {points_in_last} points)")

    else:  # 'per_frame' method
        # Sample each frame independently
        for i, edge in enumerate(edges):
            sampled_points = sample_edge_points_xaxis(edge, CONFIG['n_points'],
                                                      CONFIG['exclude_endpoints'])
            sampled_edges.append(sampled_points)

            if (i + 1) % 10 == 0:
                print(f"  Processed {i+1}/{len(edges)} edges")

    return sampled_edges

def save_sampled_edges(sampled_edges, output_dir):
    """Save sampled edge points."""
    os.makedirs(output_dir, exist_ok=True)

    # Save sampled points as pickle
    with open(os.path.join(output_dir, 'sampled_edges.pkl'), 'wb') as f:
        pickle.dump(sampled_edges, f)

    # Save statistics
    stats = {
        'n_frames': len(sampled_edges),
        'n_points_requested': CONFIG['n_points'],
        'points_per_frame': [len(pts) for pts in sampled_edges],
        'exclude_endpoints': CONFIG['exclude_endpoints'],
        'sampling_method': CONFIG['sampling_method'],
        'y_selection': CONFIG['y_selection']
    }

    # Add method-specific information
    if CONFIG['sampling_method'] in ['dense', 'displacement_like']:
        stats['avg_points_per_frame'] = float(np.mean([len(pts) for pts in sampled_edges]))
        stats['min_points_per_frame'] = int(np.min([len(pts) for pts in sampled_edges])) if sampled_edges else 0
        stats['max_points_per_frame'] = int(np.max([len(pts) for pts in sampled_edges])) if sampled_edges else 0

    if CONFIG['sampling_method'] == 'displacement_like':
        stats['target_points_displacement'] = CONFIG.get('target_points_displacement')

    # If using fixed_x method, save the fixed x-positions
    if CONFIG['sampling_method'] == 'fixed_x' and '_fixed_x_positions' in CONFIG:
        stats['fixed_x_positions'] = CONFIG['_fixed_x_positions'].tolist()

    with open(os.path.join(output_dir, 'sampling_statistics.json'), 'w') as f:
        json.dump(stats, f, indent=2)

    print(f"Saved sampled edge data to {output_dir}")

def create_verification_figures(images, masks, edges, sampled_edges, output_dir):
    """Create verification figures showing sampled points with enhanced contrast."""
    print("Creating verification figures...")

    fig_dir = os.path.join(output_dir, 'verification_figures')
    os.makedirs(fig_dir, exist_ok=True)

    for i in range(len(edges)):
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        # Calculate percentile-based contrast limits
        vmin = np.percentile(images[i], 1)
        vmax = np.percentile(images[i], 99.5)

        # Full edge with sampled points on mask
        axes[0].imshow(masks[i], cmap='gray')
        if len(edges[i]) > 0:
            axes[0].plot(edges[i][:, 1], edges[i][:, 0], 'r-', linewidth=1,
                        alpha=0.5, label='Full Edge')
        if len(sampled_edges[i]) > 0:
            # Filter out NaN points
            valid_mask = ~np.isnan(sampled_edges[i][:, 0])
            valid_points = sampled_edges[i][valid_mask]

            axes[0].scatter(valid_points[:, 1], valid_points[:, 0],
                           c='yellow', s=100, marker='o', edgecolors='red',
                           linewidths=2, label='Sampled Points', zorder=5)
            # Number the points
            for j, pt in enumerate(valid_points):
                axes[0].text(pt[1], pt[0], str(np.where(valid_mask)[0][j]),
                           color='black', fontsize=8,
                           ha='center', va='center', weight='bold')
        axes[0].set_title(f'Frame {i}: Sampled Points on Mask ({CONFIG["y_selection"]})\n{np.sum(~np.isnan(sampled_edges[i][:, 0])) if len(sampled_edges[i]) > 0 else 0} valid points')
        axes[0].legend()
        axes[0].axis('off')

        # Full edge with sampled points on image (enhanced contrast)
        axes[1].imshow(images[i], cmap='gray', vmin=vmin, vmax=vmax)
        if len(edges[i]) > 0:
            axes[1].plot(edges[i][:, 1], edges[i][:, 0], 'r-', linewidth=1,
                        alpha=0.5, label='Full Edge')
        if len(sampled_edges[i]) > 0:
            # Filter out NaN points
            valid_mask = ~np.isnan(sampled_edges[i][:, 0])
            valid_points = sampled_edges[i][valid_mask]

            axes[1].scatter(valid_points[:, 1], valid_points[:, 0],
                           c='yellow', s=100, marker='o', edgecolors='red',
                           linewidths=2, label='Sampled Points', zorder=5)
            # Number the points
            for j, pt in enumerate(valid_points):
                axes[1].text(pt[1], pt[0], str(np.where(valid_mask)[0][j]),
                           color='white', fontsize=8,
                           ha='center', va='center', weight='bold',
                           bbox=dict(boxstyle='circle', facecolor='black', alpha=0.5))
        axes[1].set_title(f'Frame {i}: Sampled Points on Image (enhanced contrast, {CONFIG["y_selection"]})')
        axes[1].legend()
        axes[1].axis('off')

        plt.tight_layout()
        plt.savefig(os.path.join(fig_dir, f'frame_{i:03d}_sampling.png'),
                   dpi=150, bbox_inches='tight')
        plt.close()

    # Summary figure showing x-distribution
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))

    # X-positions of sampled points over all frames
    all_x_positions = []
    frame_indices = []
    for i, pts in enumerate(sampled_edges):
        if len(pts) > 0:
            # Filter out NaN points
            valid_mask = ~np.isnan(pts[:, 0])
            valid_pts = pts[valid_mask]
            all_x_positions.extend(valid_pts[:, 1])
            frame_indices.extend([i] * len(valid_pts))

    if all_x_positions:
        axes[0].scatter(frame_indices, all_x_positions, alpha=0.3, s=10)
        axes[0].set_xlabel('Frame Number')
        axes[0].set_ylabel('X Position (pixels)')
        axes[0].set_title(f'X-Positions of Sampled Points Across All Frames\nMethod: {CONFIG["sampling_method"]}, Y-selection: {CONFIG["y_selection"]}')
        axes[0].grid(True, alpha=0.3)

        # Add vertical lines for fixed x-positions if using fixed_x method
        if CONFIG['sampling_method'] == 'fixed_x' and '_fixed_x_positions' in CONFIG:
            for x_pos in CONFIG['_fixed_x_positions']:
                axes[0].axhline(y=x_pos, color='red', linestyle='--', alpha=0.3, linewidth=0.5)

        # Histogram of x-positions
        axes[1].hist(all_x_positions, bins=50, edgecolor='black', alpha=0.7)
        axes[1].set_xlabel('X Position (pixels)')
        axes[1].set_ylabel('Count')
        axes[1].set_title('Distribution of Sampled X-Positions')
        axes[1].grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, 'sampling_summary.png'),
               dpi=150, bbox_inches='tight')
    plt.close()

    print(f"Saved {len(sampled_edges)+1} verification figures")

def main():
    # Parse command line arguments
    parse_arguments()
    
    # Load previous results
    images, masks, edges = load_previous_results()

    # Sample edge points
    sampled_edges = sample_all_edges(edges)

    # Save sampled edges
    save_sampled_edges(sampled_edges, CONFIG['OUTPUT_DIR'])

    # Create verification figures if requested
    if CONFIG['CREATE_VERIFICATION_FIGURES']:
        create_verification_figures(images, masks, edges, sampled_edges, CONFIG['OUTPUT_DIR'])
    else:
        print("Skipping verification figures (CREATE_VERIFICATION_FIGURES=False)")

    print("\nStep 5 complete!")
    print(f"Results saved to: {CONFIG['OUTPUT_DIR']}")

if __name__ == "__main__":
    main()
