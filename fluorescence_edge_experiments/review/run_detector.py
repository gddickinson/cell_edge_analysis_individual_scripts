#!/usr/bin/env python3
"""
Run the tuned fluorescence edge detector over the whole movie and save the
results for review. Read-only on the pipeline.

Outputs (review/out/):
  detected_edges.npz  - edges (n x w), dic_edges (n x w), gap (n)
  montage.png         - every Nth frame with detected edge, for a quick overview
"""

import os
import sys
import argparse
import numpy as np

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

_HERE = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)
sys.path.insert(0, _PARENT)
import detector
import edge_methods as em

DATA = os.path.join(os.path.dirname(_PARENT), 'data', 'test_1',
                    'analysis_results', 'step1_results')
OUT = os.path.join(_HERE, 'out')


def montage(images, edges, dic_edges, path, n_show=20):
    n = images.shape[0]
    idxs = np.linspace(0, n - 1, min(n_show, n)).round().astype(int)
    cols = 5
    rows = int(np.ceil(len(idxs) / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(3.2 * cols, 3.0 * rows))
    axes = np.atleast_1d(axes).ravel()
    x = np.arange(images.shape[2])
    for ax, fi in zip(axes, idxs):
        img = images[fi]
        ax.imshow(img, cmap='gray',
                  vmin=np.percentile(img, 1), vmax=np.percentile(img, 99.5))
        ax.plot(x, dic_edges[fi], '-', color='red', lw=0.8, alpha=0.4)
        ax.plot(x, edges[fi], '-', color='deepskyblue', lw=1.3)
        ax.set_title(f'frame {fi}', fontsize=8)
        ax.axis('off')
    for ax in axes[len(idxs):]:
        ax.axis('off')
    fig.suptitle('Detected fluorescence edge (blue) vs DIC (red)', fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(path, dpi=130, bbox_inches='tight')
    plt.close(fig)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--data-dir', default=DATA)
    p.add_argument('--output-dir', default=OUT)
    args = p.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    images = np.load(os.path.join(args.data_dir, 'images.npy'))
    masks = np.load(os.path.join(args.data_dir, 'masks.npy'))
    print(f"Detecting edges on {images.shape[0]} frames...")

    edges = detector.detect_all(images, masks)
    dic_edges = np.array([em.edge_dic(images[i], masks[i]) for i in range(images.shape[0])])

    gap = np.full(images.shape[0], np.nan)
    for i in range(images.shape[0]):
        m = np.isfinite(edges[i]) & np.isfinite(dic_edges[i])
        if m.any():
            gap[i] = float(np.median(np.abs(edges[i][m] - dic_edges[i][m])))

    np.savez_compressed(os.path.join(args.output_dir, 'detected_edges.npz'),
                        edges=edges, dic_edges=dic_edges, gap=gap)
    montage(images, edges, dic_edges, os.path.join(args.output_dir, 'montage.png'))

    print(f"Median DIC-vs-detected shift: {np.nanmedian(gap):.1f}px "
          f"(max {np.nanmax(gap):.1f}px)")
    print(f"Saved edges + montage to {args.output_dir}")
    print("Review interactively with:  python review/review_app.py")


if __name__ == '__main__':
    main()
