#!/usr/bin/env python3
"""
Tune a DIC-constrained blurred-blob region-boundary detector against the
hand-drawn labels.

The detector: blur the fluorescence, threshold (scaled Otsu) to a bright region,
clean it morphologically, then take the region's top edge per column BUT only
within +/- `band` rows of the DIC edge. The band lets the edge migrate onto the
fluorescence rim (correcting real DIC gaps) while preventing catastrophic jumps
to noise far from the cell. A final 1-D smoothing tidies the curve.

Sweeps parameters, scores by median per-column error vs the labels, reports the
best config with leave-one-out (LOO) validation, and writes overlays to
tuning/results/. Read-only on the pipeline.
"""

import os
import sys
import json
import itertools
import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import disk

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

_HERE = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)
sys.path.insert(0, _PARENT)
import edge_methods as em  # noqa: E402

DATA = os.path.join(os.path.dirname(_PARENT), 'data', 'test_1',
                    'analysis_results', 'step1_results')
LABELS = os.path.join(_PARENT, 'labeling', 'labels', 'labels.json')
OUT = os.path.join(_HERE, 'results')

BLURS = [8, 12, 18]
THR_SCALES = [0.6, 0.8, 1.0]
CLOSES = [0, 6]
BANDS = [80, 150, 300, 99999]    # 99999 = effectively unconstrained (= pure fluor)
CURVE_SIGMAS = [8, 20, 40]
BASELINE = (12, 1.0, 0, 99999, 8)   # ~ the original blob, lightly smoothed


def load_labels():
    d = json.load(open(LABELS))
    out = {}
    for k, fr in d['frames'].items():
        y = np.array([np.nan if v is None else v for v in fr['y']], float)
        if np.isfinite(y).sum() >= 5:
            out[int(k)] = y
    return out


def clean_binary(blurred, otsu, thr_scale, close):
    if otsu is None:
        return None
    b = blurred > (otsu * thr_scale)
    if close > 0:
        b = ndi.binary_closing(b, structure=disk(close))
    return em.largest_component(ndi.binary_fill_holes(b))


def top_edge_banded(binary, dic, band):
    """Uppermost True per column, restricted to +/- band rows of the DIC edge.

    Where the DIC edge is undefined the column stays empty (NaN propagates through
    the comparisons) rather than searching the whole column — that avoids grabbing
    top-of-frame noise far from the cell.
    """
    h = binary.shape[0]
    rows = np.arange(h)[:, None]
    with np.errstate(invalid='ignore'):
        lo = (dic - band)[None, :]
        hi = (dic + band)[None, :]
        valid = binary & (rows >= lo) & (rows <= hi)
    yy = np.where(valid, rows, h + 1)
    top = yy.min(axis=0).astype(float)
    top[top > h] = np.nan
    return top


def with_dic_fallback(yband, dic):
    """Keep the fluorescence edge where found; fall back to the DIC edge elsewhere."""
    return np.where(np.isfinite(yband), yband, dic)


def region_edge(image, mask, blur, thr_scale, close, band, curve_sigma):
    b = ndi.gaussian_filter(image.astype(float), blur)
    binary = clean_binary(b, em._safe_otsu(b), thr_scale, close)
    if binary is None:
        return np.full(image.shape[1], np.nan)
    dic = em.edge_dic(image, mask)
    yb = with_dic_fallback(top_edge_banded(binary, dic, band), dic)
    return em.smooth_curve(yb, curve_sigma)


def frame_error(y_pred, y_true):
    m = np.isfinite(y_pred) & np.isfinite(y_true)
    if m.sum() < 5:
        return np.nan, 0.0
    return float(np.median(np.abs(y_pred[m] - y_true[m]))), float(m.mean())


def build_error_matrix(images, masks, labels, configs):
    idx = {c: i for i, c in enumerate(configs)}
    frames = sorted(labels)
    E = np.full((len(configs), len(frames)), np.nan)
    C = np.zeros_like(E)
    for fj, f in enumerate(frames):
        img = images[f].astype(float)
        dic = em.edge_dic(images[f], masks[f])
        ytrue = labels[f]
        blur_c = {bv: ndi.gaussian_filter(img, bv) for bv in BLURS}
        otsu_c = {bv: em._safe_otsu(blur_c[bv]) for bv in BLURS}
        for blur in BLURS:
            for ts in THR_SCALES:
                for cl in CLOSES:
                    binary = clean_binary(blur_c[blur], otsu_c[blur], ts, cl)
                    for band in BANDS:
                        if binary is not None:
                            ydet = with_dic_fallback(top_edge_banded(binary, dic, band), dic)
                        else:
                            ydet = dic.copy()
                        for cs in CURVE_SIGMAS:
                            y = em.smooth_curve(ydet, cs)
                            ci = idx[(blur, ts, cl, band, cs)]
                            E[ci, fj], C[ci, fj] = frame_error(y, ytrue)
    return E, C, frames


def best_config(E, C, cols=None, min_cov=0.8):
    cols = slice(None) if cols is None else cols
    mean_err = np.nanmean(E[:, cols], axis=1)
    mean_cov = np.nanmean(C[:, cols], axis=1)
    ok = mean_cov >= min_cov
    if not ok.any():
        ok = mean_cov >= 0.0
    return int(np.nanargmin(np.where(ok, mean_err, np.inf)))


def overlay_figure(image, label_y, tuned_y, base_y, dic_y, frame, et, eb, path):
    vmin, vmax = np.percentile(image, 1), np.percentile(image, 99.5)
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.imshow(image, cmap='gray', vmin=vmin, vmax=vmax)
    x = np.arange(len(label_y))
    ax.plot(x, dic_y, '-', color='red', lw=1.0, alpha=0.4, label='DIC')
    ax.plot(x, base_y, '-', color='lime', lw=1.2, alpha=0.7, label=f'blob baseline ({eb:.1f}px)')
    ax.plot(x, tuned_y, '-', color='deepskyblue', lw=1.8, label=f'tuned ({et:.1f}px)')
    ax.plot(x, label_y, '--', color='yellow', lw=2.0, label='your label')
    ax.set_title(f'Frame {frame}: DIC-banded tuned blob vs your label')
    ax.legend(loc='upper right', fontsize=8)
    ax.axis('off')
    fig.tight_layout()
    fig.savefig(path, dpi=130, bbox_inches='tight')
    plt.close(fig)


def summary_bar(frames, e_dic, e_base, e_tuned, path):
    x = np.arange(len(frames))
    w = 0.27
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(x - w, e_dic, w, label='DIC baseline', color='red', alpha=0.7)
    ax.bar(x, e_base, w, label='blob baseline', color='lime', alpha=0.8)
    ax.bar(x + w, e_tuned, w, label='tuned (DIC-banded)', color='deepskyblue')
    ax.set_xticks(x); ax.set_xticklabels(frames)
    ax.set_xlabel('frame'); ax.set_ylabel('median |error| vs label (px)')
    ax.set_title('Per-frame agreement with hand labels (lower = better)')
    ax.legend(); ax.grid(True, axis='y', alpha=0.3)
    fig.tight_layout(); fig.savefig(path, dpi=140, bbox_inches='tight'); plt.close(fig)


def main():
    os.makedirs(OUT, exist_ok=True)
    images = np.load(os.path.join(DATA, 'images.npy'))
    masks = np.load(os.path.join(DATA, 'masks.npy'))
    labels = load_labels()
    configs = list(itertools.product(BLURS, THR_SCALES, CLOSES, BANDS, CURVE_SIGMAS))
    print(f"Labelled frames: {sorted(labels)}\nSweeping {len(configs)} configs...")
    E, C, frames = build_error_matrix(images, masks, labels, configs)

    gi = best_config(E, C)
    gp = configs[gi]
    print(f"\nBest config: blur={gp[0]}, thr_scale={gp[1]}, close={gp[2]}, "
          f"band={gp[3]}, curve_sigma={gp[4]}")
    print(f"  mean error={np.nanmean(E[gi]):.2f}px  median-of-frames={np.nanmedian(E[gi]):.2f}px"
          f"  mean coverage={np.nanmean(C[gi]):.2f}")

    loo = []
    for h in range(len(frames)):
        others = [j for j in range(len(frames)) if j != h]
        loo.append(E[best_config(E, C, cols=others), h])
    loo = np.array(loo)
    print(f"  LOO error: median={np.nanmedian(loo):.2f}px  mean={np.nanmean(loo):.2f}px")

    bi = configs.index(BASELINE)
    e_dic, e_base, e_tuned = [], [], []
    for fj, f in enumerate(frames):
        dic = em.edge_dic(images[f], masks[f])
        e_dic.append(frame_error(dic, labels[f])[0])
        e_base.append(E[bi, fj]); e_tuned.append(E[gi, fj])
        overlay_figure(images[f], labels[f],
                       region_edge(images[f], masks[f], *gp),
                       region_edge(images[f], masks[f], *BASELINE),
                       dic, f, E[gi, fj], E[bi, fj],
                       os.path.join(OUT, f'frame_{f:03d}_tuned.png'))
    summary_bar(frames, e_dic, e_base, e_tuned, os.path.join(OUT, 'error_summary.png'))

    print(f"\n{'frame':>6}{'DIC':>9}{'blob_base':>11}{'tuned':>8}")
    for fj, f in enumerate(frames):
        print(f"{f:>6}{e_dic[fj]:>9.1f}{e_base[fj]:>11.1f}{e_tuned[fj]:>8.1f}")
    print(f"{'MEDIAN':>6}{np.nanmedian(e_dic):>9.1f}"
          f"{np.nanmedian(e_base):>11.1f}{np.nanmedian(e_tuned):>8.1f}")
    print(f"{'MEAN':>6}{np.nanmean(e_dic):>9.1f}"
          f"{np.nanmean(e_base):>11.1f}{np.nanmean(e_tuned):>8.1f}")

    json.dump({'best_params': {'blur': gp[0], 'thr_scale': gp[1], 'close': gp[2],
                               'band': gp[3], 'curve_sigma': gp[4]},
               'tuned_median_px': round(float(np.nanmedian(e_tuned)), 2),
               'tuned_mean_px': round(float(np.nanmean(e_tuned)), 2),
               'loo_median_px': round(float(np.nanmedian(loo)), 2),
               'per_frame': {str(f): {'dic': round(e_dic[i], 1),
                                      'blob_baseline': round(e_base[i], 1),
                                      'tuned': round(e_tuned[i], 1)}
                             for i, f in enumerate(frames)}},
              open(os.path.join(OUT, 'tuning_metrics.json'), 'w'), indent=2)
    print(f"\nResults written to {OUT}")


if __name__ == '__main__':
    main()
