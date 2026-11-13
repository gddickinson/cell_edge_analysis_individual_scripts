"""The JS-vs-Python fixture (tests/fixtures/web_fixture.json) is still what the repo's Python code produces.

Regenerate with `python scripts/make_web_fixture.py` after changing steps 1, 2, 5, 6, 7, intensity_labels.py,
fluorescence_edge_experiments/ or the demo data. Floats are compared with rtol 1e-6 / atol 1e-9 (libm differs in the
last digit between platforms). Skipped when CI is set: the fixture holds discrete choices made from float maths
(Otsu thresholds, accepted rectangles, first rows above a threshold) that can flip on another platform's libm; the
node tests that compare the JS ports with the committed fixture still run there.
"""
import json
import math
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def _same(a, b, path=""):
    if isinstance(a, dict):
        assert isinstance(b, dict) and a.keys() == b.keys(), path
        for k in a:
            _same(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list):
        assert isinstance(b, list) and len(a) == len(b), f"{path}: length {len(a)} vs {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            _same(x, y, f"{path}[{i}]")
    elif isinstance(a, float) or isinstance(b, float):
        assert a is not None and b is not None, path
        assert math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-9), f"{path}: {a} vs {b}"
    else:
        assert a == b, f"{path}: {a!r} vs {b!r}"


@pytest.mark.skipif(bool(os.environ.get("CI")), reason="discrete choices from float maths can differ on CI's libm")
def test_fixture_is_current():
    import make_web_fixture
    stored = json.loads(make_web_fixture.OUT.read_text())
    fresh = json.loads(json.dumps(make_web_fixture.build()))
    _same(fresh, stored)


@pytest.mark.skipif(bool(os.environ.get("CI")), reason="as above")
def test_demo_data_is_current():
    import make_demo_data
    import numpy as np
    import tifffile
    images, masks, labels = make_demo_data.make_stack()
    assert np.array_equal(images, tifffile.imread(make_demo_data.OUT / "demo_piezo1.tif"))
    assert np.array_equal(masks, tifffile.imread(make_demo_data.OUT / "demo_Mask.tif"))
    _same(json.loads(json.dumps(labels)), json.loads((make_demo_data.OUT / "demo_labels.json").read_text()))
