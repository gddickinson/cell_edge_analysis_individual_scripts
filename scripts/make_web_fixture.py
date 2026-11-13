"""Write tests/fixtures/web_fixture.json: Python reference values for the JS ports in web/static/.

Everything is computed by the repo's own code (web/analysis.py and web/fluor.py call the step scripts,
intensity_labels and fluorescence_edge_experiments) or by the library calls that code makes:
  - intensity: steps 1, 2, 5, 6, 7 on the synthetic demo stack for several normalisation / statistic settings
    (edge_engine.js + intensity_engine.js)
  - labels: intensity_labels.build_intensity_label for many option combinations
  - percentile: numpy.percentile of a float32 demo frame
  - fluor: scipy gaussian_filter / binary_closing / binary_fill_holes / label, skimage threshold_otsu, the detector's
    despike / smooth_curve on small inputs, and detector.fluor_edge + edge_dic on the demo (fluor_engine.js)
tests/test_web_fixture.py checks the fixture is current; web/static/*.test.mjs check JS against it.

Run: python scripts/make_web_fixture.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy import ndimage as ndi
from skimage.morphology import disk

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from web import analysis, fluor  # noqa: E402

OUT = ROOT / "tests" / "fixtures" / "web_fixture.json"
DEMO = ROOT / "web" / "static" / "demo"

INTENSITY_CASES = [
    {"name": "defaults", "params": {}},
    {"name": "robust_max", "params": {"normalization_method": "percentile", "normalization_region": "mask",
                                      "normalization_scope": "global", "intensity_statistic": "max"}},
    {"name": "pct_frame_p90", "params": {"normalization_method": "percentile", "normalization_percentile": 99.5,
                                         "normalization_scale": 1.0, "intensity_statistic": "percentile",
                                         "intensity_percentile": 90}, "frames": [1, 2, 6]},
    {"name": "max_mask_global_flip", "params": {"normalization_region": "mask", "normalization_scope": "global",
                                                "subtract_background": False, "sampling_method": "per_frame",
                                                "rotation_method": "flip", "width": 15, "depth": 30}},
    {"name": "raw_median", "params": {"normalize_frames": False, "intensity_statistic": "percentile",
                                      "intensity_percentile": 50, "background_percentile": 25}, "frames": [0, 5]},
]
LABEL_CASES = [
    {}, {"normalize_frames": False}, {"normalization_scale": 1.0}, {"normalization_scale": 37.5},
    {"normalization_method": "percentile"}, {"normalization_method": "percentile", "normalization_percentile": 95},
    {"normalization_method": "percentile", "normalization_percentile": 99.95, "normalization_region": "mask",
     "normalization_scope": "global"}, {"intensity_statistic": "max"},
    {"intensity_statistic": "percentile", "intensity_percentile": 97.5}, {"intensity_statistic": "percentile"},
]
FLUOR_CASES = [
    {"name": "defaults", "params": {}, "frames": None},
    {"name": "small_blur_no_close", "params": {"blur": 6, "close": 0, "band": 40, "curve_sigma": 3,
                                               "median_size": 4, "restrict_to_dic": False}, "frames": [2, 4]},
    {"name": "thr_low", "params": {"blur": 10, "thr_scale": 0.6, "close": 3, "median_size": 1}, "frames": [6]},
]


def demo():
    return tifffile.imread(DEMO / "demo_piezo1.tif"), tifffile.imread(DEMO / "demo_Mask.tif")


def summarise_edges(res):
    for f in res["frames"]:
        e = np.array(f["edge"], float).reshape(-1, 2)
        f["edge"] = {"n": len(e), "sum": e.sum(axis=0).tolist() if len(e) else [0, 0],
                     "first": e[0].tolist() if len(e) else None, "last": e[-1].tolist() if len(e) else None}
    return res


def small_binaries():
    rng = np.random.default_rng(5)
    out = [(rng.random((30, 40)) > 0.55), (rng.random((25, 25)) > 0.35)]
    ring = np.zeros((20, 24), bool)
    ring[3:15, 4:18] = True
    ring[6:11, 8:13] = False          # a hole
    ring[0:4, 20:24] = True           # touches the border
    out.append(ring)
    return [b.astype(np.uint8) for b in out]


def fluor_parts(pre):
    rng = np.random.default_rng(9)
    img = rng.normal(10, 3, (21, 27))
    curves = [np.r_[np.nan, np.nan, np.sin(np.arange(40) / 4) * 9 + rng.normal(0, 2, 40), np.nan],
              np.r_[np.arange(30.0), np.full(3, np.nan), np.arange(30.0) + 50, [np.nan]]]
    curves[0][[10, 11, 25]] = np.nan
    blurred = ndi.gaussian_filter(pre[4].astype(float), 18)
    return {
        "gaussian": [{"img": img.tolist(), "sigma": s, "out": ndi.gaussian_filter(img, s).tolist()} for s in (1.5, 4.0)],
        "otsu": [{"values": v.ravel().tolist(), "t": fluor.em._safe_otsu(v)} for v in
                 (img, np.round(img), np.r_[np.zeros(50), np.ones(30) * 7.5, rng.normal(3, 1, 40)])]
        + [{"demo_frame": 4, "blur": 18, "t": fluor.em._safe_otsu(blurred)}],
        "binary": [{"bin": b.tolist(), "closing3": ndi.binary_closing(b, structure=disk(3)).astype(int).tolist(),
                    "fill": ndi.binary_fill_holes(b).astype(int).tolist(),
                    "largest": fluor.em.largest_component(b > 0).astype(int).tolist()} for b in small_binaries()],
        "curves": [{"y": [None if np.isnan(v) else v for v in c],
                    "despike": [analysis.num(v) for v in fluor.detector._despike(c.copy(), 5)],
                    "despike4": [analysis.num(v) for v in fluor.detector._despike(c.copy(), 4)],
                    "smooth": [analysis.num(v) for v in fluor.em.smooth_curve(c.copy(), 3.0)]} for c in curves],
    }


def build():
    images, masks = demo()
    pre, _ = analysis.preprocess(images, masks)
    labels = {int(k): v["y"] for k, v in json.loads((DEMO / "demo_labels.json").read_text())["frames"].items()}
    intensity = []
    for c in INTENSITY_CASES:
        res = summarise_edges(analysis.to_json(analysis.run(images, masks, c["params"], c.get("frames"))))
        intensity.append({"name": c["name"], "frames_requested": c.get("frames"), "result": res})
    lab = []
    for c in LABEL_CASES:
        p = analysis.clean_params(c)
        lab.append({"params": p, "label": analysis.label(p)})
    frame0 = images[0].astype(np.float32)
    return {
        "demo": {"image": "web/static/demo/demo_piezo1.tif", "mask": "web/static/demo/demo_Mask.tif",
                 "labels": "web/static/demo/demo_labels.json", "shape": list(images.shape),
                 "checksum": [int(images.astype(np.int64).sum()), int((masks > 0).sum())]},
        "percentile": [{"p": p, "value": float(np.percentile(frame0, p))} for p in (0, 10, 25, 37.5, 99.9, 100)],
        "intensity": intensity,
        "labels": lab,
        "fluor_parts": fluor_parts(pre),
        "fluor": [{"name": c["name"], "frames_requested": c["frames"],
                   "result": fluor.detect(images, masks, c["params"], c["frames"], labels)} for c in FLUOR_CASES],
    }


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(build(), separators=(",", ":")))
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e3:.0f} kB)")


if __name__ == "__main__":
    main()
