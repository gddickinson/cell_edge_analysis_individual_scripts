"""Web interface tests: every exported endpoint answers, the static build is complete, and the JS engine tests pass.

Run: python -m pytest -q tests/test_web.py
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from web.app import STATIC, STATIC_ENDPOINTS, app  # noqa: E402

client = TestClient(app)


def test_index_served():
    r = client.get("/")
    assert r.status_code == 200 and "static/main.js" in r.text


@pytest.mark.parametrize("path", STATIC_ENDPOINTS)
def test_endpoint(path):
    r = client.get("/api" + path)
    assert r.status_code == 200, r.text
    assert r.json() is not None


def test_static_build(tmp_path):
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_static
    build_static.build(tmp_path / "site")
    assert (tmp_path / "site" / "index.html").read_text().count("APP_STATIC") == 1
    for path in STATIC_ENDPOINTS:
        assert (tmp_path / "site" / "api" / (path.strip("/") + ".json")).exists()


def test_static_assets_referenced_exist():
    html = (STATIC / "index.html").read_text()
    for name in ("style.css", "main.js"):
        assert f"static/{name}" in html and (STATIC / name).exists()


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_js_engine():
    tests = sorted(STATIC.glob("*.test.mjs"))
    for t in tests:
        r = subprocess.run(["node", str(t)], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr


# ---- project-specific API tests ---------------------------------------------------------------------------------
DEMO = STATIC / "demo"
FILES = lambda: {"image": ("i.tif", (DEMO / "demo_piezo1.tif").read_bytes()),  # noqa: E731
                 "mask": ("m.tif", (DEMO / "demo_Mask.tif").read_bytes())}


def test_info_defaults_and_presets_come_from_config():
    from config import NORMALIZATION_PRESETS, PIPELINE_CONFIG
    d = client.get("/api/info").json()
    assert d["defaults"]["normalization_method"] == PIPELINE_CONFIG["step1"]["normalization_method"]
    assert d["defaults"]["intensity_statistic"] == PIPELINE_CONFIG["step7"]["intensity_statistic"]
    assert d["defaults"]["n_points"] == PIPELINE_CONFIG["step5"]["n_points"]
    assert d["presets"] == NORMALIZATION_PRESETS
    for k in ("image", "mask", "labels"):
        assert (STATIC / d["demo"][k].removeprefix("static/")).exists()
    assert d["sibling"].startswith("https://gddickinson.github.io/cell_edge_analysis/")


def test_guide_is_the_gui_help_text():
    import gui_help_content
    d = client.get("/api/guide").json()
    assert [(s["title"], s["body"]) for s in d["sections"]] == list(gui_help_content.HELP_SECTIONS)


def test_methods_endpoint_runs_every_candidate():
    from web.fluor import em
    d = client.get("/api/methods").json()
    names = [m["name"] for m in d["methods"]]
    assert names == list(em.METHODS) + ["detector"]
    assert all(len(m["edge"]) == 320 for m in d["methods"])
    assert d["methods"][0]["gap_to_dic"] == 0.0  # the DIC baseline against itself


def test_tiff_endpoint_reads_demo_with_pixel_size():
    r = client.post("/api/tiff", files={"file": ("demo_piezo1.tif", (DEMO / "demo_piezo1.tif").read_bytes())})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["shape"] == [8, 240, 320] and abs(d["um_per_px"] - 0.16) < 1e-6


def test_tiff_endpoint_rejects_garbage():
    r = client.post("/api/tiff", files={"file": ("x.tif", b"not a tiff")})
    assert r.status_code == 400


def test_analyse_endpoint_uses_normalisation_options_and_labels():
    params = {"normalization_method": "percentile", "normalization_region": "mask", "normalization_scope": "global",
              "intensity_statistic": "max"}
    r = client.post("/api/analyse", files=FILES(), data={"params": json.dumps(params), "frames": "2"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["label"] == "PIEZO1 intensity (max, % of stack in-mask 99.9th pct)"
    assert len(set(d["references"])) == 1 and [f["frame"] for f in d["frames"]] == [2]
    assert any(x["accepted"] and x["intensity"] is not None for x in d["frames"][0]["rects"])


def test_analyse_endpoint_rejects_bad_params():
    r = client.post("/api/analyse", files=FILES(), data={"params": '{"normalization_scope": "weekly"}'})
    assert r.status_code == 400


def test_fluor_endpoint_runs_the_detector():
    r = client.post("/api/fluor", files=FILES(), data={"params": '{"blur": 12}', "frames": "4"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["params"]["blur"] == 12.0 and len(d["frames"]) == 1 and len(d["frames"][0]["fluor"]) == 320
    r = client.post("/api/fluor", files=FILES(), data={"params": '{"sigma": 3}'})
    assert r.status_code == 400
