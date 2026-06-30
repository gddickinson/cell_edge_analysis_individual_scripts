"""
Curate a diverse set of frames to hand-label.

Picks frames spanning the full range of DIC-vs-fluorescence disagreement (the
'blob' gap), so the labelled set includes well-matched frames, moderate ones,
and badly-misplaced ones. Avoids near-adjacent frames so the labels are not
redundant.
"""

import os
import sys
import json
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)
import edge_methods as em  # noqa: E402


def _gap(dic, blob):
    m = np.isfinite(dic) & np.isfinite(blob)
    return float(np.median(np.abs(dic[m] - blob[m]))) if m.any() else np.nan


def compute_gaps(images, masks):
    gaps = np.full(images.shape[0], np.nan)
    for i in range(images.shape[0]):
        gaps[i] = _gap(em.edge_dic(images[i], masks[i]),
                       em.edge_blob(images[i], masks[i]))
    return gaps


def curate_frames(images, masks, n=12, min_separation=3):
    """Return [(frame, gap_px), ...] spread across the gap distribution."""
    gaps = compute_gaps(images, masks)
    valid = np.where(np.isfinite(gaps))[0]
    if valid.size == 0:
        return []
    order = valid[np.argsort(gaps[valid])]  # ascending gap (good -> bad)
    picks = np.linspace(0, order.size - 1, min(n, order.size)).round().astype(int)
    chosen = []
    for k in picks:
        f = int(order[k])
        if all(abs(f - c) >= min_separation for c in chosen):
            chosen.append(f)
    chosen = sorted(set(chosen))
    return [(f, round(float(gaps[f]), 1)) for f in chosen]


def queue_path(label_dir):
    return os.path.join(label_dir, 'frames_to_label.json')


def load_or_create_queue(images, masks, label_dir, n=12):
    """Load a saved labeling queue, or curate one and save it."""
    path = queue_path(label_dir)
    if os.path.exists(path):
        try:
            with open(path) as f:
                items = json.load(f)['frames']
            return [(int(it['frame']), float(it['gap'])) for it in items]
        except (json.JSONDecodeError, OSError, KeyError):
            pass
    os.makedirs(label_dir, exist_ok=True)
    queue = curate_frames(images, masks, n=n)
    with open(path, 'w') as f:
        json.dump({'frames': [{'frame': fr, 'gap': g} for fr, g in queue]}, f, indent=2)
    return queue


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description='Curate frames to hand-label')
    p.add_argument('--data-dir', default=os.path.join(
        os.path.dirname(_PARENT), 'data', 'test_1', 'analysis_results', 'step1_results'))
    p.add_argument('--label-dir', default=os.path.join(_HERE, 'labels'))
    p.add_argument('--n', type=int, default=12)
    a = p.parse_args()
    imgs = np.load(os.path.join(a.data_dir, 'images.npy'))
    msks = np.load(os.path.join(a.data_dir, 'masks.npy'))
    q = load_or_create_queue(imgs, msks, a.label_dir, n=a.n)
    print(f"Curated {len(q)} frames (frame, gap_px):")
    for fr, g in q:
        print(f"  frame {fr:3d}  gap {g:6.1f}px")
    print(f"Saved to {queue_path(a.label_dir)}")
