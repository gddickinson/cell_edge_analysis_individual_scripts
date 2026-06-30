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
    'IMAGE_STACK_PATH': "",  # Set via --image-stack-path or will search DATA_DIR
    'MASK_STACK_PATH': "",  # Set via --mask-stack-path or will search DATA_DIR
    'OUTPUT_DIR': "step1_results",
    'NORMALIZE_FRAMES': True,  # Normalize each frame to its brightest pixel
    'NORMALIZATION_SCALE': 100.0,  # Scaling factor after normalization (multiply by this value)
    'NORMALIZATION_METHOD': 'max',  # Reference value: 'max' or 'percentile' (robust to hot pixels)
    'NORMALIZATION_PERCENTILE': 99.9,  # Percentile used when NORMALIZATION_METHOD='percentile'
    'NORMALIZATION_REGION': 'frame',  # Compute reference over 'frame' (all pixels) or 'mask' (in-cell only)
    'NORMALIZATION_SCOPE': 'per_frame',  # 'per_frame' (each frame own ref) or 'global' (one ref for stack)
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
    parser.add_argument('--normalization-method', type=str, choices=['max', 'percentile'],
                        help="Reference value for normalization: 'max' (brightest pixel) "
                             "or 'percentile' (robust to hot pixels)")
    parser.add_argument('--normalization-percentile', type=float,
                        help='Percentile used when --normalization-method=percentile (default: 99.9)')
    parser.add_argument('--normalization-region', type=str, choices=['frame', 'mask'],
                        help="Compute the reference over the whole 'frame' or only 'mask' (in-cell) pixels")
    parser.add_argument('--normalization-scope', type=str, choices=['per_frame', 'global'],
                        help="Normalize each frame to its own reference ('per_frame') or "
                             "the whole stack to one reference ('global')")
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
    if args.normalization_method is not None:
        CONFIG['NORMALIZATION_METHOD'] = args.normalization_method
    if args.normalization_percentile is not None:
        CONFIG['NORMALIZATION_PERCENTILE'] = args.normalization_percentile
    if args.normalization_region is not None:
        CONFIG['NORMALIZATION_REGION'] = args.normalization_region
    if args.normalization_scope is not None:
        CONFIG['NORMALIZATION_SCOPE'] = args.normalization_scope
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

    if not CONFIG['IMAGE_STACK_PATH']:
        raise ValueError(
            "IMAGE_STACK_PATH not set. Use --image-stack-path to specify the image file."
        )
    if not CONFIG['MASK_STACK_PATH']:
        raise ValueError(
            "MASK_STACK_PATH not set. Use --mask-stack-path to specify the mask file."
        )

    if not os.path.exists(CONFIG['IMAGE_STACK_PATH']):
        raise FileNotFoundError(f"Image file not found: {CONFIG['IMAGE_STACK_PATH']}")
    if not os.path.exists(CONFIG['MASK_STACK_PATH']):
        raise FileNotFoundError(f"Mask file not found: {CONFIG['MASK_STACK_PATH']}")

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

    # Validate spatial dimension match
    if images.shape[1:] != masks.shape[1:]:
        raise ValueError(
            f"Image and mask spatial dimensions do not match: "
            f"images {images.shape[1:]} vs masks {masks.shape[1:]}. "
            f"Both must have the same height and width."
        )

    # Validate frame count match
    if images.shape[0] != masks.shape[0]:
        print(f"WARNING: Frame count mismatch: images={images.shape[0]}, masks={masks.shape[0]}")
        min_frames = min(images.shape[0], masks.shape[0])
        print(f"  Using first {min_frames} frames from each.")
        images = images[:min_frames]
        masks = masks[:min_frames]

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

def _compute_reference(values, method, percentile):
    """Compute the normalization reference (denominator) from pixel values.

    'max' uses the brightest pixel; 'percentile' uses the given percentile,
    which is robust to single hot pixels / saturated spots.
    """
    values = np.asarray(values)
    if values.size == 0:
        return 0.0
    if method == 'percentile':
        return float(np.percentile(values, percentile))
    return float(values.max())


def normalize_frames(images, masks=None):
    """Normalize frames to a reference value and apply scaling.

    The reference value (what gets mapped to NORMALIZATION_SCALE) is controlled
    by three orthogonal options:

    - method ('max' | 'percentile'): brightest pixel, or a robust percentile
      that ignores a handful of hot pixels.
    - region ('frame' | 'mask'): compute the reference over the whole image, or
      only over pixels inside the cell mask (ignores bright debris outside).
    - scope ('per_frame' | 'global'): normalize each frame to its own reference,
      or normalize the whole stack to a single reference (consistent frame-to-frame).

    Args:
        images: 3D numpy array (n_frames, height, width)
        masks: optional 3D binary mask array; required for region='mask'

    Returns:
        Normalized images as float32, typically in range [0, NORMALIZATION_SCALE]
    """
    method = CONFIG['NORMALIZATION_METHOD']
    percentile = CONFIG['NORMALIZATION_PERCENTILE']
    region = CONFIG['NORMALIZATION_REGION']
    scope = CONFIG['NORMALIZATION_SCOPE']
    scale = CONFIG['NORMALIZATION_SCALE']

    use_mask = (region == 'mask' and masks is not None)
    if region == 'mask' and masks is None:
        print("Warning: region='mask' requested but no masks provided; using whole frame")

    ref_desc = 'max' if method == 'max' else f'{percentile:g}th percentile'
    print(f"Normalizing frames ({scope}, {'in-mask' if use_mask else 'whole-frame'} {ref_desc})...")

    # Convert to float to preserve precision
    images_normalized = images.astype(np.float32)

    def frame_values(idx):
        if use_mask:
            selected = masks[idx] > 0
            if np.any(selected):
                return images_normalized[idx][selected]
            print(f"Warning: frame {idx} mask is empty; using whole frame")
        return images_normalized[idx].ravel()

    if scope in ('global', 'stack'):
        # One reference computed across the entire stack
        if use_mask and np.any(masks > 0):
            values = images_normalized[masks > 0]
        else:
            if use_mask:
                print("Warning: all masks empty; using whole stack")
            values = images_normalized
        reference = _compute_reference(values, method, percentile)
        if reference > 0:
            images_normalized = images_normalized / reference
            print(f"  Global reference value: {reference:.4f}")
        else:
            print("Warning: global reference is 0, skipping normalization")
    else:  # per_frame
        for i in range(images_normalized.shape[0]):
            reference = _compute_reference(frame_values(i), method, percentile)
            if reference > 0:  # Avoid division by zero
                images_normalized[i] = images_normalized[i] / reference
            else:
                print(f"Warning: Frame {i} reference is 0, skipping normalization")

    # Apply scaling factor
    if scale != 1.0:
        print(f"Applying normalization scale factor: {scale}")
        images_normalized = images_normalized * scale
        print(f"Normalized {images_normalized.shape[0]} frames to ~[0, {scale}]")
    else:
        print(f"Normalized {images_normalized.shape[0]} frames to ~[0, 1]")

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
        'normalization_method': CONFIG['NORMALIZATION_METHOD'],
        'normalization_percentile': CONFIG['NORMALIZATION_PERCENTILE'],
        'normalization_region': CONFIG['NORMALIZATION_REGION'],
        'normalization_scope': CONFIG['NORMALIZATION_SCOPE'],
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

    # Normalize frames if requested (masks enable region='mask' normalization)
    if CONFIG['NORMALIZE_FRAMES']:
        images = normalize_frames(images, masks)

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
