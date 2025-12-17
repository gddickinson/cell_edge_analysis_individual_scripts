#!/usr/bin/env python3
"""
Step 3: Vertical Displacement Calculation
Calculates vertical displacement at every x-position between consecutive frames.
Saves to step3_results/
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
    'OUTPUT_DIR': "step3_results",
    'min_movement_pixels': 5,  # Minimum valid displacements needed
    'ARROW_SCALE': 1,  # Scale factor for displacement arrows in visualization
    'ARROW_HEAD_WIDTH': 40,  # Width of arrow head in pixels
    'ARROW_HEAD_LENGTH': 15,  # Length of arrow head in pixels
    'ARROW_POINT_FORWARD': True,  # True: arrows point in direction of movement, False: point to previous position
    'CREATE_VERIFICATION_FIGURES': True  # Create verification figures
}

def parse_arguments():
    """Parse command line arguments to override CONFIG."""
    parser = argparse.ArgumentParser(description='Step 3: Vertical Displacement Calculation')
    
    parser.add_argument('--input-dir-step1', type=str,
                        help='Input directory from step 1')
    parser.add_argument('--input-dir-step2', type=str,
                        help='Input directory from step 2')
    parser.add_argument('--output-dir', type=str,
                        help='Output directory for results')
    parser.add_argument('--min-movement-pixels', type=int,
                        help='Minimum valid displacements needed')
    parser.add_argument('--arrow-scale', type=float,
                        help='Scale factor for displacement arrows')
    parser.add_argument('--arrow-head-width', type=float,
                        help='Width of arrow head in pixels')
    parser.add_argument('--arrow-head-length', type=float,
                        help='Length of arrow head in pixels')
    parser.add_argument('--arrow-point-forward', type=lambda x: x.lower() == 'true',
                        help='Arrow direction (true/false)')
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
    if args.min_movement_pixels is not None:
        CONFIG['min_movement_pixels'] = args.min_movement_pixels
    if args.arrow_scale is not None:
        CONFIG['ARROW_SCALE'] = args.arrow_scale
    if args.arrow_head_width is not None:
        CONFIG['ARROW_HEAD_WIDTH'] = args.arrow_head_width
    if args.arrow_head_length is not None:
        CONFIG['ARROW_HEAD_LENGTH'] = args.arrow_head_length
    if args.arrow_point_forward is not None:
        CONFIG['ARROW_POINT_FORWARD'] = args.arrow_point_forward
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

def calculate_displacement_map(current_contour, previous_contour):
    """
    Calculate vertical displacement at every x-position.
    Returns x_positions and corresponding displacements.
    """
    # Get x-range spanning both frames
    x_min = int(min(np.min(current_contour[:, 1]), np.min(previous_contour[:, 1])))
    x_max = int(max(np.max(current_contour[:, 1]), np.max(previous_contour[:, 1])))

    # Create arrays for every x-position
    x_positions = np.arange(x_min, x_max + 1)
    displacements = np.full(len(x_positions), np.nan, dtype=float)

    # For each x position, find uppermost (minimum y) points
    for i, x in enumerate(x_positions):
        # Previous frame: find uppermost point at this x
        prev_mask = np.abs(previous_contour[:, 1] - x) < 0.5
        if np.any(prev_mask):
            prev_y = np.min(previous_contour[prev_mask, 0])
        else:
            prev_y = None

        # Current frame: find uppermost point at this x
        curr_mask = np.abs(current_contour[:, 1] - x) < 0.5
        if np.any(curr_mask):
            curr_y = np.min(current_contour[curr_mask, 0])
        else:
            curr_y = None

        # Calculate displacement if both exist
        if prev_y is not None and curr_y is not None:
            displacements[i] = curr_y - prev_y  # Positive = down, negative = up

    return x_positions, displacements

def calculate_all_displacements(edges):
    """Calculate displacements for all frame pairs."""
    print(f"Calculating displacements for {len(edges)-1} frame pairs...")

    displacement_data = []

    for i in range(len(edges) - 1):
        if len(edges[i]) > 0 and len(edges[i+1]) > 0:
            x_positions, displacements = calculate_displacement_map(edges[i+1], edges[i])

            # Calculate statistics
            valid_displacements = displacements[~np.isnan(displacements)]

            if len(valid_displacements) > CONFIG['min_movement_pixels']:
                avg_displacement = np.mean(valid_displacements)
                std_displacement = np.std(valid_displacements)
                n_valid = len(valid_displacements)
            else:
                avg_displacement = 0.0
                std_displacement = 0.0
                n_valid = 0

            displacement_data.append({
                'frame_pair': (i, i+1),
                'x_positions': x_positions,
                'displacements': displacements,
                'avg_displacement': avg_displacement,
                'std_displacement': std_displacement,
                'n_valid': n_valid
            })
        else:
            displacement_data.append({
                'frame_pair': (i, i+1),
                'x_positions': np.array([]),
                'displacements': np.array([]),
                'avg_displacement': 0.0,
                'std_displacement': 0.0,
                'n_valid': 0
            })

        if (i + 1) % 10 == 0:
            print(f"  Processed {i+1}/{len(edges)-1} frame pairs")

    return displacement_data

def save_displacement_data(displacement_data, output_dir):
    """Save displacement data."""
    os.makedirs(output_dir, exist_ok=True)

    # Save full data as pickle
    with open(os.path.join(output_dir, 'displacement_data.pkl'), 'wb') as f:
        pickle.dump(displacement_data, f)

    # Save summary statistics
    stats = {
        'n_frame_pairs': len(displacement_data),
        'avg_displacements': [d['avg_displacement'] for d in displacement_data],
        'std_displacements': [d['std_displacement'] for d in displacement_data],
        'n_valid_per_pair': [d['n_valid'] for d in displacement_data],
        'overall_mean_displacement': float(np.mean([d['avg_displacement'] for d in displacement_data])),
        'overall_std_displacement': float(np.std([d['avg_displacement'] for d in displacement_data]))
    }

    with open(os.path.join(output_dir, 'displacement_statistics.json'), 'w') as f:
        json.dump(stats, f, indent=2)

    print(f"Saved displacement data to {output_dir}")

def create_verification_figures(images, edges, displacement_data, output_dir):
    """Create verification figures showing displacement maps with enhanced contrast."""
    print("Creating verification figures...")

    fig_dir = os.path.join(output_dir, 'verification_figures')
    os.makedirs(fig_dir, exist_ok=True)

    for i, data in enumerate(displacement_data):
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # Calculate percentile-based contrast limits for better visualization
        vmin_i = np.percentile(images[i], 1)  # 1st percentile for frame i
        vmax_i = np.percentile(images[i], 99.5)  # 99.5th percentile for frame i
        vmin_i1 = np.percentile(images[i+1], 1)  # 1st percentile for frame i+1
        vmax_i1 = np.percentile(images[i+1], 99.5)  # 99.5th percentile for frame i+1

        # Frame pair with edges (enhanced contrast)
        axes[0, 0].imshow(images[i], cmap='gray', alpha=0.5, vmin=vmin_i, vmax=vmax_i)
        if len(edges[i]) > 0:
            axes[0, 0].plot(edges[i][:, 1], edges[i][:, 0], 'b-', linewidth=2, label=f'Frame {i}')
        if len(edges[i+1]) > 0:
            axes[0, 0].plot(edges[i+1][:, 1], edges[i+1][:, 0], 'r-', linewidth=2, label=f'Frame {i+1}')
        axes[0, 0].set_title(f'Frame Pair {i}→{i+1}: Edge Overlay (enhanced contrast)')
        axes[0, 0].legend()
        axes[0, 0].axis('off')

        # Displacement map
        x_pos = data['x_positions']
        disp = data['displacements']
        valid_mask = ~np.isnan(disp)

        if np.any(valid_mask):
            scatter = axes[0, 1].scatter(x_pos[valid_mask], disp[valid_mask],
                                        c=disp[valid_mask], cmap='RdBu_r',
                                        vmin=-5, vmax=5, s=20)
            axes[0, 1].axhline(y=0, color='k', linestyle='--', linewidth=1)
            axes[0, 1].set_xlabel('X Position (pixels)')
            axes[0, 1].set_ylabel('Vertical Displacement (pixels)')
            axes[0, 1].set_title(f'Displacement Map\nAvg: {data["avg_displacement"]:.2f}px, Valid: {data["n_valid"]}')
            plt.colorbar(scatter, ax=axes[0, 1], label='Displacement (px)')
            axes[0, 1].grid(True, alpha=0.3)
        else:
            axes[0, 1].text(0.5, 0.5, 'No valid displacements',
                           ha='center', va='center', transform=axes[0, 1].transAxes)
            axes[0, 1].set_title('Displacement Map')

        # Displacement histogram
        if np.any(valid_mask):
            axes[1, 0].hist(disp[valid_mask], bins=30, edgecolor='black', alpha=0.7)
            axes[1, 0].axvline(x=data['avg_displacement'], color='r',
                              linestyle='--', linewidth=2, label='Mean')
            axes[1, 0].set_xlabel('Displacement (pixels)')
            axes[1, 0].set_ylabel('Count')
            axes[1, 0].set_title('Displacement Distribution')
            axes[1, 0].legend()
            axes[1, 0].grid(True, alpha=0.3)
        else:
            axes[1, 0].text(0.5, 0.5, 'No valid displacements',
                           ha='center', va='center', transform=axes[1, 0].transAxes)
            axes[1, 0].set_title('Displacement Distribution')

        # Displacement profile with arrows showing direction (enhanced contrast)
        axes[1, 1].imshow(images[i+1], cmap='gray', alpha=0.5, vmin=vmin_i1, vmax=vmax_i1)
        if len(edges[i+1]) > 0:
            axes[1, 1].plot(edges[i+1][:, 1], edges[i+1][:, 0], 'r-', linewidth=1, alpha=0.5)

        # Plot arrows for every 10th x-position to avoid clutter
        if np.any(valid_mask):
            step = max(1, len(x_pos) // 20)
            for j in range(0, len(x_pos), step):
                if valid_mask[j]:
                    x = x_pos[j]
                    # Find corresponding y on current edge
                    curr_mask = np.abs(edges[i+1][:, 1] - x) < 0.5
                    if np.any(curr_mask):
                        y = np.min(edges[i+1][curr_mask, 0])
                        dy = disp[j]
                        color = 'blue' if dy < 0 else 'red'
                        # Arrow direction: positive dy for forward (direction of movement), negative for backward
                        arrow_dy = dy if CONFIG['ARROW_POINT_FORWARD'] else -dy
                        axes[1, 1].arrow(x, y, 0, arrow_dy*CONFIG['ARROW_SCALE'],
                                        head_width=CONFIG['ARROW_HEAD_WIDTH'],
                                        head_length=CONFIG['ARROW_HEAD_LENGTH'],
                                        fc=color, ec=color, alpha=0.6, width=1)

        direction_text = "showing movement direction" if CONFIG['ARROW_POINT_FORWARD'] else "pointing to previous position"
        axes[1, 1].set_title(f'Displacement Arrows ({CONFIG["ARROW_SCALE"]}x scale, {direction_text})\nBlue=Extending, Red=Retracting')
        axes[1, 1].axis('off')

        plt.tight_layout()
        plt.savefig(os.path.join(fig_dir, f'frame_pair_{i:03d}_displacement.png'),
                   dpi=150, bbox_inches='tight')
        plt.close()

    print(f"Saved {len(displacement_data)} verification figures")

def main():
    # Parse command line arguments
    parse_arguments()
    
    # Load previous results
    images, masks, edges = load_previous_results()

    # Calculate displacements
    displacement_data = calculate_all_displacements(edges)

    # Save displacement data
    save_displacement_data(displacement_data, CONFIG['OUTPUT_DIR'])

    # Create verification figures if requested
    if CONFIG['CREATE_VERIFICATION_FIGURES']:
        create_verification_figures(images, edges, displacement_data, CONFIG['OUTPUT_DIR'])
    else:
        print("Skipping verification figures (CREATE_VERIFICATION_FIGURES=False)")

    print("\nStep 3 complete!")
    print(f"Results saved to: {CONFIG['OUTPUT_DIR']}")

if __name__ == "__main__":
    main()
