"""FastAPI web app for Cell Edge Analysis (individual scripts): front end in static/, JSON API under /api.

Run with `python run_web.py` (http://127.0.0.1:8173, local only). `scripts/build_static.py` exports every path in
STATIC_ENDPOINTS to JSON for the GitHub Pages site, so keep that list in step with the GET routes below.

The Intensity and Fluorescence-edge pages run JavaScript ports (static/edge_engine.js, static/fluor_engine.js) in
the browser in both modes. The local app adds: POST /api/tiff reads any TIFF with tifffile (compressed files too),
and POST /api/analyse and /api/fluor re-run the same frames with the repo's own Python (web/analysis.py,
web/fluor.py) so a browser result can be checked against Python.
"""
import base64
import functools
import json
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from web import analysis, fluor, guide  # noqa: I001  (analysis puts the repo root on sys.path first)
from web.tiff_io import read_stack

STATIC = Path(__file__).resolve().parent / "static"
DEMO = STATIC / "demo"
MAX_UPLOAD_BYTES = 200 * 1024 * 1024
SIBLING = "https://gddickinson.github.io/cell_edge_analysis/"

app = FastAPI(title="Cell Edge Analysis (individual scripts)")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")


def demo_labels():
    d = json.loads((DEMO / "demo_labels.json").read_text())
    return {int(k): v["y"] for k, v in d["frames"].items()}


@functools.lru_cache(maxsize=1)
def demo_stacks():
    img, _, _ = read_stack((DEMO / "demo_piezo1.tif").read_bytes())
    msk, _, _ = read_stack((DEMO / "demo_Mask.tif").read_bytes())
    return img, msk


@app.get("/api/info")
def info():
    """Project summary, defaults (config.PIPELINE_CONFIG), the GUI's normalisation presets and the demo files."""
    from config import NORMALIZATION_PRESETS, PIPELINE_CONFIG
    meta = json.loads((DEMO / "demo_labels.json").read_text())["meta"]
    return {
        "title": "Cell Edge Analysis · individual scripts",
        "repo": "cell_edge_analysis_individual_scripts",
        "sibling": SIBLING,
        "description": "The nine-step PIEZO1 cell-edge pipeline as individual scripts, with the additions this "
                       "repository makes: configurable intensity normalisation (step 1), a per-rectangle intensity "
                       "statistic (step 7) with self-describing labels, and experiments that find the cell edge "
                       "from the PIEZO1 fluorescence instead of the DIC mask.",
        "defaults": analysis.default_params(),
        "choices": analysis.CHOICES,
        "presets": NORMALIZATION_PRESETS,
        "detector": fluor.detector_params(),
        "file_patterns": {"image": PIPELINE_CONFIG["IMAGE_PATTERNS"], "mask": PIPELINE_CONFIG["MASK_PATTERNS"]},
        "demo": {"image": "static/demo/demo_piezo1.tif", "mask": "static/demo/demo_Mask.tif",
                 "labels": "static/demo/demo_labels.json", "dic_offset_px": meta["dic_offset_px"],
                 "note": "SYNTHETIC labelled demo written by scripts/make_demo_data.py (8 frames, 320 x 240 px, fixed "
                         "seed): a moving cell edge with grainy PIEZO1-like signal in a rim just inside it, "
                         "photobleaching, hot pixels (frames 2 and 5) and debris outside the cell (frame 6). The mask "
                         "is a 'DIC' mask displaced from the true edge by a known amount per frame; the true edge is "
                         "stored as labels. Not measured data."},
    }


@app.get("/api/guide")
def guide_sections():
    """The desktop GUI's Help -> Analysis Guide (gui_help_content.py), section by section."""
    return guide.sections()


@app.get("/api/methods")
def methods_demo():
    """All seven candidate edge detectors + the tuned detector on demo frame 4 (Python, precomputed for the site)."""
    img, msk = demo_stacks()
    return fluor.methods(img, msk, 4, demo_labels())


async def _read(upload: UploadFile) -> bytes:
    data = await upload.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File too large for the web app (200 MB); use run_all_steps.py for big stacks.")
    return data


@app.post("/api/tiff")
async def tiff(file: UploadFile = File(...)):
    """Read a TIFF stack with tifffile; float32 pixels as base64 plus shape and the file's own pixel size."""
    try:
        stack, um, source = read_stack(await _read(file))
    except HTTPException:
        raise
    except Exception as e:  # tifffile raises many types for unreadable files
        raise HTTPException(400, f"Could not read {file.filename}: {e}")
    return {"name": file.filename, "shape": list(stack.shape), "um_per_px": um, "scale_source": source,
            "data": base64.b64encode(stack.tobytes()).decode("ascii")}


async def _stacks(image, mask, frames):
    img, _, _ = read_stack(await _read(image))
    msk, _, _ = read_stack(await _read(mask))
    sel = [int(f) for f in frames.split(",") if f.strip()] or None
    if sel and any(f < 0 or f >= img.shape[0] for f in sel):
        raise ValueError(f"frame index out of range (0..{img.shape[0] - 1})")
    return img, msk, sel


@app.post("/api/analyse")
async def analyse(image: UploadFile = File(...), mask: UploadFile = File(...), params: str = Form("{}"),
                  frames: str = Form("")):
    """The repo's Python steps 1, 2, 5, 6, 7 on the uploaded stacks (frames: comma-separated indices)."""
    try:
        img, msk, sel = await _stacks(image, mask, frames)
        return analysis.to_json(analysis.run(img, msk, json.loads(params or "{}"), sel))
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/fluor")
async def fluor_edges(image: UploadFile = File(...), mask: UploadFile = File(...), params: str = Form("{}"),
                      frames: str = Form("")):
    """detector.fluor_edge + the DIC edge on the uploaded stacks (after default step 1), per requested frame."""
    try:
        img, msk, sel = await _stacks(image, mask, frames)
        return fluor.detect(img, msk, json.loads(params or "{}"), sel)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(400, str(e))


# GET paths (without the /api prefix) written to the static site as api/<path>.json.
STATIC_ENDPOINTS = ["/info", "/guide", "/methods"]
