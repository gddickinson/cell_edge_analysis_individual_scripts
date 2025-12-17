#!/usr/bin/env python3
"""
Step 4: Movement Classification
Classifies each frame pair as extruding/retracting/stable based on displacement.
Saves to step4_results/
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
    'INPUT_DIR_STEP3': "step3_results",
    'OUTPUT_DIR': "step4_results",
    'movement_threshold': 5,  # Threshold in pixels
    # Visualization options
    'SHOW_EDGES': True,  # Show cell edges on images
    'SHOW_ARROWS': True,  # Show displacement arrows on images
    'ARROW_SCALE': 1,  # Scale factor for displacement arrows
    'ARROW_HEAD_WIDTH': 20,  # Width of arrow head in pixels
    'ARROW_HEAD_LENGTH': 10,  # Length of arrow head in pixels
    'ARROW_POINT_FORWARD': True,  # True: arrows point in direction of movement
    'CREATE_VERIFICATION_FIGURES': True  # Create verification figures
}

def parse_arguments():
    """Parse command line arguments to override CONFIG."""
    parser = argparse.ArgumentParser(description='Step 4: Movement Classification')
    
    parser.add_argument('--input-dir-step1', type=str,
                        help='Input directory from step 1')
    parser.add_argument('--input-dir-step2', type=str,
                        help='Input directory from step 2')
    parser.add_argument('--input-dir-step3', type=str,
                        help='Input directory from step 3')
    parser.add_argument('--output-dir', type=str,
                        help='Output directory for results')
    parser.add_argument('--movement-threshold', type=float,
                        help='Movement threshold in pixels')
    parser.add_argument('--show-edges', type=lambda x: x.lower() == 'true',
                        help='Show cell edges (true/false)')
    parser.add_argument('--show-arrows', type=lambda x: x.lower() == 'true',
                        help='Show displacement arrows (true/false)')
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
    if args.input_dir_step3 is not None:
        CONFIG['INPUT_DIR_STEP3'] = args.input_dir_step3
    if args.output_dir is not None:
        CONFIG['OUTPUT_DIR'] = args.output_dir
    if args.movement_threshold is not None:
        CONFIG['movement_threshold'] = args.movement_threshold
    if args.show_edges is not None:
        CONFIG['SHOW_EDGES'] = args.show_edges
    if args.show_arrows is not None:
        CONFIG['SHOW_ARROWS'] = args.show_arrows
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
    """Load data from Steps 1, 2, and 3."""
    print("Loading previous results...")

    images = np.load(os.path.join(CONFIG['INPUT_DIR_STEP1'], 'images.npy'))

    with open(os.path.join(CONFIG['INPUT_DIR_STEP2'], 'edges.pkl'), 'rb') as f:
        edges = pickle.load(f)

    with open(os.path.join(CONFIG['INPUT_DIR_STEP3'], 'displacement_data.pkl'), 'rb') as f:
        displacement_data = pickle.load(f)

    return images, edges, displacement_data

def classify_movement(avg_displacement, threshold):
    """Classify movement type based on average displacement."""
    if avg_displacement < -threshold:
        return 'extruding'
    elif avg_displacement > threshold:
        return 'retracting'
    else:
        return 'stable'

def classify_all_movements(displacement_data):
    """Classify movement for all frame pairs."""
    print(f"Classifying movement for {len(displacement_data)} frame pairs...")

    classifications = []

    for data in displacement_data:
        movement_type = classify_movement(data['avg_displacement'],
                                         CONFIG['movement_threshold'])

        classifications.append({
            'frame_pair': data['frame_pair'],
            'avg_displacement': data['avg_displacement'],
            'std_displacement': data['std_displacement'],
            'n_valid': data['n_valid'],
            'movement_type': movement_type
        })

    return classifications

def save_classifications(classifications, output_dir):
    """Save classification results."""
    os.makedirs(output_dir, exist_ok=True)

    # Save full data as pickle
    with open(os.path.join(output_dir, 'movement_classifications.pkl'), 'wb') as f:
        pickle.dump(classifications, f)

    # Count movement types
    movement_types = [c['movement_type'] for c in classifications]
    extruding_count = movement_types.count('extruding')
    retracting_count = movement_types.count('retracting')
    stable_count = movement_types.count('stable')

    # Save summary statistics
    stats = {
        'n_frame_pairs': len(classifications),
        'extruding_count': extruding_count,
        'retracting_count': retracting_count,
        'stable_count': stable_count,
        'extruding_percent': float(extruding_count / len(classifications) * 100),
        'retracting_percent': float(retracting_count / len(classifications) * 100),
        'stable_percent': float(stable_count / len(classifications) * 100),
        'avg_displacements': [c['avg_displacement'] for c in classifications],
        'movement_types': movement_types
    }

    with open(os.path.join(output_dir, 'classification_statistics.json'), 'w') as f:
        json.dump(stats, f, indent=2)

    print(f"Saved classification data to {output_dir}")
    print(f"  Extruding: {extruding_count} ({extruding_count/len(classifications)*100:.1f}%)")
    print(f"  Retracting: {retracting_count} ({retracting_count/len(classifications)*100:.1f}%)")
    print(f"  Stable: {stable_count} ({stable_count/len(classifications)*100:.1f}%)")

def create_verification_figures(images, edges, displacement_data, classifications, output_dir):
    """Create verification figures showing movement classification with enhanced contrast."""
    print("Creating verification figures...")

    fig_dir = os.path.join(output_dir, 'verification_figures')
    os.makedirs(fig_dir, exist_ok=True)

    # Color mapping
    color_map = {
        'extruding': 'blue',
        'retracting': 'red',
        'stable': 'gray'
    }

    # Individual frame pair figures
    for i, cls in enumerate(classifications):
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))

        # Frame pair with enhanced contrast
        frame_idx = cls['frame_pair'][1]

        # Calculate percentile-based contrast limits
        vmin = np.percentile(images[frame_idx], 1)
        vmax = np.percentile(images[frame_idx], 99.5)

        axes[0].imshow(images[frame_idx], cmap='gray', vmin=vmin, vmax=vmax)

        # Optionally show edges
        if CONFIG['SHOW_EDGES']:
            prev_idx = cls['frame_pair'][0]
            if len(edges[prev_idx]) > 0:
                axes[0].plot(edges[prev_idx][:, 1], edges[prev_idx][:, 0],
                           'b-', linewidth=1.5, alpha=0.7, label=f'Frame {prev_idx}')
            if len(edges[frame_idx]) > 0:
                axes[0].plot(edges[frame_idx][:, 1], edges[frame_idx][:, 0],
                           'r-', linewidth=1.5, alpha=0.7, label=f'Frame {frame_idx}')
            axes[0].legend(loc='upper right')

        # Optionally show arrows
        if CONFIG['SHOW_ARROWS'] and i < len(displacement_data):
            data = displacement_data[i]
            x_pos = data['x_positions']
            disp = data['displacements']
            valid_mask = ~np.isnan(disp)
            prev_idx = cls['frame_pair'][0]

            if np.any(valid_mask) and len(edges[frame_idx]) > 0 and len(edges[prev_idx]) > 0:
                # Plot arrows for every 20th x-position to avoid clutter
                step = max(1, len(x_pos) // 20)
                for j in range(0, len(x_pos), step):
                    if valid_mask[j]:
                        x = x_pos[j]
                        # Find corresponding y on previous edge
                        prev_mask = np.abs(edges[prev_idx][:, 1] - x) < 0.5
                        # Find corresponding y on current edge
                        curr_mask = np.abs(edges[frame_idx][:, 1] - x) < 0.5

                        if np.any(prev_mask) and np.any(curr_mask):
                            y_prev = np.min(edges[prev_idx][prev_mask, 0])
                            y_curr = np.min(edges[frame_idx][curr_mask, 0])
                            dy = disp[j]
                            arrow_color = 'cyan' if dy < 0 else 'yellow'

                            # Arrow from previous to current position
                            if CONFIG['ARROW_POINT_FORWARD']:
                                # Arrow points from previous frame to current frame
                                axes[0].arrow(x, y_prev, 0, (y_curr - y_prev)*CONFIG['ARROW_SCALE'],
                                            head_width=CONFIG['ARROW_HEAD_WIDTH'],
                                            head_length=CONFIG['ARROW_HEAD_LENGTH'],
                                            fc=arrow_color, ec=arrow_color, alpha=0.8, width=1.5)
                            else:
                                # Arrow points from current frame to previous frame
                                axes[0].arrow(x, y_curr, 0, (y_prev - y_curr)*CONFIG['ARROW_SCALE'],
                                            head_width=CONFIG['ARROW_HEAD_WIDTH'],
                                            head_length=CONFIG['ARROW_HEAD_LENGTH'],
                                            fc=arrow_color, ec=arrow_color, alpha=0.8, width=1.5)

        axes[0].set_title(f'Frame {frame_idx} (enhanced contrast)')
        axes[0].axis('off')

        # Classification info
        color = color_map[cls['movement_type']]
        axes[1].axis('off')
        axes[1].set_xlim(0, 1)
        axes[1].set_ylim(0, 1)

        info_text = f"Frame Pair: {cls['frame_pair'][0]} → {cls['frame_pair'][1]}\n\n"
        info_text += f"Movement Type: {cls['movement_type'].upper()}\n\n"
        info_text += f"Avg Displacement: {cls['avg_displacement']:.3f} px\n"
        info_text += f"Std Displacement: {cls['std_displacement']:.3f} px\n"
        info_text += f"Valid Points: {cls['n_valid']}\n\n"
        info_text += f"Threshold: ±{CONFIG['movement_threshold']} px\n\n"

        if cls['movement_type'] == 'extruding':
            info_text += "Interpretation:\nCell edge moving UP/OUT\n(negative displacement)"
        elif cls['movement_type'] == 'retracting':
            info_text += "Interpretation:\nCell edge moving DOWN/IN\n(positive displacement)"
        else:
            info_text += "Interpretation:\nMinimal edge movement"

        axes[1].text(0.5, 0.5, info_text,
                    ha='center', va='center', fontsize=12,
                    bbox=dict(boxstyle='round', facecolor=color, alpha=0.3))

        plt.tight_layout()
        plt.savefig(os.path.join(fig_dir, f'frame_pair_{i:03d}_classification.png'),
                   dpi=150, bbox_inches='tight')
        plt.close()

    # Summary figure
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))

    # Time series of displacement
    frame_pairs = [c['frame_pair'][0] for c in classifications]
    displacements = [c['avg_displacement'] for c in classifications]
    colors = [color_map[c['movement_type']] for c in classifications]

    axes[0].scatter(frame_pairs, displacements, c=colors, s=50, alpha=0.6)
    axes[0].axhline(y=CONFIG['movement_threshold'], color='k',
                   linestyle='--', linewidth=1, label='Threshold')
    axes[0].axhline(y=-CONFIG['movement_threshold'], color='k',
                   linestyle='--', linewidth=1)
    axes[0].axhline(y=0, color='k', linestyle='-', linewidth=0.5)
    axes[0].set_xlabel('Frame Number')
    axes[0].set_ylabel('Average Displacement (pixels)')
    axes[0].set_title('Movement Classification Over Time')
    axes[0].legend(['Threshold', 'Extruding', 'Retracting', 'Stable'])
    axes[0].grid(True, alpha=0.3)

    # Movement type distribution
    movement_types = [c['movement_type'] for c in classifications]
    type_counts = {
        'extruding': movement_types.count('extruding'),
        'retracting': movement_types.count('retracting'),
        'stable': movement_types.count('stable')
    }

    bars = axes[1].bar(type_counts.keys(), type_counts.values(),
                      color=[color_map[t] for t in type_counts.keys()], alpha=0.6)
    axes[1].set_ylabel('Count')
    axes[1].set_title('Movement Type Distribution')
    axes[1].grid(True, alpha=0.3, axis='y')

    # Add percentage labels on bars
    for bar in bars:
        height = bar.get_height()
        axes[1].text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}\n({height/len(classifications)*100:.1f}%)',
                    ha='center', va='bottom')

    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, 'classification_summary.png'),
               dpi=150, bbox_inches='tight')
    plt.close()

    print(f"Saved {len(classifications)+1} verification figures")

def main():
    # Parse command line arguments
    parse_arguments()
    
    # Load previous results
    images, edges, displacement_data = load_previous_results()

    # Classify movements
    classifications = classify_all_movements(displacement_data)

    # Save classifications
    save_classifications(classifications, CONFIG['OUTPUT_DIR'])

    # Create verification figures if requested
    if CONFIG['CREATE_VERIFICATION_FIGURES']:
        create_verification_figures(images, edges, displacement_data, classifications, CONFIG['OUTPUT_DIR'])
    else:
        print("Skipping verification figures (CREATE_VERIFICATION_FIGURES=False)")

    print("\nStep 4 complete!")
    print(f"Results saved to: {CONFIG['OUTPUT_DIR']}")

if __name__ == "__main__":
    main()
