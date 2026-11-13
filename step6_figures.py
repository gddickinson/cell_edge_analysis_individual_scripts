"""Step 6 verification figures: sampling rectangles on each frame, coverage summary (moved verbatim from step6_sampling_rectangles.py; config = that script's CONFIG)."""

import os
import numpy as np
import matplotlib.pyplot as plt


def create_verification_figures(config, images, masks, edges, all_rectangles, output_dir):
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
        axes[0, 0].axvline(x=config['min_cell_coverage'], color='k',
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
    stats_text += f"Rectangle Size: {config['width']}×{config['depth']} px\n"
    stats_text += f"Min Coverage: {config['min_cell_coverage']:.1%}\n"
    stats_text += f"Rotation Method: {config['rotation_method']}\n"

    if config['rotation_method'] == 'search':
        stats_text += f"Search Angles: {config['rotation_search_angles']}\n"

    stats_text += "\n"

    if all_coverages:
        stats_text += f"Mean Coverage: {np.mean(all_coverages):.1%}\n"
        stats_text += f"Std Coverage: {np.std(all_coverages):.1%}"

    axes[1, 0].text(0.1, 0.5, stats_text, fontsize=12, verticalalignment='center',
                   family='monospace')

    # Rotation visualization - depends on method
    if config['rotation_method'] == 'search':
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
