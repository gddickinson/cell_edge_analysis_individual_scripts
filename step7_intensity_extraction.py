#!/usr/bin/env python3
"""
Step 7: PIEZO1 Intensity Extraction
Extracts mean PIEZO1 intensity from accepted sampling rectangles.
Saves to step7_results/
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
    'INPUT_DIR_STEP6': "step6_results",
    'OUTPUT_DIR': "step7_results",
    'show_edge': True  # Display cell edge in verification figures
,
    'CREATE_VERIFICATION_FIGURES': True  # Create verification figures
}

def load_previous_results():
    """Load data from previous steps."""
    print("Loading previous results...")

    images = np.load(os.path.join(CONFIG['INPUT_DIR_STEP1'], 'images.npy'))

    with open(os.path.join(CONFIG['INPUT_DIR_STEP6'], 'sampling_rectangles.pkl'), 'rb') as f:
        all_rectangles = pickle.load(f)

    # Load edges if we want to display them
    edges = None
    if CONFIG['show_edge']:
        try:
            with open(os.path.join(CONFIG['INPUT_DIR_STEP2'], 'edges.pkl'), 'rb') as f:
                edges = pickle.load(f)
            print("  Loaded cell edges for visualization")
        except FileNotFoundError:
            print("  Warning: Could not load edges from step2_results, will skip edge display")
            edges = None

    return images, all_rectangles, edges


def parse_arguments():
    """Parse command line arguments to override CONFIG."""
    parser = argparse.ArgumentParser(description='Step 7: PIEZO1 Intensity Extraction')
    
    parser.add_argument('--input-dir-step1', type=str,
                        help='Input directory from step 1')
    parser.add_argument('--input-dir-step2', type=str,
                        help='Input directory from step 2')
    parser.add_argument('--input-dir-step6', type=str,
                        help='Input directory from step 6')
    parser.add_argument('--output-dir', type=str,
                        help='Output directory for results')
    parser.add_argument('--show-edge', type=lambda x: x.lower() == 'true',
                        help='Show cell edge in figures (true/false)')
    parser.add_argument('--create-verification-figures', type=lambda x: x.lower() == 'true',
                        help='Create verification figures (true/false)')
    
    args = parser.parse_args()
    
    # Override CONFIG with command line arguments
    if args.input_dir_step1 is not None:
        CONFIG['INPUT_DIR_STEP1'] = args.input_dir_step1
    if args.input_dir_step2 is not None:
        CONFIG['INPUT_DIR_STEP2'] = args.input_dir_step2
    if args.input_dir_step6 is not None:
        CONFIG['INPUT_DIR_STEP6'] = args.input_dir_step6
    if args.output_dir is not None:
        CONFIG['OUTPUT_DIR'] = args.output_dir
    if args.show_edge is not None:
        CONFIG['show_edge'] = args.show_edge
    if args.create_verification_figures is not None:
        CONFIG['CREATE_VERIFICATION_FIGURES'] = args.create_verification_figures
    
    return args

def extract_intensity_from_rectangle(image, pixels):
    """Extract mean intensity from rectangle pixels."""
    if len(pixels) == 0:
        return np.nan

    # Get intensities
    intensities = image[pixels[:, 0], pixels[:, 1]]

    return np.mean(intensities)

def extract_all_intensities(images, all_rectangles):
    """Extract intensities for all frames."""
    print(f"Extracting intensities for {len(all_rectangles)} frames...")

    intensity_data = []

    for i in range(len(all_rectangles)):
        frame_intensities = []

        for rect in all_rectangles[i]:
            if rect['accepted']:
                intensity = extract_intensity_from_rectangle(images[i], rect['pixels'])
            else:
                intensity = np.nan

            frame_intensities.append({
                'point_index': rect['point_index'],
                'edge_point': rect['edge_point'],
                'intensity': intensity,
                'accepted': rect['accepted'],
                'n_pixels': len(rect['pixels'])
            })

        intensity_data.append(frame_intensities)

        if (i + 1) % 10 == 0:
            print(f"  Processed {i+1}/{len(all_rectangles)} frames")

    return intensity_data

def save_intensities(intensity_data, output_dir):
    """Save intensity data."""
    os.makedirs(output_dir, exist_ok=True)

    # Save full data as pickle
    with open(os.path.join(output_dir, 'intensity_data.pkl'), 'wb') as f:
        pickle.dump(intensity_data, f)

    # Calculate statistics
    all_intensities = []
    valid_intensities = []

    for frame_data in intensity_data:
        for point_data in frame_data:
            all_intensities.append(point_data['intensity'])
            if point_data['accepted'] and not np.isnan(point_data['intensity']):
                valid_intensities.append(point_data['intensity'])

    stats = {
        'n_frames': len(intensity_data),
        'total_measurements': len(all_intensities),
        'valid_measurements': len(valid_intensities),
        'invalid_measurements': len(all_intensities) - len(valid_intensities)
    }

    if valid_intensities:
        stats['mean_intensity'] = float(np.mean(valid_intensities))
        stats['std_intensity'] = float(np.std(valid_intensities))
        stats['min_intensity'] = float(np.min(valid_intensities))
        stats['max_intensity'] = float(np.max(valid_intensities))
        stats['median_intensity'] = float(np.median(valid_intensities))

    with open(os.path.join(output_dir, 'intensity_statistics.json'), 'w') as f:
        json.dump(stats, f, indent=2)

    print(f"Saved intensity data to {output_dir}")
    print(f"  Valid measurements: {len(valid_intensities)}/{len(all_intensities)}")
    if valid_intensities:
        print(f"  Mean intensity: {np.mean(valid_intensities):.1f}")

def create_verification_figures(images, all_rectangles, intensity_data, edges, output_dir):
    """Create verification figures showing intensity extraction."""
    print("Creating verification figures...")

    fig_dir = os.path.join(output_dir, 'verification_figures')
    os.makedirs(fig_dir, exist_ok=True)

    for i, frame_data in enumerate(intensity_data):
        if len(frame_data) == 0:
            continue

        fig, axes = plt.subplots(1, 3, figsize=(18, 5))

        # Calculate percentile-based contrast limits for enhanced visualization
        img_vmin = np.percentile(images[i], 1)  # 1st percentile
        img_vmax = np.percentile(images[i], 99.5)  # 99.5th percentile

        # Image with rectangles colored by intensity (enhanced contrast)
        axes[0].imshow(images[i], cmap='gray', vmin=img_vmin, vmax=img_vmax)

        # Plot cell edge if available
        if edges is not None and i < len(edges) and len(edges[i]) > 0:
            axes[0].plot(edges[i][:, 1], edges[i][:, 0], 'r-', linewidth=1.5, alpha=0.6, label='Cell Edge')

        # Collect valid intensities for this frame for colormap normalization
        valid_intensities = [p['intensity'] for p in frame_data
                           if p['accepted'] and not np.isnan(p['intensity'])]

        if valid_intensities:
            intensity_vmin, intensity_vmax = np.min(valid_intensities), np.max(valid_intensities)
        else:
            intensity_vmin, intensity_vmax = 0, 1

        for j, point_data in enumerate(frame_data):
            if point_data['accepted'] and not np.isnan(point_data['intensity']):
                # Draw rectangle region
                rect = all_rectangles[i][j]
                corners = rect['corners']

                # Color by intensity
                if intensity_vmax > intensity_vmin:
                    normalized = (point_data['intensity'] - intensity_vmin) / (intensity_vmax - intensity_vmin)
                else:
                    normalized = 0.5

                color = plt.cm.viridis(normalized)
                poly = plt.Polygon(corners[:, [1, 0]], fill=True,
                                 facecolor=color, edgecolor='white',
                                 alpha=0.5, linewidth=1)
                axes[0].add_patch(poly)

                # Label with intensity value
                center = np.mean(corners, axis=0)
                axes[0].text(center[1], center[0], f"{point_data['intensity']:.0f}",
                           color='white', fontsize=8, ha='center', va='center',
                           bbox=dict(boxstyle='round', facecolor='black', alpha=0.7))

        axes[0].set_title(f'Frame {i}: Intensity Values (enhanced contrast)')

        # Add legend if edge is displayed
        if edges is not None and i < len(edges) and len(edges[i]) > 0:
            axes[0].legend(loc='upper right', fontsize=8, framealpha=0.8)

        axes[0].axis('off')

        # Scatter plot of intensity vs position
        valid_points = [p for p in frame_data if p['accepted'] and not np.isnan(p['intensity'])]
        if valid_points:
            x_positions = [p['edge_point'][1] for p in valid_points]
            intensities = [p['intensity'] for p in valid_points]

            scatter = axes[1].scatter(x_positions, intensities,
                                     c=intensities, cmap='viridis',
                                     s=100, edgecolors='black', linewidth=1)
            axes[1].set_xlabel('X Position (pixels)')
            axes[1].set_ylabel('Mean Intensity')
            axes[1].set_title(f'Intensity vs X-Position\nn={len(valid_points)} points')
            axes[1].grid(True, alpha=0.3)
            plt.colorbar(scatter, ax=axes[1], label='Intensity')
        else:
            axes[1].text(0.5, 0.5, 'No valid measurements',
                        ha='center', va='center', transform=axes[1].transAxes)
            axes[1].set_title('Intensity vs X-Position')

        # Intensity distribution
        if valid_points:
            axes[2].hist(intensities, bins=15, edgecolor='black', alpha=0.7, color='skyblue')
            axes[2].axvline(x=np.mean(intensities), color='r',
                           linestyle='--', linewidth=2, label='Mean')
            axes[2].axvline(x=np.median(intensities), color='g',
                           linestyle='--', linewidth=2, label='Median')
            axes[2].set_xlabel('Intensity')
            axes[2].set_ylabel('Count')
            axes[2].set_title(f'Intensity Distribution\nMean: {np.mean(intensities):.1f}')
            axes[2].legend()
            axes[2].grid(True, alpha=0.3, axis='y')
        else:
            axes[2].text(0.5, 0.5, 'No valid measurements',
                        ha='center', va='center', transform=axes[2].transAxes)
            axes[2].set_title('Intensity Distribution')

        plt.tight_layout()
        plt.savefig(os.path.join(fig_dir, f'frame_{i:03d}_intensities.png'),
                   dpi=150, bbox_inches='tight')
        plt.close()

    # Summary figure
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Intensity over time (frame-averaged)
    frame_means = []
    frame_numbers = []
    for i, frame_data in enumerate(intensity_data):
        valid = [p['intensity'] for p in frame_data
                if p['accepted'] and not np.isnan(p['intensity'])]
        if valid:
            frame_means.append(np.mean(valid))
            frame_numbers.append(i)

    if frame_means:
        axes[0, 0].plot(frame_numbers, frame_means, marker='o', markersize=4)
        axes[0, 0].set_xlabel('Frame Number')
        axes[0, 0].set_ylabel('Mean Intensity')
        axes[0, 0].set_title('Mean Intensity Over Time')
        axes[0, 0].grid(True, alpha=0.3)

    # Overall intensity distribution
    all_valid = []
    for frame_data in intensity_data:
        all_valid.extend([p['intensity'] for p in frame_data
                         if p['accepted'] and not np.isnan(p['intensity'])])

    if all_valid:
        axes[0, 1].hist(all_valid, bins=30, edgecolor='black', alpha=0.7, color='skyblue')
        axes[0, 1].axvline(x=np.mean(all_valid), color='r',
                          linestyle='--', linewidth=2, label='Mean')
        axes[0, 1].set_xlabel('Intensity')
        axes[0, 1].set_ylabel('Count')
        axes[0, 1].set_title('Overall Intensity Distribution')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3, axis='y')

    # Number of valid measurements per frame
    valid_counts = []
    for frame_data in intensity_data:
        count = sum(1 for p in frame_data if p['accepted'] and not np.isnan(p['intensity']))
        valid_counts.append(count)

    axes[1, 0].bar(range(len(valid_counts)), valid_counts, alpha=0.7, color='green')
    axes[1, 0].set_xlabel('Frame Number')
    axes[1, 0].set_ylabel('Valid Measurements')
    axes[1, 0].set_title('Valid Measurements Per Frame')
    axes[1, 0].grid(True, alpha=0.3, axis='y')

    # Statistics summary
    axes[1, 1].axis('off')
    if all_valid:
        stats_text = f"Intensity Statistics:\n\n"
        stats_text += f"Total Measurements: {len(all_valid)}\n"
        stats_text += f"Mean: {np.mean(all_valid):.1f}\n"
        stats_text += f"Std: {np.std(all_valid):.1f}\n"
        stats_text += f"Median: {np.median(all_valid):.1f}\n"
        stats_text += f"Min: {np.min(all_valid):.1f}\n"
        stats_text += f"Max: {np.max(all_valid):.1f}\n"
        stats_text += f"Range: {np.max(all_valid) - np.min(all_valid):.1f}\n\n"
        stats_text += f"Frames: {len(intensity_data)}\n"
        stats_text += f"Avg measurements/frame: {len(all_valid)/len(intensity_data):.1f}"

        axes[1, 1].text(0.1, 0.5, stats_text, fontsize=12,
                       verticalalignment='center', family='monospace')

    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, 'intensity_summary.png'),
               dpi=150, bbox_inches='tight')
    plt.close()

    print(f"Saved {len(intensity_data)+1} verification figures")

def main():
    # Parse command line arguments
    parse_arguments()
    
    # Load previous results
    images, all_rectangles, edges = load_previous_results()

    # Extract intensities
    intensity_data = extract_all_intensities(images, all_rectangles)

    # Save intensities
    save_intensities(intensity_data, CONFIG['OUTPUT_DIR'])

    # Create verification figures if requested
    if CONFIG['CREATE_VERIFICATION_FIGURES']:
        create_verification_figures(images, all_rectangles, intensity_data, edges, CONFIG['OUTPUT_DIR'])
    else:
        print("Skipping verification figures (CREATE_VERIFICATION_FIGURES=False)")

    print("\nStep 7 complete!")
    print(f"Results saved to: {CONFIG['OUTPUT_DIR']}")

if __name__ == "__main__":
    main()
