"""
Figure builders for the fluorescence edge experiments (matplotlib, Agg backend).
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from edge_methods import METHODS


def contrast(image):
    """Percentile contrast limits for displaying a fluorescence frame."""
    return np.percentile(image, 1), np.percentile(image, 99.5)


def _draw_edge(ax, top_y, color, lw=1.6, label=None, alpha=1.0):
    x = np.arange(len(top_y))
    ax.plot(x, top_y, '-', color=color, linewidth=lw, label=label, alpha=alpha)


def figure_methods_for_frame(image, edges_by_method, frame_idx, out_path):
    """One figure per frame: a panel per method (DIC edge shown faint for
    reference) plus a final panel overlaying every method's edge."""
    names = list(edges_by_method.keys())
    dic_y = edges_by_method.get('dic_baseline')
    vmin, vmax = contrast(image)

    n_panels = len(names) + 1  # + overlay
    ncols = 4
    nrows = int(np.ceil(n_panels / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.4 * ncols, 4.4 * nrows))
    axes = np.atleast_1d(axes).ravel()

    for ax, name in zip(axes, names):
        meta = METHODS[name]
        ax.imshow(image, cmap='gray', vmin=vmin, vmax=vmax)
        if name != 'dic_baseline' and dic_y is not None:
            _draw_edge(ax, dic_y, 'red', lw=1.0, alpha=0.5)  # reference
        _draw_edge(ax, edges_by_method[name], meta['color'], lw=1.8)
        ax.set_title(f"{meta['label']}\n[{meta['kind']}]", fontsize=9)
        ax.axis('off')

    # Overlay panel
    ax = axes[len(names)]
    ax.imshow(image, cmap='gray', vmin=vmin, vmax=vmax)
    for name in names:
        _draw_edge(ax, edges_by_method[name], METHODS[name]['color'],
                   lw=1.4, label=METHODS[name]['label'], alpha=0.9)
    ax.set_title('All methods overlaid', fontsize=9)
    ax.legend(loc='upper right', fontsize=6, framealpha=0.8)
    ax.axis('off')

    # Hide any leftover axes
    for ax in axes[n_panels:]:
        ax.axis('off')

    fig.suptitle(f'Frame {frame_idx}: cell-edge candidates on PIEZO1 fluorescence',
                 fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(out_path, dpi=140, bbox_inches='tight')
    plt.close(fig)


def figure_zoom_compare(image, edges_by_method, frame_idx, out_path,
                        compare=('dic_baseline', 'snap', 'chanvese', 'column_band')):
    """A single large overlay of a few key methods, for close inspection."""
    vmin, vmax = contrast(image)
    fig, ax = plt.subplots(figsize=(11, 9))
    ax.imshow(image, cmap='gray', vmin=vmin, vmax=vmax)
    for name in compare:
        if name in edges_by_method:
            _draw_edge(ax, edges_by_method[name], METHODS[name]['color'],
                       lw=2.0, label=METHODS[name]['label'])
    ax.set_title(f'Frame {frame_idx}: key candidates vs DIC baseline', fontsize=13)
    ax.legend(loc='upper right', fontsize=9, framealpha=0.85)
    ax.axis('off')
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)


def figure_timeline(frames, gap, intens_dic, intens_fluor, selected, out_path):
    """Per-frame DIC-vs-fluorescence gap and edge-intensity over the whole stack."""
    fig, axes = plt.subplots(2, 1, figsize=(13, 8), sharex=True)

    axes[0].plot(frames, gap, '-', color='steelblue', lw=1.5)
    axes[0].scatter(selected, gap[selected], color='red', zorder=5,
                    label='Illustrated frames')
    axes[0].axhline(np.nanmedian(gap), color='gray', ls='--', lw=1,
                    label=f'median = {np.nanmedian(gap):.1f}px')
    axes[0].set_ylabel('DIC vs fluor edge gap (px)')
    axes[0].set_title('Per-frame disagreement between the DIC mask edge and the '
                      'fluorescence edge\n(larger = DIC edge sits further from the PIEZO1 signal)')
    axes[0].legend(fontsize=9)
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(frames, intens_dic, '-', color='red', lw=1.5,
                 label='along DIC edge')
    axes[1].plot(frames, intens_fluor, '-', color='yellow', lw=1.5,
                 label='along fluor edge', markeredgecolor='k')
    axes[1].set_xlabel('Frame')
    axes[1].set_ylabel('PIEZO1 intensity at edge')
    axes[1].set_title('Fluorescence intensity sampled along each edge '
                      '(higher = edge sits on the bright PIEZO1 signal)')
    axes[1].legend(fontsize=9)
    axes[1].grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(out_path, dpi=140, bbox_inches='tight')
    plt.close(fig)
