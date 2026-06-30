#!/usr/bin/env python3
"""
Run the cell-edge-from-fluorescence experiments and generate comparison figures.

EXPLORATORY: reads the existing step-1 outputs (PIEZO1 images + DIC masks) but
writes ONLY into this folder's results/ directory. Nothing in the main pipeline
is modified.

Usage:
    python run_experiments.py                      # auto-select frames from test_1
    python run_experiments.py --frames 5 40 88     # specific frames
    python run_experiments.py --data-dir <step1_results dir> --y-selection uppermost
"""

import os
import sys
import glob
import json
import argparse
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edge_methods as em
import viz

DEFAULT_DATA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data', 'test_1', 'analysis_results', 'step1_results')


def parse_args():
    p = argparse.ArgumentParser(description='Cell-edge-from-fluorescence experiments')
    p.add_argument('--data-dir', default=DEFAULT_DATA,
                   help='Folder containing images.npy and masks.npy (step1_results)')
    p.add_argument('--output-dir', default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'results'))
    p.add_argument('--frames', type=int, nargs='*', default=None,
                   help='Explicit frame indices to illustrate (overrides auto-select)')
    p.add_argument('--n-worst', type=int, default=3, help='Worst-gap frames to show')
    p.add_argument('--n-best', type=int, default=2, help='Best-gap frames to show')
    p.add_argument('--y-selection', default='uppermost',
                   choices=['uppermost', 'lowermost'])
    return p.parse_args()


def intensity_along_edge(image, top_y, halfwin=1):
    """Median PIEZO1 intensity sampled at the edge (max over +/-halfwin rows)."""
    h, w = image.shape
    vals = []
    for x in range(w):
        y = top_y[x]
        if not np.isfinite(y):
            continue
        yi = int(round(y))
        vals.append(image[max(0, yi - halfwin):min(h, yi + halfwin + 1), x].max())
    return float(np.median(vals)) if vals else np.nan


def gap_between(a, b):
    """Median absolute vertical distance between two per-column edges."""
    m = np.isfinite(a) & np.isfinite(b)
    return float(np.median(np.abs(a[m] - b[m]))) if m.any() else np.nan


def coverage(top_y):
    return float(np.mean(np.isfinite(top_y)))


def per_frame_metrics(images, masks):
    """Cheap pass over ALL frames: DIC vs fluorescence-reference gap + edge intensity.

    The reference is the robust region-based 'blob' edge (heavy blur + threshold),
    NOT a per-column threshold: grainy PIEZO1 signal makes naive per-column /
    ridge tracing latch onto noise, which would corrupt the gap metric.
    """
    n = images.shape[0]
    gap = np.full(n, np.nan)
    intens_dic = np.full(n, np.nan)
    intens_fluor = np.full(n, np.nan)
    for i in range(n):
        dic = em.edge_dic(images[i], masks[i])
        fluor = em.edge_blob(images[i], masks[i])
        gap[i] = gap_between(dic, fluor)
        intens_dic[i] = intensity_along_edge(images[i], dic)
        intens_fluor[i] = intensity_along_edge(images[i], fluor)
    return gap, intens_dic, intens_fluor


def select_frames(gap, n_worst, n_best):
    valid = np.where(np.isfinite(gap))[0]
    order = valid[np.argsort(gap[valid])]
    if order.size == 0:
        return [0]
    best = list(order[:n_best])
    worst = list(order[-n_worst:][::-1])
    median = [int(order[len(order) // 2])]
    return sorted(set(best + worst + median))


def main():
    args = parse_args()
    em.SELECT = args.y_selection
    os.makedirs(args.output_dir, exist_ok=True)
    # Clear stale per-frame figures so the folder reflects only this run
    for old in glob.glob(os.path.join(args.output_dir, 'frame_*.png')):
        os.remove(old)

    images = np.load(os.path.join(args.data_dir, 'images.npy'))
    masks = np.load(os.path.join(args.data_dir, 'masks.npy'))
    print(f"Loaded {images.shape[0]} frames of {images.shape[1]}x{images.shape[2]}")

    # 1) Whole-stack gap + edge-intensity timeline
    print("Scanning all frames for DIC-vs-fluorescence disagreement...")
    gap, intens_dic, intens_fluor = per_frame_metrics(images, masks)

    if args.frames is not None:
        selected = sorted(set(args.frames))
    else:
        selected = select_frames(gap, args.n_worst, args.n_best)
    selected = [int(s) for s in selected]
    print(f"Illustrating frames: {selected}")

    viz.figure_timeline(np.arange(images.shape[0]), gap, intens_dic, intens_fluor,
                        np.array(selected), os.path.join(args.output_dir, 'gap_timeline.png'))

    # 2) Per-frame: run ALL methods, build figures, collect metrics
    method_names = list(em.METHODS.keys())
    agg = {n: {'intensity': [], 'gap_to_dic': [], 'coverage': []} for n in method_names}
    edges_store = {}

    for fi in selected:
        image, mask = images[fi], masks[fi]
        edges = {}
        for name in method_names:
            try:
                edges[name] = em.compute_edge(name, image, mask)
            except Exception as e:
                print(f"  frame {fi} method {name} failed: {e}")
                edges[name] = np.full(image.shape[1], np.nan)
        edges_store[str(fi)] = {n: edges[n].tolist() for n in method_names}

        dic = edges['dic_baseline']
        for name in method_names:
            agg[name]['intensity'].append(intensity_along_edge(image, edges[name]))
            agg[name]['gap_to_dic'].append(gap_between(edges[name], dic))
            agg[name]['coverage'].append(coverage(edges[name]))

        viz.figure_methods_for_frame(
            image, edges, fi, os.path.join(args.output_dir, f'frame_{fi:03d}_methods.png'))
        viz.figure_zoom_compare(
            image, edges, fi, os.path.join(args.output_dir, f'frame_{fi:03d}_keycompare.png'))
        print(f"  frame {fi}: figures written")

    # 3) Aggregate metrics
    summary = {}
    for name in method_names:
        summary[name] = {
            'label': em.METHODS[name]['label'],
            'kind': em.METHODS[name]['kind'],
            'median_intensity_at_edge': round(float(np.nanmedian(agg[name]['intensity'])), 2),
            'median_gap_to_dic_px': round(float(np.nanmedian(agg[name]['gap_to_dic'])), 2),
            'mean_coverage': round(float(np.nanmean(agg[name]['coverage'])), 3),
        }

    with open(os.path.join(args.output_dir, 'metrics.json'), 'w') as f:
        json.dump({'frames': selected,
                   'whole_stack_gap_median_px': round(float(np.nanmedian(gap)), 2),
                   'whole_stack_gap_max_px': round(float(np.nanmax(gap)), 2),
                   'per_method': summary}, f, indent=2)
    np.savez_compressed(os.path.join(args.output_dir, 'edges.npz'),
                        gap=gap, intens_dic=intens_dic, intens_fluor=intens_fluor,
                        selected=np.array(selected))

    # 4) Console summary
    print("\n=== Whole-stack DIC-vs-fluor gap: "
          f"median {np.nanmedian(gap):.1f}px, max {np.nanmax(gap):.1f}px ===")
    print(f"{'method':<34}{'kind':<7}{'I@edge':>8}{'gap_DIC':>9}{'cover':>7}")
    for name in method_names:
        s = summary[name]
        print(f"{s['label']:<34}{s['kind']:<7}{s['median_intensity_at_edge']:>8}"
              f"{s['median_gap_to_dic_px']:>9}{s['mean_coverage']:>7}")
    print(f"\nResults written to: {args.output_dir}")


if __name__ == '__main__':
    main()
