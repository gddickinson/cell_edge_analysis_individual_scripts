#!/usr/bin/env python3
"""
Extend an already-exported mask stack to the full left/right frame width.

Each frame's region is extended to the image edges by replicating the outermost
columns that contain cell pixels (the drawn boundary is held flat out to each
edge). Operates directly on labeled_mask.tif, so it does NOT need the original
image/mask data. The original is backed up once to *_preedge.tif.

    cd fluorescence_edge_experiments/labeling
    python fix_mask_edges.py                       # fixes labels/labeled_mask.tif in place
    python fix_mask_edges.py --mask <path> --output <path>
"""

import os
import sys
import shutil
import argparse
import numpy as np
import tifffile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import label_io


def main():
    ap = argparse.ArgumentParser(description='Extend mask frames to the L/R edges')
    ap.add_argument('--mask', default=os.path.join(_HERE, 'labels', 'labeled_mask.tif'))
    ap.add_argument('--output', default=None, help='default: overwrite input (backs up original)')
    args = ap.parse_args()

    if not os.path.exists(args.mask):
        print(f"Not found: {args.mask}")
        return
    m = tifffile.imread(args.mask)
    out = args.output or args.mask
    if out == args.mask:
        backup = args.mask.replace('.tif', '_preedge.tif')
        if not os.path.exists(backup):
            shutil.copy2(args.mask, backup)
            print(f"Backed up original -> {backup}")

    for i in range(m.shape[0]):
        label_io.extend_mask_frame(m[i])
    tifffile.imwrite(out, m)

    W = m.shape[2]
    cols = (m > 0).any(axis=1)
    full = int(sum(c.any() and c[0] and c[-1] for c in cols))
    print(f"Wrote {out}")
    print(f"  {m.shape}, {m.dtype}; frames spanning full width: {full}/{m.shape[0]}")


if __name__ == '__main__':
    main()
