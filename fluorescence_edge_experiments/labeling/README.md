# Edge labeling app — draw every frame, export a mask

Hand-draw the cell edge on **every frame** and **export a binary mask stack** you
can substitute for the DIC mask in the analysis pipeline.

**Reads** a step1 `images.npy` + `masks.npy`; **writes** only into `labels/`.
Nothing in the pipeline is modified until you swap the mask in yourself.

> NOTE: the app needs the dataset's `images.npy` and `masks.npy`. If the default
> `data/test_1/.../step1_results` folder is missing, pass `--data-dir <path>`.

## Run
```bash
cd fluorescence_edge_experiments/labeling
python label_app.py
python label_app.py --data-dir <step1_results dir>
```

## Workflow (labelling a whole movie)
1. **Navigate** all frames: the slider, the ◄/► buttons, ◄◄/►► for first/last,
   the **Left/Right arrow keys**, the frame list, or **Next unlabelled** to jump
   to the next frame without a label. The list shows `[✓]` for done frames and a
   `labelled/total` count.
2. **Draw** the boundary with a **left-drag** on the image (the outer edge of the
   cell / bright region). Multiple strokes are fine — later strokes override the
   columns they cover. Your label is the **yellow** line.
3. Speed-ups for a movie, where the edge moves slowly:
   - **Copy prev label** — duplicate the previous frame's edge, then tweak it.
   - **Seed from auto-edge** — drop in the automated guess and correct it.
4. **Undo stroke** / **Clear frame** as needed. Everything **autosaves** after
   each change and **resumes** when you reopen the app.
5. Toggle **DIC** / **auto** reference overlays. (If a drag doesn't draw, deselect
   the zoom/pan tool in the toolbar first.)

## Export the mask
Click **Export mask (.tif)**. It writes `labels/labeled_mask.tif`:
- a binary stack (`uint8`, 0/255) at the **original image dimensions**,
- for each labelled frame the cell is filled on one side of your line
  (set **cell is [below|above] the line** — default **below**, matching the
  pipeline's `uppermost`-edge convention),
- **unlabelled frames fall back to the original DIC mask**, so the stack is
  always complete and drop-in (the dialog reports how many of each).

### Use it in the pipeline
Either replace the dataset's `*_Mask.tif` with `labeled_mask.tif`, or point step 1
at it directly and re-run from there:
```bash
python step1_data_loading.py --image-stack-path <piezo1.tif> \
                             --mask-stack-path labels/labeled_mask.tif
# then step2 ... step9  (or run_all_steps.py)
```

## Outputs (`labels/`)
- `labels.json` — raw strokes + derived per-column `y(x)` per frame (resumable).
- `labeled_mask.tif` — the exported mask stack for the pipeline (git-ignored: hand-labelled data stays local / on the data drive, not in the repo).
