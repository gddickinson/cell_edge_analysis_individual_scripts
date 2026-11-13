"""The Tk GUI results views: overview, edges, displacement, classification, sampling, intensity, correlation.

Mixin of cell_edge_analysis_gui.AnalysisGUI (methods moved verbatim from that file)."""
import numpy as np
import matplotlib.pyplot as plt


class ViewsMixin:
    def show_overview(self):
        """Show overview of current frame."""
        self.fig.clear()

        if self.images is None:
            return

        frame = self.current_frame

        # Create subplots
        if self.edges is not None:
            axes = self.fig.subplots(1, 3)
        else:
            axes = self.fig.subplots(1, 2)

        # Calculate contrast limits
        vmin = np.percentile(self.images[frame], 1)
        vmax = np.percentile(self.images[frame], 99.5)

        # Raw image
        axes[0].imshow(self.images[frame], cmap='gray', vmin=vmin, vmax=vmax)
        axes[0].set_title(f'Frame {frame}: PIEZO1 Image')
        axes[0].axis('off')

        # Mask
        axes[1].imshow(self.masks[frame], cmap='gray')
        axes[1].set_title(f'Frame {frame}: Cell Mask')
        axes[1].axis('off')

        # Edge overlay
        if self.edges is not None and len(axes) > 2:
            axes[2].imshow(self.images[frame], cmap='gray', vmin=vmin, vmax=vmax)
            if len(self.edges[frame]) > 0:
                axes[2].plot(self.edges[frame][:, 1], self.edges[frame][:, 0], 'r-', linewidth=2)
            axes[2].set_title(f'Frame {frame}: Edge Detection')
            axes[2].axis('off')

        self.fig.tight_layout()

    def show_edge_detection(self):
        """Show edge detection results."""
        self.fig.clear()

        if self.edges is None:
            return

        frame = self.current_frame
        axes = self.fig.subplots(1, 2)

        vmin = np.percentile(self.images[frame], 1)
        vmax = np.percentile(self.images[frame], 99.5)

        # Edge on mask
        axes[0].imshow(self.masks[frame], cmap='gray')
        if len(self.edges[frame]) > 0:
            axes[0].plot(self.edges[frame][:, 1], self.edges[frame][:, 0], 'r-', linewidth=2)
        axes[0].set_title(f'Frame {frame}: Edge on Mask ({len(self.edges[frame])} points)')
        axes[0].axis('off')

        # Edge on image
        axes[1].imshow(self.images[frame], cmap='gray', vmin=vmin, vmax=vmax)
        if len(self.edges[frame]) > 0:
            axes[1].plot(self.edges[frame][:, 1], self.edges[frame][:, 0], 'r-', linewidth=2)
        axes[1].set_title(f'Frame {frame}: Edge on Image')
        axes[1].axis('off')

        self.fig.tight_layout()

    def show_displacement(self):
        """Show displacement analysis."""
        self.fig.clear()

        if self.displacement_data is None or self.current_frame >= len(self.displacement_data):
            return

        frame = self.current_frame
        data = self.displacement_data[frame]

        axes = self.fig.subplots(2, 2)

        # Frame pair overlay
        vmin = np.percentile(self.images[frame], 1)
        vmax = np.percentile(self.images[frame], 99.5)

        axes[0, 0].imshow(self.images[frame], cmap='gray', alpha=0.5, vmin=vmin, vmax=vmax)
        if len(self.edges[frame]) > 0:
            axes[0, 0].plot(self.edges[frame][:, 1], self.edges[frame][:, 0], 'b-', linewidth=2, label=f'Frame {frame}')
        if frame + 1 < len(self.edges) and len(self.edges[frame+1]) > 0:
            axes[0, 0].plot(self.edges[frame+1][:, 1], self.edges[frame+1][:, 0], 'r-', linewidth=2, label=f'Frame {frame+1}')
        axes[0, 0].set_title(f'Frame Pair {frame}→{frame+1}')
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
            axes[0, 1].set_title(f'Avg: {data["avg_displacement"]:.2f}px')
            self.fig.colorbar(scatter, ax=axes[0, 1], label='Displacement (px)')
            axes[0, 1].grid(True, alpha=0.3)

        # Histogram
        if np.any(valid_mask):
            axes[1, 0].hist(disp[valid_mask], bins=30, edgecolor='black', alpha=0.7)
            axes[1, 0].axvline(x=data['avg_displacement'], color='r', linestyle='--', linewidth=2)
            axes[1, 0].set_xlabel('Displacement (pixels)')
            axes[1, 0].set_ylabel('Count')
            axes[1, 0].set_title('Distribution')
            axes[1, 0].grid(True, alpha=0.3)

        # Statistics
        axes[1, 1].axis('off')
        stats_text = f"Displacement Statistics\n\n"
        stats_text += f"Mean: {data['avg_displacement']:.3f} px\n"
        stats_text += f"Std: {data['std_displacement']:.3f} px\n"
        stats_text += f"Valid points: {data['n_valid']}\n"
        axes[1, 1].text(0.1, 0.5, stats_text, fontsize=12, verticalalignment='center', family='monospace')

        self.fig.tight_layout()

    def show_classification(self):
        """Show movement classification."""
        self.fig.clear()

        if self.classifications is None or self.current_frame >= len(self.classifications):
            return

        frame = self.current_frame
        cls = self.classifications[frame]

        axes = self.fig.subplots(1, 2)

        # Image with classification
        vmin = np.percentile(self.images[frame+1], 1)
        vmax = np.percentile(self.images[frame+1], 99.5)

        axes[0].imshow(self.images[frame+1], cmap='gray', vmin=vmin, vmax=vmax)
        if len(self.edges[frame]) > 0:
            axes[0].plot(self.edges[frame][:, 1], self.edges[frame][:, 0], 'b-', linewidth=2, alpha=0.7)
        if len(self.edges[frame+1]) > 0:
            axes[0].plot(self.edges[frame+1][:, 1], self.edges[frame+1][:, 0], 'r-', linewidth=2, alpha=0.7)
        axes[0].set_title(f'Frame {frame}→{frame+1}')
        axes[0].axis('off')

        # Classification info
        color_map = {'extruding': 'blue', 'retracting': 'red', 'stable': 'gray'}
        color = color_map[cls['movement_type']]

        axes[1].axis('off')
        axes[1].set_xlim(0, 1)
        axes[1].set_ylim(0, 1)

        info_text = f"Movement Type:\n{cls['movement_type'].upper()}\n\n"
        info_text += f"Avg Displacement:\n{cls['avg_displacement']:.3f} px\n\n"
        info_text += f"Std Displacement:\n{cls['std_displacement']:.3f} px\n\n"
        info_text += f"Valid Points: {cls['n_valid']}"

        axes[1].text(0.5, 0.5, info_text, ha='center', va='center', fontsize=14,
                    bbox=dict(boxstyle='round', facecolor=color, alpha=0.3))

        self.fig.tight_layout()

    def show_sampling(self):
        """Show sampling rectangles."""
        self.fig.clear()

        if self.sampling_rectangles is None or self.current_frame >= len(self.sampling_rectangles):
            return

        frame = self.current_frame
        rectangles = self.sampling_rectangles[frame]

        ax = self.fig.add_subplot(111)

        vmin = np.percentile(self.images[frame], 1)
        vmax = np.percentile(self.images[frame], 99.5)

        ax.imshow(self.images[frame], cmap='gray', vmin=vmin, vmax=vmax)

        if len(self.edges[frame]) > 0:
            ax.plot(self.edges[frame][:, 1], self.edges[frame][:, 0], 'r-', linewidth=1.5, alpha=0.6)

        # Draw rectangles
        for rect in rectangles:
            if rect['accepted']:
                corners = rect['corners']
                poly = plt.Polygon(corners[:, [1, 0]], fill=False, edgecolor='lime', linewidth=2)
                ax.add_patch(poly)

        ax.set_title(f'Frame {frame}: Sampling Rectangles ({sum(1 for r in rectangles if r["accepted"])} accepted)')
        ax.axis('off')

        self.fig.tight_layout()

    def show_intensity(self):
        """Show intensity extraction results."""
        self.fig.clear()

        if self.intensity_data is None or self.current_frame >= len(self.intensity_data):
            return

        frame = self.current_frame
        frame_data = self.intensity_data[frame]

        if len(frame_data) == 0:
            return

        axes = self.fig.subplots(1, 2)

        # Image with intensity values
        vmin = np.percentile(self.images[frame], 1)
        vmax = np.percentile(self.images[frame], 99.5)

        axes[0].imshow(self.images[frame], cmap='gray', vmin=vmin, vmax=vmax)

        if len(self.edges[frame]) > 0:
            axes[0].plot(self.edges[frame][:, 1], self.edges[frame][:, 0], 'r-', linewidth=1.5, alpha=0.6)

        # Draw rectangles with intensity colors
        valid_intensities = [p['intensity'] for p in frame_data if p['accepted'] and not np.isnan(p['intensity'])]

        if valid_intensities:
            int_vmin, int_vmax = np.min(valid_intensities), np.max(valid_intensities)

            for j, point_data in enumerate(frame_data):
                if point_data['accepted'] and not np.isnan(point_data['intensity']):
                    rect = self.sampling_rectangles[frame][j]
                    corners = rect['corners']

                    if int_vmax > int_vmin:
                        normalized = (point_data['intensity'] - int_vmin) / (int_vmax - int_vmin)
                    else:
                        normalized = 0.5

                    color = plt.cm.viridis(normalized)
                    poly = plt.Polygon(corners[:, [1, 0]], fill=True, facecolor=color,
                                     edgecolor='white', alpha=0.5, linewidth=1)
                    axes[0].add_patch(poly)

        axes[0].set_title(f'Frame {frame}: Intensity Values')
        axes[0].axis('off')

        # Intensity distribution
        if valid_intensities:
            axes[1].hist(valid_intensities, bins=15, edgecolor='black', alpha=0.7)
            axes[1].axvline(x=np.mean(valid_intensities), color='r', linestyle='--', linewidth=2, label='Mean')
            axes[1].set_xlabel(self.intensity_label)
            axes[1].set_ylabel('Count')
            axes[1].set_title(f'Distribution (Mean: {np.mean(valid_intensities):.1f})')
            axes[1].legend()
            axes[1].grid(True, alpha=0.3)

        self.fig.tight_layout()

    def show_correlation(self):
        """Show correlation analysis results.

        Note: This method is deprecated. Correlation visualization is now
        handled by the dedicated "Correlation Analysis" tab.
        """
        # This method is no longer used - correlation viewing moved to dedicated tab
        return

