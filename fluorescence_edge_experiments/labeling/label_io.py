"""
Shared I/O and geometry helpers for the hand-labeling app.

A label for a frame is an ordered list of "segments" (each a list of [x, y]
points the user drew). Later segments overwrite earlier columns, so you can seed
from the blob suggestion and then redraw only the wrong parts. The authoritative
boundary is the derived per-column curve y(x) (one row per column), which matches
the pipeline's edge representation and the candidate detectors' output.
"""

import os
import sys
import json
import numpy as np

# Make the parent experiment package importable (edge_methods.py).
_PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)
import edge_methods as em  # noqa: E402


def blob_suggestion(image, mask):
    """The blurred-blob fluorescence edge, used as an editable starting curve."""
    return em.edge_blob(image, mask)


def dic_edge(image, mask):
    """The current DIC mask edge, shown faint for reference."""
    return em.edge_dic(image, mask)


def segments_to_yx(segments, width, height=None):
    """Rasterise drawn segments to a per-column boundary y(x).

    Each segment is interpolated across its own x-span; later segments overwrite
    earlier columns (so corrections drawn after a seed win). Columns never drawn
    on remain NaN.
    """
    y = np.full(width, np.nan)
    for seg in segments:
        pts = np.asarray(seg, dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 1:
            continue
        xi = np.round(pts[:, 0]).astype(int)
        keep = (xi >= 0) & (xi < width)
        xi, yy = xi[keep], pts[keep, 1]
        if xi.size == 0:
            continue
        ux = np.unique(xi)
        uy = np.array([yy[xi == v].mean() for v in ux])
        if ux.size == 1:
            y[ux[0]] = uy[0]
            continue
        grid = np.arange(ux.min(), ux.max() + 1)
        y[grid] = np.interp(grid, ux, uy)
    if height is not None:
        with np.errstate(invalid='ignore'):
            y = np.where(np.isfinite(y), np.clip(y, 0, height - 1), np.nan)
    return y


def labels_path(label_dir):
    return os.path.join(label_dir, 'labels.json')


def load_labels(label_dir):
    """Return {frame_int: [segment, ...]} from a previous session, or {}."""
    path = labels_path(label_dir)
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    out = {}
    for k, v in data.get('frames', {}).items():
        out[int(k)] = [np.asarray(s, float).tolist() for s in v.get('segments', [])]
    return out


def save_labels(label_dir, segments_by_frame, width, height, meta=None):
    """Persist segments + the derived y(x) for every labelled frame."""
    os.makedirs(label_dir, exist_ok=True)
    frames = {}
    for f, segs in segments_by_frame.items():
        if not segs:
            continue
        y = segments_to_yx(segs, width, height)
        frames[str(int(f))] = {
            'segments': [np.asarray(s, float).tolist() for s in segs],
            'y': [None if not np.isfinite(v) else round(float(v), 2) for v in y],
        }
    payload = {
        'meta': {'width': int(width), 'height': int(height),
                 'definition': 'bright-signal region boundary (per-column y(x))',
                 **(meta or {})},
        'frames': frames,
    }
    with open(labels_path(label_dir), 'w') as f:
        json.dump(payload, f, indent=2)
    return len(frames)


def extend_mask_frame(frame):
    """Extend a binary mask frame to the left/right image edges.

    Replicates the outermost columns that contain any cell pixel out to the
    frame borders, so the masked region spans the full width (the boundary is
    held flat from the last drawn column to each edge). Modifies in place.
    """
    cols = np.where((frame > 0).any(axis=0))[0]
    if cols.size == 0:
        return frame
    left, right = cols[0], cols[-1]
    if left > 0:
        frame[:, :left] = frame[:, left:left + 1]
    if right < frame.shape[1] - 1:
        frame[:, right + 1:] = frame[:, right:right + 1]
    return frame


def save_snapshot(image, y, dic, blob, frame_idx, path):
    """Write a PNG of the image with the final label (and references) overlaid."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    vmin, vmax = np.percentile(image, 1), np.percentile(image, 99.5)
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.imshow(image, cmap='gray', vmin=vmin, vmax=vmax)
    x = np.arange(len(y))
    if dic is not None:
        ax.plot(x, dic, '-', color='red', lw=1.0, alpha=0.5, label='DIC edge')
    if blob is not None:
        ax.plot(x, blob, '-', color='lime', lw=1.0, alpha=0.5, label='blob suggestion')
    ax.plot(x, y, '-', color='yellow', lw=2.2, label='your label')
    ax.set_title(f'Frame {frame_idx}: hand-labelled bright-signal boundary')
    ax.legend(loc='upper right', fontsize=8)
    ax.axis('off')
    fig.tight_layout()
    fig.savefig(path, dpi=130, bbox_inches='tight')
    plt.close(fig)
