# Cell edge from PIEZO1 fluorescence — exploration

**Status: exploratory. Nothing here is wired into the main pipeline.** It only
*reads* the existing step-1 outputs (`images.npy` = PIEZO1, `masks.npy` = DIC mask)
and writes figures/metrics into `results/`. Use it to review options before we
decide whether/how to change the pipeline's edge (step 2).

## The problem

The cell mask is segmented from the **DIC** image. In some frames its edge sits
right on the PIEZO1 fluorescence; in others it is drawn far from the signal,
leaving a gap. Because every downstream measurement (displacement, sampling
rectangles, intensity) is positioned **relative to that edge**, a misplaced edge
biases the correlation analysis.

## What the experiment shows (on `data/test_1`)

- The DIC edge and a fluorescence-based edge disagree by a **median of ~48 px**
  and **up to ~197 px**, and the disagreement is strongly **frame-dependent**
  (`results/gap_timeline.png`, top panel). Compare a good frame
  (`frame_051_keycompare.png`: DIC ≈ fluorescence) with a bad one
  (`frame_090_keycompare.png`: DIC sits ~100 px off the bright region).
- The fluorescence edge sits on **consistently brighter** PIEZO1 signal than the
  DIC edge across almost the whole movie (`gap_timeline.png`, bottom panel) —
  i.e. the DIC edge often lies in dimmer territory than the signal.
- **The PIEZO1 signal is grainy.** Naive per-column and ridge tracers latch onto
  noise and are unusable here (the wild yellow/magenta lines in the
  `*_methods.png` panels). Only methods that **average noise away** (heavy blur /
  region segmentation) or are **anchored to the DIC prior** stay sensible.

### Important caveat — what is "the edge"?
Different methods encode different *definitions*, and they genuinely disagree on
this data:
- **Membrane outer boundary** — the outermost rim of PIEZO1 signal (what the DIC
  mask roughly targets).
- **Intensity region boundary** — an iso-intensity contour of the (blurred)
  fluorescence, which sits partway up the intensity gradient and tends to land
  *inside* the membrane rim.

So a large DIC-vs-fluorescence "gap" is partly a real error and partly a
definitional difference. Picking a method = picking a definition. **This is the
main thing to decide before integrating anything** (see "Open question").

## The options (all implemented & tested — `edge_methods.py`)

Each method returns a per-column edge `y(x)` (matching the pipeline's
`uppermost`-edge geometry; convert to step-2's `(y,x)` contour with
`top_y_to_contour`). Colours below match the figures.

### A. Fluorescence only
| Method | Idea | On this data |
|---|---|---|
| **Otsu region** (cyan) | global Otsu threshold → largest filled region → top edge | finds bright signal but **fragmented** (coverage ~0.3–0.5) |
| **Blurred blob** (lime) | heavy Gaussian blur merges puncta → threshold → region boundary | **robust**; relocates onto the fluorescence; partial coverage on the right |
| **Top-of-band per column** (yellow) | per column, first sustained above-threshold run | **fails** — follows noise on grainy signal |
| **Sato ridge** (magenta) | ridge filter enhances the membrane band → topmost ridge | **fails** here — fires on noise/borders |

### B. Combination (DIC + fluorescence)
| Method | Idea | On this data |
|---|---|---|
| **Chan–Vese** (orange) | active-contour segmentation seeded by the DIC mask, ~200 iters | smooth, but the cell/background **mean-intensity contrast is too weak**, so it barely migrates off the DIC seed (under-corrects on bad frames) |
| **DIC → snap to fluor peak** (deepskyblue) | move each DIC edge column to the brightest pixel within ±N rows | corrects **small** offsets well; ±30 px window can't reach the ~100 px errors |

### C. Diagnostic (no new edge — just flags bad frames)
The per-frame **DIC-vs-fluorescence gap** (`gap_timeline.png`) is itself useful:
it pinpoints which frames are suspect, so you could **exclude or down-weight**
them in the correlation analysis without changing the segmentation at all.

## Recommendation (for review)

No method is a turnkey winner on this noisy data, but the promising direction is:

1. **Denoise first, then segment a region** — the blur-then-threshold (`blob`)
   approach is the only fluorescence-only method that survives the grain. A
   refined version (denoise → threshold → morphological cleanup → take the rim,
   not the mid-gradient contour) is worth developing.
2. **Keep the DIC mask as a prior, but let it move further** — either a
   `snap` with a larger, signal-gated search window, or `blob`/active-contour
   constrained to stay within a band around the DIC edge. This corrects gross
   errors while staying robust where fluorescence is ambiguous.
3. **Ship the gap metric as QC regardless** — it's cheap, needs no new edge, and
   directly protects the correlation from the worst frames.

## Open question for you

What should the edge represent — the **membrane outer rim** or the **bright-signal
region boundary**? Hand-marking the "true" edge on ~3–5 frames (including good and
bad ones) would let us tune and *validate* a method instead of guessing. Tell me
which definition you want and I'll refine the matching method.

## How to run / reproduce
```bash
cd fluorescence_edge_experiments
python run_experiments.py                 # auto-selects good & bad frames
python run_experiments.py --frames 51 90  # inspect specific frames
python run_experiments.py --y-selection lowermost   # if the front faces down
```

## Files & outputs
- `edge_methods.py` — the 7 candidate detectors + helpers (uniform `fn(image, mask) -> y(x)`).
- `viz.py` — figure builders. `run_experiments.py` — orchestration + metrics.
- `results/gap_timeline.png` — per-frame DIC-vs-fluor gap and edge-intensity over the whole stack.
- `results/frame_XXX_methods.png` — every method on one frame (DIC shown faint for reference).
- `results/frame_XXX_keycompare.png` — large overlay of the key candidates.
- `results/metrics.json`, `results/edges.npz` — numbers behind the figures.

### Metrics (median over the illustrated frames)
`median_intensity_at_edge` (higher = edge sits on brighter signal),
`median_gap_to_dic_px` (how far it moved from DIC), `mean_coverage`
(fraction of columns with a defined edge). See `results/metrics.json`.
