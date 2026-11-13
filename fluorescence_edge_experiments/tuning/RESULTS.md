# Blob tuning vs hand labels — results

Validated the fluorescence edge detector against your 10 hand-labelled frames
(`labeling/labels/labels.json`). Read-only on the pipeline.

## Recommended detector: DIC-banded smoothed blob
1. Gaussian-blur the PIEZO1 image (sigma **18**) to average away the grain.
2. Threshold at **1.0 × Otsu**, morphological **close (r=6)**, fill holes, keep
   the largest region.
3. Take the region's **top edge per column, but only within ±150 px of the DIC
   edge** (the band stops it jumping to noise far from the cell).
4. Where the band has no fluorescence signal, **fall back to the DIC edge**
   (handles frames where the labelled boundary is faint, e.g. frame 86).
5. Smooth the resulting curve (1-D Gaussian, sigma **8**).

`best_params = {blur: 18, thr_scale: 1.0, close: 6, band: 150, curve_sigma: 8}`

## Agreement with your labels (median |error| in px)
| | DIC mask | blob baseline | tuned (this) |
|---|---|---|---|
| median over frames | 28.9 | 20.6 | **14.7** |
| mean over frames | 37.5 | 24.9 | **16.5** |
| leave-one-out median | — | — | **18.0** |

It roughly **halves** the DIC edge error and is robust — no catastrophic frames
(the earlier 465 px / NaN failures are fixed by the NaN-DIC handling + fallback).
Where DIC was already accurate (frames 51, 62) the tuned edge costs a few px;
where DIC was badly off (frames 1, 14, 80) it corrects 40–80 px.

## Note (2026-11-12): closing at the image border
The numbers above were produced with scipy's `binary_closing`, which also eroded a `close`-pixel strip wherever
the bright region touched the image border (its erosion treated the outside as background). The detector and this
script now use `edge_methods.close_binary` (outside = foreground for the erosion), so the outer columns can differ
slightly from these results; re-run `tune_blob.py` on the labelled data to refresh them.

## Known refinements (not yet done)
- **Border spikes**: a few columns at the left/right edges (where the DIC edge is
  undefined) can spike; trim/clamp the outer columns.
- Frame 22 remains the hardest (~38 px) — genuinely ambiguous bright region.
- Params tuned on 10 frames from one dataset; re-validate on more data before trusting broadly.

## Reproduce
```bash
cd fluorescence_edge_experiments/tuning
python tune_blob.py        # writes results/ (overlays, error_summary.png, tuning_metrics.json)
```

## Next step (needs your go-ahead — would touch the pipeline)
Draft `step2_edge_from_fluorescence.py` as an **alternative** edge source: run this
detector over all frames, output the same `edges.pkl` format step 3+ expect, so it
can be swapped in without changing later steps. Not started — the pipeline is
untouched until you approve.
