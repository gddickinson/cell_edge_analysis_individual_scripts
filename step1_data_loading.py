#!/usr/bin/env python3
"""
Step 1: Data Loading and Initialization
Loads image and mask stacks, performs basic validation, saves to step1_results/
"""

import os
import sys
import argparse
import numpy as np
import matplotlib.pyplot as plt
import tifffile
import json

# Configuration
CONFIG = {
    'IMAGE_STACK_PATH': "/Users/george/Desktop/forJinghao_scripts/data/test_1/151_2019_07_29_TIRF_mKera_scratch_1_Pos7_rot30_crop_piezo1.tif",
    'MASK_STACK_PATH': "/Users/george/Desktop/forJinghao_scripts/data/test_1/151_2019_07_29_TIRF_mKera_scratch_1_Pos7_rot30_crop_Mask.tif",
    'OUTPUT_DIR': "step1_results",
    'NORMALIZE_FRAMES': True,  # Normalize each frame to its brightest pixel
    'NORMALIZATION_SCALE': 100.0,  # Scaling factor after normalization (multiply by this value)
    'SUBTRACT_BACKGROUND': True,  # Subtract background before normalization
    'BACKGROUND_PERCENTILE': 10,  # Percentile of histogram to use as background (0-100)
    'CREATE_VERIFICATION_FIGURES': True  # Create verification figures
}

def parse_arguments():
    """Parse command line arguments to override CONFIG."""
    parser = argparse.ArgumentParser(description='Step 1: Data Loading and Initialization')

    parser.add_argument('--image-stack-path', type=str,
                        help='Path to image stack TIFF file')
    parser.add_argument('--mask-stack-path', type=str,
                        help='Path to mask stack TIFF file')
    parser.add_argument('--output-dir', type=str,
                        help='Output directory for results')
    parser.add_argument('--normalize-frames', type=lambda x: x.lower() == 'true',
                        help='Normalize frames (true/false)')
    parser.add_argument('--normalization-scale', type=float,
                        help='Scaling factor after normalization (default: 1.0)')
    parser.add_argument('--subtract-background', type=lambda x: x.lower() == 'true',
                        help='Subtract background before normalization (true/false)')
    parser.add_argument('--background-percentile', type=float,
                        help='Percentile of histogram to use as background (0-100, default: 10)')
    parser.add_argument('--create-verification-figures', type=lambda x: x.lower() == 'true',
                        help='Create verification figures (true/false)')

    args = parser.parse_args()

    # Override CONFIG with command line arguments
    if args.image_stack_path is not None:
        CONFIG['IMAGE_STACK_PATH'] = args.image_stack_path
    if args.mask_stack_path is not None:
        CONFIG['MASK_STACK_PATH'] = args.mask_stack_path
    if args.output_dir is not None:
        CONFIG['OUTPUT_DIR'] = args.output_dir
    if args.normalize_frames is not None:
        CONFIG['NORMALIZE_FRAMES'] = args.normalize_frames
    if args.normalization_scale is not None:
        CONFIG['NORMALIZATION_SCALE'] = args.normalization_scale
    if args.subtract_background is not None:
        CONFIG['SUBTRACT_BACKGROUND'] = args.subtract_background
    if args.background_percentile is not None:
        CONFIG['BACKGROUND_PERCENTILE'] = args.background_percentile
    if args.create_verification_figures is not None:
        CONFIG['CREATE_VERIFICATION_FIGURES'] = args.create_verification_figures

    return args

def load_and_validate_data():
    """Load and validate image and mask stacks."""
    print("Step 1: Loading data...")

    # Load images
    images = tifffile.imread(CONFIG['IMAGE_STACK_PATH'])
    masks = tifffile.imread(CONFIG['MASK_STACK_PATH'])

    # Ensure masks are binary
    masks = (masks > 0).astype(np.uint8)

    # Handle single image case
    if images.ndim == 2:
        images = images[np.newaxis, ...]
    if masks.ndim == 2:
        masks = masks[np.newaxis, ...]

    print(f"Loaded {images.shape[0]} frames of size {images.shape[1]}x{images.shape[2]}")

    return images, masks

def subtract_background(images):
    """Subtract background from each frame based on histogram percentile.

    Args:
        images: 3D numpy array (n_frames, height, width)

    Returns:
        Background-subtracted images
    """
    print(f"Subtracting background using {CONFIG['BACKGROUND_PERCENTILE']}th percentile...")

    # Convert to float to allow negative values during subtraction
    images_bg_subtracted = images.astype(np.float32)

    background_values = []

    # Subtract background from each frame
    for i in range(images_bg_subtracted.shape[0]):
        # Calculate background as the specified percentile
        background = np.percentile(images_bg_subtracted[i], CONFIG['BACKGROUND_PERCENTILE'])
        background_values.append(background)

        # Subtract background
        images_bg_subtracted[i] = images_bg_subtracted[i] - background

        # Clip negative values to zero
        images_bg_subtracted[i] = np.maximum(images_bg_subtracted[i], 0)

    # Report statistics
    print(f"  Background range: [{min(background_values):.2f}, {max(background_values):.2f}]")
    print(f"  Mean background: {np.mean(background_values):.2f}")
    print(f"Background subtraction complete for {images_bg_subtracted.shape[0]} frames")

    return images_bg_subtracted

def normalize_frames(images):
    """Normalize each frame to its brightest pixel value and apply scaling.

    Args:
        images: 3D numpy array (n_frames, height, width)

    Returns:
        Normalized images as float32 in range [0, NORMALIZATION_SCALE]
    """
    print("Normalizing frames to brightest pixel...")

    # Convert to float to preserve precision
    images_normalized = images.astype(np.float32)

    # Normalize each frame independently
    for i in range(images_normalized.shape[0]):
        frame_max = images_normalized[i].max()
        if frame_max > 0:  # Avoid division by zero
            images_normalized[i] = images_normalized[i] / frame_max
        else:
            print(f"Warning: Frame {i} has max value of 0, skipping normalization")

    # Apply scaling factor
    if CONFIG['NORMALIZATION_SCALE'] != 1.0:
        print(f"Applying normalization scale factor: {CONFIG['NORMALIZATION_SCALE']}")
        images_normalized = images_normalized * CONFIG['NORMALIZATION_SCALE']
        print(f"Normalized {images_normalized.shape[0]} frames to range [0, {CONFIG['NORMALIZATION_SCALE']}]")
    else:
        print(f"Normalized {images_normalized.shape[0]} frames to range [0, 1]")

    return images_normalized

def save_data_and_metadata(images, masks, output_dir):
    """Save loaded data and metadata."""
    os.makedirs(output_dir, exist_ok=True)

    # Save as NPY files for fast loading in next steps
    np.save(os.path.join(output_dir, 'images.npy'), images)
    np.save(os.path.join(output_dir, 'masks.npy'), masks)

    # Save metadata
    metadata = {
        'n_frames': int(images.shape[0]),
        'height': int(images.shape[1]),
        'width': int(images.shape[2]),
        'image_dtype': str(images.dtype),
        'mask_dtype': str(masks.dtype),
        'normalized': CONFIG['NORMALIZE_FRAMES'],
        'normalization_scale': CONFIG['NORMALIZATION_SCALE'],
        'background_subtracted': CONFIG['SUBTRACT_BACKGROUND'],
        'background_percentile': CONFIG['BACKGROUND_PERCENTILE'] if CONFIG['SUBTRACT_BACKGROUND'] else None
    }

    with open(os.path.join(output_dir, 'metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"Saved data to {output_dir}")

def create_verification_figures(images, masks, output_dir):
    """Create verification figures for each frame with enhanced contrast."""
    print("Creating verification figures...")

    fig_dir = os.path.join(output_dir, 'verification_figures')
    os.makedirs(fig_dir, exist_ok=True)

    for i in range(images.shape[0]):
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))

        # Calculate percentile-based contrast limits for better visualization
        vmin = np.percentile(images[i], 1)  # 1st percentile
        vmax = np.percentile(images[i], 99.5)  # 99.5th percentile

        # Raw image with enhanced contrast
        axes[0].imshow(images[i], cmap='gray', vmin=vmin, vmax=vmax)
        axes[0].set_title(f'Frame {i}: PIEZO1 Image (enhanced contrast)')
        axes[0].axis('off')

        # Mask
        axes[1].imshow(masks[i], cmap='gray')
        axes[1].set_title(f'Frame {i}: Cell Mask')
        axes[1].axis('off')

        # Overlay with enhanced contrast
        axes[2].imshow(images[i], cmap='gray', vmin=vmin, vmax=vmax)
        axes[2].contour(masks[i], colors='red', linewidths=1)
        axes[2].set_title(f'Frame {i}: Overlay (enhanced contrast)')
        axes[2].axis('off')

        plt.tight_layout()
        plt.savefig(os.path.join(fig_dir, f'frame_{i:03d}_data_verification.png'),
                   dpi=150, bbox_inches='tight')
        plt.close()

    print(f"Saved {images.shape[0]} verification figures")

def main():
    # Parse command line arguments
    parse_arguments()

    # Load data
    images, masks = load_and_validate_data()

    # Subtract background if requested (before normalization)
    if CONFIG['SUBTRACT_BACKGROUND']:
        images = subtract_background(images)

    # Normalize frames if requested
    if CONFIG['NORMALIZE_FRAMES']:
        images = normalize_frames(images)

    # Save data
    save_data_and_metadata(images, masks, CONFIG['OUTPUT_DIR'])

    # Create verification figures if requested
    if CONFIG['CREATE_VERIFICATION_FIGURES']:
        create_verification_figures(images, masks, CONFIG['OUTPUT_DIR'])
    else:
        print("Skipping verification figures (CREATE_VERIFICATION_FIGURES=False)")

    print("\nStep 1 complete!")
    print(f"Results saved to: {CONFIG['OUTPUT_DIR']}")

if __name__ == "__main__":
    main()
