#!/usr/bin/env python3
"""
Step 2: Cell Edge Detection
Detects cell edges from masks, saves edge coordinates to step2_results/
"""

import os
import sys
import argparse
import numpy as np
import matplotlib.pyplot as plt
from skimage import measure
from scipy.ndimage import gaussian_filter1d
import pickle
import json

# Configuration
CONFIG = {
    'INPUT_DIR': "step1_results",
    'OUTPUT_DIR': "step2_results",
    'SMOOTH_EDGES': True,  # Apply Gaussian smoothing to edges
    'SMOOTHING_SIGMA': 20.0,  # Sigma for Gaussian smoothing (higher = more smoothing)
    'CREATE_VERIFICATION_FIGURES': True  # Create verification figures
}

def parse_arguments():
    """Parse command line arguments to override CONFIG."""
    parser = argparse.ArgumentParser(description='Step 2: Cell Edge Detection')

    parser.add_argument('--input-dir', type=str,
                        help='Input directory (step1_results)')
    parser.add_argument('--output-dir', type=str,
                        help='Output directory for results')
    parser.add_argument('--smooth-edges', type=lambda x: x.lower() == 'true',
                        help='Apply Gaussian smoothing to edges (true/false)')
    parser.add_argument('--smoothing-sigma', type=float,
                        help='Sigma for Gaussian smoothing (default: 20.0, higher = more smoothing)')
    parser.add_argument('--create-verification-figures', type=lambda x: x.lower() == 'true',
                        help='Create verification figures (true/false)')

    args = parser.parse_args()

    # Override CONFIG with command line arguments
    if args.input_dir is not None:
        CONFIG['INPUT_DIR'] = args.input_dir
    if args.output_dir is not None:
        CONFIG['OUTPUT_DIR'] = args.output_dir
    if args.smooth_edges is not None:
        CONFIG['SMOOTH_EDGES'] = args.smooth_edges
    if args.smoothing_sigma is not None:
        CONFIG['SMOOTHING_SIGMA'] = args.smoothing_sigma
    if args.create_verification_figures is not None:
        CONFIG['CREATE_VERIFICATION_FIGURES'] = args.create_verification_figures

    return args

def load_previous_results():
    """Load data from Step 1."""
    print("Loading Step 1 results...")

    images = np.load(os.path.join(CONFIG['INPUT_DIR'], 'images.npy'))
    masks = np.load(os.path.join(CONFIG['INPUT_DIR'], 'masks.npy'))

    with open(os.path.join(CONFIG['INPUT_DIR'], 'metadata.json'), 'r') as f:
        metadata = json.load(f)

    return images, masks, metadata

def detect_cell_edge(mask):
    """Detect the cell edge from a binary mask."""
    contours = measure.find_contours(mask, 0.5)

    if len(contours) > 0:
        contour = max(contours, key=len)
        return contour
    else:
        return np.array([])

def smooth_edge(edge, sigma):
    """Apply Gaussian smoothing to edge coordinates while preserving endpoints.

    Args:
        edge: Nx2 array of edge coordinates (row, col)
        sigma: Standard deviation for Gaussian kernel

    Returns:
        Smoothed edge coordinates with original endpoints preserved
    """
    if len(edge) == 0:
        return edge

    # Check if edge is a closed contour (first and last points are close)
    is_closed = np.linalg.norm(edge[0] - edge[-1]) < 5  # Within 5 pixels

    if is_closed:
        # For closed contours, use wrap mode
        smoothed_edge = np.zeros_like(edge)
        smoothed_edge[:, 0] = gaussian_filter1d(edge[:, 0], sigma=sigma, mode='wrap')
        smoothed_edge[:, 1] = gaussian_filter1d(edge[:, 1], sigma=sigma, mode='wrap')
    else:
        # For open contours, use reflect mode and preserve endpoints
        smoothed_edge = np.zeros_like(edge)

        # Smooth interior points with reflect mode
        smoothed_edge[:, 0] = gaussian_filter1d(edge[:, 0], sigma=sigma, mode='reflect')
        smoothed_edge[:, 1] = gaussian_filter1d(edge[:, 1], sigma=sigma, mode='reflect')

        # Restore original endpoints to prevent artifacts
        smoothed_edge[0] = edge[0].copy()
        smoothed_edge[-1] = edge[-1].copy()

    return smoothed_edge

def detect_all_edges(masks):
    """Detect edges for all frames."""
    print(f"Detecting edges for {masks.shape[0]} frames...")

    edges = []
    for i in range(masks.shape[0]):
        edge = detect_cell_edge(masks[i])

        # Apply smoothing if requested
        if CONFIG['SMOOTH_EDGES'] and len(edge) > 0:
            edge = smooth_edge(edge, CONFIG['SMOOTHING_SIGMA'])

        edges.append(edge)
        if (i + 1) % 10 == 0:
            print(f"  Processed {i+1}/{masks.shape[0]} frames")

    if CONFIG['SMOOTH_EDGES']:
        print(f"Applied Gaussian smoothing (sigma={CONFIG['SMOOTHING_SIGMA']})")

    return edges

def save_edges(edges, output_dir):
    """Save edge coordinates."""
    os.makedirs(output_dir, exist_ok=True)

    # Save edges as pickle
    with open(os.path.join(output_dir, 'edges.pkl'), 'wb') as f:
        pickle.dump(edges, f)

    # Save edge statistics
    stats = {
        'n_frames': len(edges),
        'edge_points_per_frame': [len(edge) for edge in edges],
        'mean_edge_points': float(np.mean([len(edge) for edge in edges])),
        'std_edge_points': float(np.std([len(edge) for edge in edges])),
        'smoothed': CONFIG['SMOOTH_EDGES'],
        'smoothing_sigma': CONFIG['SMOOTHING_SIGMA'] if CONFIG['SMOOTH_EDGES'] else None
    }

    with open(os.path.join(output_dir, 'edge_statistics.json'), 'w') as f:
        json.dump(stats, f, indent=2)

    print(f"Saved edge data to {output_dir}")

def create_verification_figures(images, masks, edges, output_dir):
    """Create verification figures showing detected edges with enhanced contrast."""
    print("Creating verification figures...")

    fig_dir = os.path.join(output_dir, 'verification_figures')
    os.makedirs(fig_dir, exist_ok=True)

    for i in range(len(edges)):
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))

        # Calculate percentile-based contrast limits for better visualization
        vmin = np.percentile(images[i], 1)  # 1st percentile
        vmax = np.percentile(images[i], 99.5)  # 99.5th percentile

        # Edge on mask
        axes[0].imshow(masks[i], cmap='gray')
        if len(edges[i]) > 0:
            axes[0].plot(edges[i][:, 1], edges[i][:, 0], 'r-', linewidth=2, label='Detected Edge')
        axes[0].set_title(f'Frame {i}: Edge on Mask\n{len(edges[i])} edge points')
        axes[0].legend()
        axes[0].axis('off')

        # Edge on image with enhanced contrast
        axes[1].imshow(images[i], cmap='gray', vmin=vmin, vmax=vmax)
        if len(edges[i]) > 0:
            axes[1].plot(edges[i][:, 1], edges[i][:, 0], 'r-', linewidth=2, label='Detected Edge')
        axes[1].set_title(f'Frame {i}: Edge on Image (enhanced contrast)')
        axes[1].legend()
        axes[1].axis('off')

        plt.tight_layout()
        plt.savefig(os.path.join(fig_dir, f'frame_{i:03d}_edge_detection.png'),
                   dpi=150, bbox_inches='tight')
        plt.close()

    print(f"Saved {len(edges)} verification figures")

def main():
    # Parse command line arguments
    parse_arguments()

    # Load previous results
    images, masks, metadata = load_previous_results()

    # Detect edges
    edges = detect_all_edges(masks)

    # Save edges
    save_edges(edges, CONFIG['OUTPUT_DIR'])

    # Create verification figures if requested
    if CONFIG['CREATE_VERIFICATION_FIGURES']:
        create_verification_figures(images, masks, edges, CONFIG['OUTPUT_DIR'])
    else:
        print("Skipping verification figures (CREATE_VERIFICATION_FIGURES=False)")

    print("\nStep 2 complete!")
    print(f"Results saved to: {CONFIG['OUTPUT_DIR']}")

if __name__ == "__main__":
    main()
