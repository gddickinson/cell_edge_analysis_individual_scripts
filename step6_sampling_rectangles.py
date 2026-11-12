#!/usr/bin/env python3
"""
Step 6: Sampling Rectangle Creation
Creates sampling rectangles at each edge point and validates cell coverage.

Rectangle Sampling Methods:
- 'none': No rotation attempted, use initial normal direction only
- 'flip': Try 180° flip if initial rectangle is rejected
- 'search': Search through multiple angles to find maximum coverage
- 'vertical': Simple vertical rectangles (no normal calculation or rotation)

Saves to step6_results/
"""

import os
import sys
import argparse
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import pickle
import json

# Configuration
CONFIG = {
    'INPUT_DIR_STEP1': "step1_results",
    'INPUT_DIR_STEP2': "step2_results",
    'INPUT_DIR_STEP5': "step5_results",
    'OUTPUT_DIR': "step6_results",
    'depth': 50,                # Depth of rectangle (pixels into cell)
    'width': 25,                 # Width of rectangle (pixels)
    'min_cell_coverage': 0.8,    # Minimum fraction inside cell
    'rotation_method': 'vertical', # Options: 'none', 'flip', 'search', 'vertical'
                                 # 'none': No rotation attempted
                                 # 'flip': Try 180° flip only (original try_rotation behavior)
                                 # 'search': Search through multiple angles to find maximum coverage
                                 # 'vertical': Simple vertical rectangles, no normal calculation or rotation
    'rotation_search_angles': 18 # Number of angles to try (0-360°) for 'search' method
,
    'CREATE_VERIFICATION_FIGURES': True  # Create verification figures
}

def load_previous_results():
    """Load data from previous steps."""
    print("Loading previous results...")

    images = np.load(os.path.join(CONFIG['INPUT_DIR_STEP1'], 'images.npy'))
    masks = np.load(os.path.join(CONFIG['INPUT_DIR_STEP1'], 'masks.npy'))

    with open(os.path.join(CONFIG['INPUT_DIR_STEP2'], 'edges.pkl'), 'rb') as f:
        edges = pickle.load(f)

    with open(os.path.join(CONFIG['INPUT_DIR_STEP5'], 'sampled_edges.pkl'), 'rb') as f:
        sampled_edges = pickle.load(f)

    return images, masks, edges, sampled_edges


def parse_arguments():
    """Parse command line arguments to override CONFIG."""
    parser = argparse.ArgumentParser(description='Step 6: Sampling Rectangle Creation')
    
    parser.add_argument('--input-dir-step1', type=str,
                        help='Input directory from step 1')
    parser.add_argument('--input-dir-step2', type=str,
                        help='Input directory from step 2')
    parser.add_argument('--input-dir-step5', type=str,
                        help='Input directory from step 5')
    parser.add_argument('--output-dir', type=str,
                        help='Output directory for results')
    parser.add_argument('--depth', type=int,
                        help='Depth of rectangle (pixels into cell)')
    parser.add_argument('--width', type=int,
                        help='Width of rectangle (pixels)')
    parser.add_argument('--min-cell-coverage', type=float,
                        help='Minimum fraction inside cell')
    parser.add_argument('--rotation-method', type=str,
                        choices=['none', 'flip', 'search', 'vertical'],
                        help='Rotation method')
    parser.add_argument('--rotation-search-angles', type=int,
                        help='Number of angles to try for search method')
    parser.add_argument('--create-verification-figures', type=lambda x: x.lower() == 'true',
                        help='Create verification figures (true/false)')
    
    args = parser.parse_args()
    
    # Override CONFIG with command line arguments
    if args.input_dir_step1 is not None:
        CONFIG['INPUT_DIR_STEP1'] = args.input_dir_step1
    if args.input_dir_step2 is not None:
        CONFIG['INPUT_DIR_STEP2'] = args.input_dir_step2
    if args.input_dir_step5 is not None:
        CONFIG['INPUT_DIR_STEP5'] = args.input_dir_step5
    if args.output_dir is not None:
        CONFIG['OUTPUT_DIR'] = args.output_dir
    if args.depth is not None:
        CONFIG['depth'] = args.depth
    if args.width is not None:
        CONFIG['width'] = args.width
    if args.min_cell_coverage is not None:
        CONFIG['min_cell_coverage'] = args.min_cell_coverage
    if args.rotation_method is not None:
        CONFIG['rotation_method'] = args.rotation_method
    if args.rotation_search_angles is not None:
        CONFIG['rotation_search_angles'] = args.rotation_search_angles
    if args.create_verification_figures is not None:
        CONFIG['CREATE_VERIFICATION_FIGURES'] = args.create_verification_figures
    
    return args

def calculate_edge_normal(contour, point_idx, inward=True):
    """Calculate normal vector at edge point."""
    n = len(contour)
    if n < 3:
        return np.array([0, -1]) if inward else np.array([0, 1])

    # Use neighboring points for tangent
    prev_idx = max(0, point_idx - 2)
    next_idx = min(n - 1, point_idx + 2)

    tangent = contour[next_idx] - contour[prev_idx]
    tangent = tangent / (np.linalg.norm(tangent) + 1e-10)

    # Normal is perpendicular to tangent
    normal = np.array([-tangent[1], tangent[0]])

    # Determine if normal points inward
    center = np.mean(contour, axis=0)
    to_center = center - contour[point_idx]

    if np.dot(normal, to_center) < 0:
        normal = -normal

    if not inward:
        normal = -normal

    return normal

def create_sampling_rectangle(edge_point, normal, width, depth, image_shape):
    """Create rectangle coordinates."""
    half_width = width / 2

    # Perpendicular vector to normal
    perpendicular = np.array([normal[1], -normal[0]])

    # Four corners of rectangle
    corners = np.array([
        edge_point - perpendicular * half_width,
        edge_point - perpendicular * half_width + normal * depth,
        edge_point + perpendicular * half_width + normal * depth,
        edge_point + perpendicular * half_width
    ])

    return corners

def rotate_vector(vector, angle_degrees):
    """Rotate a 2D vector by the specified angle in degrees."""
    angle_rad = np.radians(angle_degrees)
    cos_angle = np.cos(angle_rad)
    sin_angle = np.sin(angle_rad)

    rotation_matrix = np.array([
        [cos_angle, -sin_angle],
        [sin_angle, cos_angle]
    ])

    return rotation_matrix @ vector

def search_optimal_rotation(edge_point, initial_normal, width, depth, mask, image_shape, n_angles):
    """
    Search through multiple rotation angles to find the orientation with maximum cell coverage.

    Parameters:
    - edge_point: The point on the edge
    - initial_normal: Initial normal vector
    - width, depth: Rectangle dimensions
    - mask: Cell mask
    - image_shape: Shape of the image
    - n_angles: Number of angles to test (evenly spaced 0-360°)

    Returns:
    - best_corners: Rectangle corners with maximum coverage
    - best_coverage: Maximum coverage achieved
    - best_angle: Angle (degrees) that gave best coverage
    """
    best_coverage = 0.0
    best_corners = None
    best_angle = 0.0
    best_pixels = []

    # Test angles from 0 to 360 degrees
    angles = np.linspace(0, 360, n_angles, endpoint=False)

    for angle in angles:
        # Rotate the normal vector
        rotated_normal = rotate_vector(initial_normal, angle)

        # Create rectangle with rotated normal
        corners = create_sampling_rectangle(edge_point, rotated_normal, width, depth, image_shape)

        # Check coverage
        coverage, pixels = check_cell_coverage(corners, mask)

        if coverage > best_coverage:
            best_coverage = coverage
            best_corners = corners
            best_angle = angle
            best_pixels = pixels

    return best_corners, best_coverage, best_angle, best_pixels

def check_cell_coverage(rectangle_corners, mask):
    """Check what fraction of rectangle is inside cell.

    Coverage is calculated as: (pixels in cell) / (theoretical rectangle area)
    This ensures rectangles extending outside the image bounds are properly penalized.
    """
    # Calculate theoretical rectangle area using cross product
    # Area = |AB × AD| where ABCD are the corners
    v1 = rectangle_corners[1] - rectangle_corners[0]  # AB
    v2 = rectangle_corners[3] - rectangle_corners[0]  # AD
    theoretical_area = abs(v1[0] * v2[1] - v1[1] * v2[0])

    if theoretical_area == 0:
        return 0.0, []

    # Get rectangle bounding box (before clipping)
    y_min_rect = int(np.floor(np.min(rectangle_corners[:, 0])))
    y_max_rect = int(np.ceil(np.max(rectangle_corners[:, 0])))
    x_min_rect = int(np.floor(np.min(rectangle_corners[:, 1])))
    x_max_rect = int(np.ceil(np.max(rectangle_corners[:, 1])))

    # Clip to image bounds for sampling
    y_min = max(0, y_min_rect)
    y_max = min(mask.shape[0], y_max_rect)
    x_min = max(0, x_min_rect)
    x_max = min(mask.shape[1], x_max_rect)

    if y_max <= y_min or x_max <= x_min:
        # Rectangle is completely outside image bounds
        return 0.0, []

    # Check each pixel within the clipped bounds
    y_coords, x_coords = np.mgrid[y_min:y_max, x_min:x_max]
    points = np.column_stack([y_coords.ravel(), x_coords.ravel()])

    # Point-in-polygon test
    def point_in_rectangle(point, corners):
        # Use cross product method
        def sign(p1, p2, p3):
            return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])

        d1 = sign(point, corners[0], corners[1])
        d2 = sign(point, corners[1], corners[2])
        d3 = sign(point, corners[2], corners[3])
        d4 = sign(point, corners[3], corners[0])

        has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0) or (d4 < 0)
        has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0) or (d4 > 0)

        return not (has_neg and has_pos)

    inside_rect = np.array([point_in_rectangle(p, rectangle_corners) for p in points])
    rect_pixels = points[inside_rect]

    if len(rect_pixels) == 0:
        return 0.0, []

    # Check how many are in cell
    inside_cell = mask[rect_pixels[:, 0], rect_pixels[:, 1]] > 0
    pixels_in_cell = np.sum(inside_cell)

    # Calculate coverage relative to theoretical area, not just visible pixels
    # This properly penalizes rectangles that extend outside the image
    coverage = pixels_in_cell / theoretical_area

    return coverage, rect_pixels

def create_rectangles_for_frame(sampled_points, edge, mask):
    """Create and validate rectangles for all sampled points in a frame."""
    rectangles = []

    for i, point in enumerate(sampled_points):
        # Step 5 ('fixed_x') records [nan, x] where no edge point was found: keep the slot, rejected, no pixels
        if np.any(np.isnan(point)):
            rectangles.append({
                'point_index': i, 'edge_point': point, 'normal': np.array([np.nan, np.nan]),
                'corners': np.full((4, 2), np.nan), 'coverage': 0.0, 'pixels': np.empty((0, 2), dtype=int),
                'accepted': False, 'rotation_tried': False, 'rotation_angle': 0.0
            })
            continue

        # Handle 'vertical' method separately (simple vertical rectangles, no normal calculation)
        if CONFIG['rotation_method'] == 'vertical':
            # Use fixed vertical direction (downward in image coordinates)
            normal = np.array([1.0, 0.0])

            # Create vertical rectangle
            corners = create_sampling_rectangle(point, normal, CONFIG['width'],
                                               CONFIG['depth'], mask.shape)

            # Check coverage
            coverage, pixels = check_cell_coverage(corners, mask)

            # Accept or reject based on threshold only (no rotation attempts)
            accepted = coverage >= CONFIG['min_cell_coverage']
            rotation_tried = False
            rotation_angle = 0.0

        else:
            # All other methods: calculate edge normal
            # Find closest edge point to get normal
            distances = np.sum((edge - point)**2, axis=1)
            edge_idx = np.argmin(distances)

            # Calculate normal
            normal = calculate_edge_normal(edge, edge_idx, inward=True)

            # Create initial rectangle
            corners = create_sampling_rectangle(point, normal, CONFIG['width'],
                                               CONFIG['depth'], mask.shape)

            # Check coverage
            coverage, pixels = check_cell_coverage(corners, mask)

            accepted = coverage >= CONFIG['min_cell_coverage']
            rotation_tried = False
            rotation_angle = 0.0

        # Apply rotation strategy if not accepted (skip for 'vertical' method)
        if not accepted and CONFIG['rotation_method'] not in ['none', 'vertical']:
            if CONFIG['rotation_method'] == 'flip':
                # Try simple 180° flip
                corners_rotated = create_sampling_rectangle(point, -normal, CONFIG['width'],
                                                           CONFIG['depth'], mask.shape)
                coverage_rotated, pixels_rotated = check_cell_coverage(corners_rotated, mask)

                if coverage_rotated >= CONFIG['min_cell_coverage']:
                    corners = corners_rotated
                    coverage = coverage_rotated
                    pixels = pixels_rotated
                    accepted = True
                    rotation_tried = True
                    rotation_angle = 180.0

            elif CONFIG['rotation_method'] == 'search':
                # Search through multiple angles for maximum coverage
                best_corners, best_coverage, best_angle, best_pixels = search_optimal_rotation(
                    point, normal, CONFIG['width'], CONFIG['depth'],
                    mask, mask.shape, CONFIG['rotation_search_angles']
                )

                # Accept if best coverage meets threshold
                if best_coverage >= CONFIG['min_cell_coverage']:
                    corners = best_corners
                    coverage = best_coverage
                    pixels = best_pixels
                    accepted = True
                    rotation_tried = True
                    rotation_angle = best_angle

        rectangles.append({
            'point_index': i,
            'edge_point': point,
            'normal': normal,
            'corners': corners,
            'coverage': coverage,
            'pixels': pixels,
            'accepted': accepted,
            'rotation_tried': rotation_tried,
            'rotation_angle': rotation_angle
        })

    return rectangles

def create_all_rectangles(sampled_edges, edges, masks):
    """Create rectangles for all frames."""
    print(f"Creating sampling rectangles for {len(sampled_edges)} frames...")

    all_rectangles = []

    for i in range(len(sampled_edges)):
        if len(sampled_edges[i]) > 0 and len(edges[i]) > 0:
            rectangles = create_rectangles_for_frame(sampled_edges[i], edges[i], masks[i])
        else:
            rectangles = []

        all_rectangles.append(rectangles)

        if (i + 1) % 10 == 0:
            print(f"  Processed {i+1}/{len(sampled_edges)} frames")

    return all_rectangles

def save_rectangles(all_rectangles, output_dir):
    """Save rectangle data."""
    os.makedirs(output_dir, exist_ok=True)

    # Save full data as pickle
    with open(os.path.join(output_dir, 'sampling_rectangles.pkl'), 'wb') as f:
        pickle.dump(all_rectangles, f)

    # Calculate statistics
    total_rectangles = sum(len(rects) for rects in all_rectangles)
    accepted_rectangles = sum(sum(r['accepted'] for r in rects) for rects in all_rectangles)
    rotated_rectangles = sum(sum(r['rotation_tried'] for r in rects) for rects in all_rectangles)

    # Calculate rotation angle statistics for search method
    rotation_angles = []
    for rects in all_rectangles:
        for r in rects:
            if r['rotation_tried']:
                rotation_angles.append(r['rotation_angle'])

    stats = {
        'n_frames': int(len(all_rectangles)),
        'total_rectangles': int(total_rectangles),
        'accepted_rectangles': int(accepted_rectangles),
        'rejected_rectangles': int(total_rectangles - accepted_rectangles),
        'acceptance_rate': float(accepted_rectangles / total_rectangles) if total_rectangles > 0 else 0.0,
        'rotation_tried_count': int(rotated_rectangles),
        'rotation_method': CONFIG['rotation_method'],
        'rectangle_width': float(CONFIG['width']),
        'rectangle_depth': float(CONFIG['depth']),
        'min_cell_coverage': float(CONFIG['min_cell_coverage'])
    }

    # Add rotation angle statistics if using search method
    if CONFIG['rotation_method'] == 'search' and rotation_angles:
        stats['rotation_search_angles'] = int(CONFIG['rotation_search_angles'])
        stats['rotation_angles_used'] = {
            'mean': float(np.mean(rotation_angles)),
            'std': float(np.std(rotation_angles)),
            'min': float(np.min(rotation_angles)),
            'max': float(np.max(rotation_angles))
        }

    with open(os.path.join(output_dir, 'rectangle_statistics.json'), 'w') as f:
        json.dump(stats, f, indent=2)

    print(f"Saved rectangle data to {output_dir}")
    print(f"  Rotation method: {CONFIG['rotation_method']}")
    print(f"  Total rectangles: {total_rectangles}")
    print(f"  Accepted: {accepted_rectangles} ({accepted_rectangles/total_rectangles*100:.1f}%)")
    print(f"  Rejected: {total_rectangles - accepted_rectangles}")
    if rotated_rectangles > 0:
        print(f"  Rotations tried: {rotated_rectangles} ({rotated_rectangles/total_rectangles*100:.1f}%)")

def create_verification_figures(images, masks, edges, all_rectangles, output_dir):
    """Create verification figures showing sampling rectangles."""
    print("Creating verification figures...")

    fig_dir = os.path.join(output_dir, 'verification_figures')
    os.makedirs(fig_dir, exist_ok=True)

    for i, rectangles in enumerate(all_rectangles):
        if len(rectangles) == 0:
            continue

        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        # Rectangles on mask
        axes[0].imshow(masks[i], cmap='gray')
        if len(edges[i]) > 0:
            axes[0].plot(edges[i][:, 1], edges[i][:, 0], 'r-', linewidth=1, alpha=0.3)

        for rect in rectangles:
            color = 'green' if rect['accepted'] else 'red'
            alpha = 0.3 if rect['accepted'] else 0.2
            corners = rect['corners']

            # Draw rectangle
            poly = plt.Polygon(corners[:, [1, 0]], fill=True,
                             facecolor=color, edgecolor=color,
                             alpha=alpha, linewidth=2)
            axes[0].add_patch(poly)

            # Mark center
            center = np.mean(corners, axis=0)
            axes[0].plot(center[1], center[0], 'o', color=color, markersize=5)
            axes[0].text(center[1], center[0], str(rect['point_index']),
                        color='white', fontsize=8, ha='center', va='center',
                        bbox=dict(boxstyle='circle', facecolor='black', alpha=0.5))

        accepted_count = sum(r['accepted'] for r in rectangles)
        axes[0].set_title(f'Frame {i}: Sampling Rectangles on Mask\n' +
                         f'Accepted: {accepted_count}/{len(rectangles)}')
        axes[0].axis('off')

        # Calculate percentile-based contrast limits for enhanced visualization
        vmin = np.percentile(images[i], 1)  # 1st percentile
        vmax = np.percentile(images[i], 99.5)  # 99.5th percentile

        # Rectangles on image with enhanced contrast
        axes[1].imshow(images[i], cmap='gray', vmin=vmin, vmax=vmax)
        if len(edges[i]) > 0:
            axes[1].plot(edges[i][:, 1], edges[i][:, 0], 'r-', linewidth=1, alpha=0.3)

        for rect in rectangles:
            color = 'lime' if rect['accepted'] else 'red'
            alpha = 0.3 if rect['accepted'] else 0.2
            corners = rect['corners']

            poly = plt.Polygon(corners[:, [1, 0]], fill=False,
                             edgecolor=color, linewidth=2, alpha=0.8)
            axes[1].add_patch(poly)

            # Mark center with coverage
            center = np.mean(corners, axis=0)
            axes[1].text(center[1], center[0], f"{rect['coverage']:.1%}",
                        color='white', fontsize=7, ha='center', va='center',
                        bbox=dict(boxstyle='round', facecolor='black', alpha=0.6))

        axes[1].set_title(f'Frame {i}: Sampling Rectangles on Image (enhanced contrast)')
        axes[1].axis('off')

        plt.tight_layout()
        plt.savefig(os.path.join(fig_dir, f'frame_{i:03d}_rectangles.png'),
                   dpi=150, bbox_inches='tight')
        plt.close()

    # Summary statistics figure
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Coverage distribution
    all_coverages = []
    accepted_coverages = []
    rejected_coverages = []

    for rectangles in all_rectangles:
        for rect in rectangles:
            all_coverages.append(rect['coverage'])
            if rect['accepted']:
                accepted_coverages.append(rect['coverage'])
            else:
                rejected_coverages.append(rect['coverage'])

    if all_coverages:
        axes[0, 0].hist([accepted_coverages, rejected_coverages],
                       bins=20, label=['Accepted', 'Rejected'],
                       color=['green', 'red'], alpha=0.7)
        axes[0, 0].axvline(x=CONFIG['min_cell_coverage'], color='k',
                          linestyle='--', linewidth=2, label='Threshold')
        axes[0, 0].set_xlabel('Cell Coverage')
        axes[0, 0].set_ylabel('Count')
        axes[0, 0].set_title('Rectangle Cell Coverage Distribution')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3, axis='y')

    # Acceptance rate per frame
    acceptance_rates = []
    for rectangles in all_rectangles:
        if len(rectangles) > 0:
            rate = sum(r['accepted'] for r in rectangles) / len(rectangles)
            acceptance_rates.append(rate)
        else:
            acceptance_rates.append(0)

    axes[0, 1].plot(acceptance_rates, marker='o', markersize=3)
    axes[0, 1].set_xlabel('Frame Number')
    axes[0, 1].set_ylabel('Acceptance Rate')
    axes[0, 1].set_title('Rectangle Acceptance Rate Over Time')
    axes[0, 1].grid(True, alpha=0.3)
    axes[0, 1].set_ylim(0, 1.05)

    # Overall statistics
    axes[1, 0].axis('off')
    total_rects = len(all_coverages)
    accepted = len(accepted_coverages)
    rejected = len(rejected_coverages)

    stats_text = f"Overall Statistics:\n\n"
    stats_text += f"Total Rectangles: {total_rects}\n"
    stats_text += f"Accepted: {accepted} ({accepted/total_rects*100:.1f}%)\n"
    stats_text += f"Rejected: {rejected} ({rejected/total_rects*100:.1f}%)\n\n"
    stats_text += f"Rectangle Size: {CONFIG['width']}×{CONFIG['depth']} px\n"
    stats_text += f"Min Coverage: {CONFIG['min_cell_coverage']:.1%}\n"
    stats_text += f"Rotation Method: {CONFIG['rotation_method']}\n"

    if CONFIG['rotation_method'] == 'search':
        stats_text += f"Search Angles: {CONFIG['rotation_search_angles']}\n"

    stats_text += "\n"

    if all_coverages:
        stats_text += f"Mean Coverage: {np.mean(all_coverages):.1%}\n"
        stats_text += f"Std Coverage: {np.std(all_coverages):.1%}"

    axes[1, 0].text(0.1, 0.5, stats_text, fontsize=12, verticalalignment='center',
                   family='monospace')

    # Rotation visualization - depends on method
    if CONFIG['rotation_method'] == 'search':
        # Show histogram of rotation angles used
        rotation_angles = []
        for rectangles in all_rectangles:
            for rect in rectangles:
                if rect['rotation_tried'] and rect['accepted']:
                    rotation_angles.append(rect['rotation_angle'])

        if rotation_angles:
            axes[1, 1].hist(rotation_angles, bins=36, edgecolor='black', alpha=0.7)
            axes[1, 1].set_xlabel('Rotation Angle (degrees)')
            axes[1, 1].set_ylabel('Count')
            axes[1, 1].set_title('Distribution of Accepted Rotation Angles')
            axes[1, 1].grid(True, alpha=0.3, axis='y')
        else:
            axes[1, 1].axis('off')
            axes[1, 1].text(0.5, 0.5, 'No rotations used', ha='center', va='center', fontsize=14)
    else:
        # Show rotated vs non-rotated pie chart for flip/none methods
        rotation_counts = {'Not Rotated': 0, 'Rotated & Accepted': 0}
        for rectangles in all_rectangles:
            for rect in rectangles:
                if rect['accepted']:
                    if rect['rotation_tried']:
                        rotation_counts['Rotated & Accepted'] += 1
                    else:
                        rotation_counts['Not Rotated'] += 1

        axes[1, 1].bar(rotation_counts.keys(), rotation_counts.values(),
                      color=['blue', 'orange'], alpha=0.7)
        axes[1, 1].set_ylabel('Count')
        axes[1, 1].set_title('Rectangle Rotation Statistics')
        axes[1, 1].grid(True, alpha=0.3, axis='y')

        for i, (k, v) in enumerate(rotation_counts.items()):
            axes[1, 1].text(i, v, str(v), ha='center', va='bottom')

    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, 'rectangle_summary.png'),
               dpi=150, bbox_inches='tight')
    plt.close()

    print(f"Saved {len(all_rectangles)+1} verification figures")

def main():
    # Parse command line arguments
    parse_arguments()
    
    # Load previous results
    images, masks, edges, sampled_edges = load_previous_results()

    # Create rectangles
    all_rectangles = create_all_rectangles(sampled_edges, edges, masks)

    # Save rectangles
    save_rectangles(all_rectangles, CONFIG['OUTPUT_DIR'])

    # Create verification figures if requested
    if CONFIG['CREATE_VERIFICATION_FIGURES']:
        create_verification_figures(images, masks, edges, all_rectangles, CONFIG['OUTPUT_DIR'])
    else:
        print("Skipping verification figures (CREATE_VERIFICATION_FIGURES=False)")

    print("\nStep 6 complete!")
    print(f"Results saved to: {CONFIG['OUTPUT_DIR']}")

if __name__ == "__main__":
    main()
