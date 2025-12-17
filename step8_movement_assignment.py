#!/usr/bin/env python3
"""
Step 8: Local Movement Assignment
Assigns local displacement values to each sampling point based on x-position.
Saves to step8_results/
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
    'INPUT_DIR_STEP3': "step3_results",
    'INPUT_DIR_STEP7': "step7_results",
    'OUTPUT_DIR': "step8_results",
    'temporal_direction': 'past'  # 'past' or 'future'
,
    'CREATE_VERIFICATION_FIGURES': True  # Create verification figures
}

def load_previous_results():
    """Load data from previous steps."""
    print("Loading previous results...")

    with open(os.path.join(CONFIG['INPUT_DIR_STEP3'], 'displacement_data.pkl'), 'rb') as f:
        displacement_data = pickle.load(f)

    with open(os.path.join(CONFIG['INPUT_DIR_STEP7'], 'intensity_data.pkl'), 'rb') as f:
        intensity_data = pickle.load(f)

    return displacement_data, intensity_data


def parse_arguments():
    """Parse command line arguments to override CONFIG."""
    parser = argparse.ArgumentParser(description='Step 8: Local Movement Assignment')
    
    parser.add_argument('--input-dir-step3', type=str,
                        help='Input directory from step 3')
    parser.add_argument('--input-dir-step7', type=str,
                        help='Input directory from step 7')
    parser.add_argument('--output-dir', type=str,
                        help='Output directory for results')
    parser.add_argument('--temporal-direction', type=str,
                        choices=['past', 'future'],
                        help='Temporal direction (past/future)')
    parser.add_argument('--create-verification-figures', type=lambda x: x.lower() == 'true',
                        help='Create verification figures (true/false)')
    
    args = parser.parse_args()
    
    # Override CONFIG with command line arguments
    if args.input_dir_step3 is not None:
        CONFIG['INPUT_DIR_STEP3'] = args.input_dir_step3
    if args.input_dir_step7 is not None:
        CONFIG['INPUT_DIR_STEP7'] = args.input_dir_step7
    if args.output_dir is not None:
        CONFIG['OUTPUT_DIR'] = args.output_dir
    if args.temporal_direction is not None:
        CONFIG['temporal_direction'] = args.temporal_direction
    if args.create_verification_figures is not None:
        CONFIG['CREATE_VERIFICATION_FIGURES'] = args.create_verification_figures
    
    return args

def assign_displacement_to_point(x_position, displacement_data):
    """Assign local displacement based on x-position."""
    x_positions = displacement_data['x_positions']
    displacements = displacement_data['displacements']

    # Find closest x-position
    if len(x_positions) == 0:
        return np.nan, False

    distances = np.abs(x_positions - x_position)
    closest_idx = np.argmin(distances)

    # Check if displacement is valid
    displacement = displacements[closest_idx]
    is_valid = not np.isnan(displacement)

    return displacement, is_valid

def assign_all_movements(displacement_data, intensity_data, temporal_direction):
    """Assign movements to all sampling points."""
    print(f"Assigning movements with temporal direction: {temporal_direction}")
    print(f"Processing {len(intensity_data)} frames...")

    combined_data = []

    # Match frames based on temporal direction
    for i in range(len(intensity_data)):
        if temporal_direction == 'past':
            # Frame i intensity compared with movement from i-1 to i
            if i == 0:
                continue  # Skip first frame (no previous movement)
            disp_idx = i - 1
            intensity_idx = i
        else:  # 'future'
            # Frame i intensity compared with movement from i to i+1
            if i >= len(displacement_data):
                continue  # Skip last frame (no future movement)
            disp_idx = i
            intensity_idx = i

        # Get displacement data for this pair
        if disp_idx >= len(displacement_data):
            continue

        disp_data = displacement_data[disp_idx]
        int_data = intensity_data[intensity_idx]

        frame_combined = []

        for point in int_data:
            if point['accepted'] and not np.isnan(point['intensity']):
                x_pos = point['edge_point'][1]

                # Assign displacement
                displacement, is_valid = assign_displacement_to_point(x_pos, disp_data)

                frame_combined.append({
                    'frame_idx': intensity_idx,
                    'displacement_pair': disp_data['frame_pair'],
                    'point_index': point['point_index'],
                    'x_position': x_pos,
                    'y_position': point['edge_point'][0],
                    'intensity': point['intensity'],
                    'displacement': displacement,
                    'valid': is_valid
                })

        combined_data.append(frame_combined)

        if (i + 1) % 10 == 0:
            print(f"  Processed {i+1}/{len(intensity_data)} frames")

    return combined_data

def save_combined_data(combined_data, output_dir):
    """Save combined movement-intensity data."""
    os.makedirs(output_dir, exist_ok=True)

    # Save full data as pickle
    with open(os.path.join(output_dir, 'combined_data.pkl'), 'wb') as f:
        pickle.dump(combined_data, f)

    # Flatten data for statistics
    all_points = []
    for frame_data in combined_data:
        all_points.extend(frame_data)

    valid_points = [p for p in all_points if p['valid']]

    stats = {
        'n_frames': len(combined_data),
        'total_points': len(all_points),
        'valid_points': len(valid_points),
        'invalid_points': len(all_points) - len(valid_points),
        'temporal_direction': CONFIG['temporal_direction']
    }

    if valid_points:
        stats['mean_displacement'] = float(np.mean([p['displacement'] for p in valid_points]))
        stats['std_displacement'] = float(np.std([p['displacement'] for p in valid_points]))
        stats['mean_intensity'] = float(np.mean([p['intensity'] for p in valid_points]))
        stats['std_intensity'] = float(np.std([p['intensity'] for p in valid_points]))

    with open(os.path.join(output_dir, 'combined_statistics.json'), 'w') as f:
        json.dump(stats, f, indent=2)

    print(f"Saved combined data to {output_dir}")
    print(f"  Valid points: {len(valid_points)}/{len(all_points)}")

def create_verification_figures(combined_data, output_dir):
    """Create verification figures showing movement-intensity pairs."""
    print("Creating verification figures...")

    fig_dir = os.path.join(output_dir, 'verification_figures')
    os.makedirs(fig_dir, exist_ok=True)

    # Individual frame figures
    for i, frame_data in enumerate(combined_data):
        if len(frame_data) == 0:
            continue

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        valid_data = [p for p in frame_data if p['valid']]

        if not valid_data:
            fig.text(0.5, 0.5, 'No valid data for this frame',
                    ha='center', va='center', fontsize=14)
            plt.savefig(os.path.join(fig_dir, f'frame_{i:03d}_combined.png'),
                       dpi=150, bbox_inches='tight')
            plt.close()
            continue

        frame_idx = valid_data[0]['frame_idx']
        disp_pair = valid_data[0]['displacement_pair']

        # Scatter: Displacement vs X-position
        x_pos = [p['x_position'] for p in valid_data]
        displacements = [p['displacement'] for p in valid_data]

        scatter1 = axes[0, 0].scatter(x_pos, displacements,
                                     c=displacements, cmap='RdBu_r',
                                     s=100, edgecolors='black', linewidth=1,
                                     vmin=-2, vmax=2)
        axes[0, 0].axhline(y=0, color='k', linestyle='--', linewidth=1)
        axes[0, 0].set_xlabel('X Position (pixels)')
        axes[0, 0].set_ylabel('Displacement (pixels)')
        axes[0, 0].set_title(f'Frame {frame_idx}: Displacement vs X-Position\n' +
                            f'Movement: {disp_pair[0]}→{disp_pair[1]}')
        axes[0, 0].grid(True, alpha=0.3)
        plt.colorbar(scatter1, ax=axes[0, 0], label='Displacement')

        # Scatter: Intensity vs X-position
        intensities = [p['intensity'] for p in valid_data]

        scatter2 = axes[0, 1].scatter(x_pos, intensities,
                                     c=intensities, cmap='viridis',
                                     s=100, edgecolors='black', linewidth=1)
        axes[0, 1].set_xlabel('X Position (pixels)')
        axes[0, 1].set_ylabel('Intensity')
        axes[0, 1].set_title(f'Frame {frame_idx}: Intensity vs X-Position')
        axes[0, 1].grid(True, alpha=0.3)
        plt.colorbar(scatter2, ax=axes[0, 1], label='Intensity')

        # Key plot: Intensity vs Displacement
        scatter3 = axes[1, 0].scatter(displacements, intensities,
                                     c=displacements, cmap='RdBu_r',
                                     s=100, edgecolors='black', linewidth=1,
                                     vmin=-2, vmax=2, alpha=0.6)
        axes[1, 0].axvline(x=0, color='k', linestyle='--', linewidth=1)
        axes[1, 0].set_xlabel('Displacement (pixels)')
        axes[1, 0].set_ylabel('Intensity')
        axes[1, 0].set_title('Intensity vs Displacement')
        axes[1, 0].grid(True, alpha=0.3)
        plt.colorbar(scatter3, ax=axes[1, 0], label='Displacement')

        # Statistics table
        axes[1, 1].axis('off')
        stats_text = f"Frame Statistics:\n\n"
        stats_text += f"Frame: {frame_idx}\n"
        stats_text += f"Movement: {disp_pair[0]} → {disp_pair[1]}\n"
        stats_text += f"Direction: {CONFIG['temporal_direction']}\n\n"
        stats_text += f"Valid Points: {len(valid_data)}\n"
        stats_text += f"Total Points: {len(frame_data)}\n\n"
        stats_text += f"Displacement:\n"
        stats_text += f"  Mean: {np.mean(displacements):.3f} px\n"
        stats_text += f"  Std: {np.std(displacements):.3f} px\n"
        stats_text += f"  Range: [{np.min(displacements):.2f}, {np.max(displacements):.2f}]\n\n"
        stats_text += f"Intensity:\n"
        stats_text += f"  Mean: {np.mean(intensities):.1f}\n"
        stats_text += f"  Std: {np.std(intensities):.1f}\n"
        stats_text += f"  Range: [{np.min(intensities):.0f}, {np.max(intensities):.0f}]"

        axes[1, 1].text(0.1, 0.5, stats_text, fontsize=10,
                       verticalalignment='center', family='monospace')

        plt.tight_layout()
        plt.savefig(os.path.join(fig_dir, f'frame_{i:03d}_combined.png'),
                   dpi=150, bbox_inches='tight')
        plt.close()

    # Summary figure: All data combined
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    all_valid = []
    for frame_data in combined_data:
        all_valid.extend([p for p in frame_data if p['valid']])

    if all_valid:
        all_displacements = [p['displacement'] for p in all_valid]
        all_intensities = [p['intensity'] for p in all_valid]

        # Main correlation plot
        scatter = axes[0, 0].scatter(all_displacements, all_intensities,
                                    c=all_displacements, cmap='RdBu_r',
                                    s=30, alpha=0.5, edgecolors='none',
                                    vmin=-2, vmax=2)
        axes[0, 0].axvline(x=0, color='k', linestyle='--', linewidth=1)
        axes[0, 0].set_xlabel('Displacement (pixels)')
        axes[0, 0].set_ylabel('Intensity')
        axes[0, 0].set_title(f'All Data: Intensity vs Displacement\nn={len(all_valid)} points')
        axes[0, 0].grid(True, alpha=0.3)
        plt.colorbar(scatter, ax=axes[0, 0], label='Displacement')

        # Add regression line
        z = np.polyfit(all_displacements, all_intensities, 1)
        p = np.poly1d(z)
        x_line = np.linspace(min(all_displacements), max(all_displacements), 100)
        axes[0, 0].plot(x_line, p(x_line), 'r--', linewidth=2, alpha=0.8, label='Linear fit')
        axes[0, 0].legend()

        # Displacement distribution
        axes[0, 1].hist(all_displacements, bins=30, edgecolor='black', alpha=0.7, color='coral')
        axes[0, 1].axvline(x=0, color='k', linestyle='--', linewidth=2)
        axes[0, 1].axvline(x=np.mean(all_displacements), color='r',
                          linestyle='--', linewidth=2, label='Mean')
        axes[0, 1].set_xlabel('Displacement (pixels)')
        axes[0, 1].set_ylabel('Count')
        axes[0, 1].set_title('Displacement Distribution')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3, axis='y')

        # Intensity distribution
        axes[1, 0].hist(all_intensities, bins=30, edgecolor='black', alpha=0.7, color='skyblue')
        axes[1, 0].axvline(x=np.mean(all_intensities), color='r',
                          linestyle='--', linewidth=2, label='Mean')
        axes[1, 0].set_xlabel('Intensity')
        axes[1, 0].set_ylabel('Count')
        axes[1, 0].set_title('Intensity Distribution')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3, axis='y')

        # Statistics
        axes[1, 1].axis('off')

        # Calculate correlation
        from scipy import stats
        r, p_value = stats.pearsonr(all_displacements, all_intensities)

        stats_text = f"Overall Statistics:\n\n"
        stats_text += f"Total Valid Points: {len(all_valid)}\n"
        stats_text += f"Frames: {len(combined_data)}\n"
        stats_text += f"Temporal Direction: {CONFIG['temporal_direction']}\n\n"
        stats_text += f"Displacement:\n"
        stats_text += f"  Mean: {np.mean(all_displacements):.3f} px\n"
        stats_text += f"  Std: {np.std(all_displacements):.3f} px\n"
        stats_text += f"  Range: [{np.min(all_displacements):.2f}, {np.max(all_displacements):.2f}]\n\n"
        stats_text += f"Intensity:\n"
        stats_text += f"  Mean: {np.mean(all_intensities):.1f}\n"
        stats_text += f"  Std: {np.std(all_intensities):.1f}\n"
        stats_text += f"  Range: [{np.min(all_intensities):.0f}, {np.max(all_intensities):.0f}]\n\n"
        stats_text += f"Correlation:\n"
        stats_text += f"  Pearson r: {r:.3f}\n"
        stats_text += f"  R²: {r**2:.3f}\n"
        stats_text += f"  p-value: {p_value:.3e}"

        axes[1, 1].text(0.1, 0.5, stats_text, fontsize=11,
                       verticalalignment='center', family='monospace')

    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, 'combined_summary.png'),
               dpi=150, bbox_inches='tight')
    plt.close()

    print(f"Saved {len(combined_data)+1} verification figures")

def main():
    # Parse command line arguments
    parse_arguments()
    
    # Load previous results
    displacement_data, intensity_data = load_previous_results()

    # Assign movements to intensities
    combined_data = assign_all_movements(displacement_data, intensity_data,
                                        CONFIG['temporal_direction'])

    # Save combined data
    save_combined_data(combined_data, CONFIG['OUTPUT_DIR'])

    # Create verification figures if requested
    if CONFIG['CREATE_VERIFICATION_FIGURES']:
        create_verification_figures(combined_data, CONFIG['OUTPUT_DIR'])
    else:
        print("Skipping verification figures (CREATE_VERIFICATION_FIGURES=False)")

    print("\nStep 8 complete!")
    print(f"Results saved to: {CONFIG['OUTPUT_DIR']}")

if __name__ == "__main__":
    main()
