"""Write the SYNTHETIC, labelled demo data used by the web pages (web/static/demo/).

Not measured data: no real recording is published. The stack imitates the situations the individual scripts were
written for, with a known answer:

- demo_piezo1.tif: a scratch-assay-like cell sheet below a wavy leading edge that moves from frame to frame, with grainy
  (punctate) PIEZO1-like signal concentrated in a rim just inside the edge, slow photobleaching over the stack, a few
  hot pixels (frames 2 and 5) and a bright piece of debris outside the cell (frame 6). These are what the step 1
  normalisation options (percentile / in-mask / global) and the step 7 statistic are about.
- demo_Mask.tif: a "DIC" cell mask whose edge is displaced from the true (fluorescent) edge by a different, known
  amount in every frame, as the DIC-segmented masks were in the fluorescence_edge_experiments.
- demo_labels.json: the true edge y(x) of every frame, in the labelling tool's format (labeling/label_io.py:
  {"meta": {...}, "frames": {"<frame>": {"y": [...]}}}), standing in for hand labels.

File names follow the pipeline's rule (`*piezo1.tif`, `*Mask.tif`); uncompressed so the browser can read them.
Deterministic (fixed seed). Run: python scripts/make_demo_data.py
"""
import json
from pathlib import Path

import numpy as np
import tifffile
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "static" / "demo"
DEMO = {"frames": 8, "height": 240, "width": 320, "seed": 2026, "um_per_px": 0.16}
# Known offset of the DIC mask edge from the true edge in each frame (px, + = DIC edge lower, inside the cell).
DIC_OFFSET = [2, -10, 34, 5, 52, -22, 66, 8]
NOTE = ("SYNTHETIC labelled demo written by scripts/make_demo_data.py (8 frames, 320 x 240 px, fixed seed): a moving "
        "cell edge with grainy PIEZO1-like signal in a rim just inside it, photobleaching, hot pixels (frames 2, 5) and "
        "debris outside the cell (frame 6); the mask is a 'DIC' mask displaced from the true edge by a known amount "
        "per frame, and the true edge is stored as labels. Not measured data.")


def true_edge(x, t):
    """Row of the true (fluorescent) leading edge at column x in frame t; the cell lies below it."""
    return 92 + 16 * np.sin(2 * np.pi * x / 200 + 0.55 * t) + 6 * np.sin(2 * np.pi * x / 67 - 0.9 * t)


def dic_edge(x, t):
    """Row of the 'DIC' mask edge: the true edge plus the frame's known offset and a gentle wobble."""
    return true_edge(x, t) + DIC_OFFSET[t] + 4 * np.sin(2 * np.pi * x / 140 + t)


def make_stack():
    T, H, W = DEMO["frames"], DEMO["height"], DEMO["width"]
    rng = np.random.default_rng(DEMO["seed"])
    rows, cols = np.mgrid[0:H, 0:W].astype(float)
    x = np.arange(W, dtype=float)
    images = np.zeros((T, H, W), np.uint16)
    masks = np.zeros((T, H, W), np.uint8)
    labels = {}
    for t in range(T):
        e = true_edge(x, t)
        depth = rows - e[None, :]                       # > 0 inside the cell
        inside = depth > 0
        # grainy rim: random puncta, lightly blurred, strongest within ~20 px of the edge
        puncta = ndi.gaussian_filter((rng.random((H, W)) < 0.06).astype(float), 1.2) * 18
        rim = np.exp(-np.clip(depth, 0, None) / 18) * (0.35 + puncta)
        body = 0.18 * np.exp(-np.clip(depth, 0, None) / 120)
        bleach = 1 - 0.07 * t
        img = 100 + inside * bleach * (900 * rim + 900 * body) + rng.normal(0, 12, (H, W))
        if t in (2, 5):                                 # hot pixels outside the cell
            for _ in range(6):
                r, c = int(rng.integers(5, 40)), int(rng.integers(5, W - 5))
                img[r, c] = 30000
        if t == 6:                                      # bright debris outside the cell
            img += 20000 * np.exp(-((rows - 22) ** 2 + (cols - 250) ** 2) / (2 * 4.0 ** 2))
        images[t] = np.clip(np.round(img), 0, 65535).astype(np.uint16)
        masks[t] = (rows > dic_edge(x, t)[None, :]).astype(np.uint8) * 255
        labels[str(t)] = {"y": [round(float(v), 3) for v in e]}
    meta = {"width": W, "height": H, "definition": "true fluorescent edge, per-column y(x) (synthetic)",
            "synthetic": True, "dic_offset_px": DIC_OFFSET}
    return images, masks, {"meta": meta, "frames": labels}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    images, masks, labels = make_stack()
    res = (1 / DEMO["um_per_px"], 1 / DEMO["um_per_px"])
    meta = {"unit": "um", "axes": "TYX"}
    tifffile.imwrite(OUT / "demo_piezo1.tif", images, imagej=True, resolution=res, metadata=meta)
    tifffile.imwrite(OUT / "demo_Mask.tif", masks, imagej=True, resolution=res, metadata=meta)
    (OUT / "demo_labels.json").write_text(json.dumps(labels, separators=(",", ":")))
    print(f"wrote {OUT}: demo_piezo1.tif, demo_Mask.tif {images.shape}, demo_labels.json")


if __name__ == "__main__":
    main()
