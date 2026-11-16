"""Regression: the step scripts are found when the pipeline or GUI is started from another working directory.

Before the fix, run_all_steps.py and the GUI ran `python step1_data_loading.py` relative to the current directory, so
`python /path/to/run_all_steps.py` from anywhere else failed with "can't open file".
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def test_run_all_steps_resolves_scripts_from_repo(tmp_path, monkeypatch):
    import run_all_steps
    seen = []
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: seen.append(cmd))
    assert run_all_steps.run_step(1, "step1_data_loading.py", "Data Loading")
    script = Path(seen[0][1])
    assert script.is_absolute() and script == ROOT / "step1_data_loading.py"


def test_gui_resolves_scripts_from_repo(tmp_path, monkeypatch):
    import cell_edge_analysis_gui as gui_mod

    class Var:
        def __init__(self, v): self.v = v
        def get(self): return self.v

    class Proc:
        stdout = []
        returncode = 0
        def wait(self): return 0

    seen = []
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(gui_mod.subprocess, "Popen", lambda cmd, **kw: seen.append(cmd) or Proc())
    gui = gui_mod.AnalysisGUI.__new__(gui_mod.AnalysisGUI)   # no Tk window needed for run_step
    gui.output_base_dir = Var(str(tmp_path / "out"))
    gui.log = lambda msg: None
    gui.smooth_edges, gui.smoothing_sigma = Var(True), Var(20.0)
    assert gui.run_step("step2_edge_detection.py", "Edge Detection")
    script = Path(seen[0][1])
    assert script.is_absolute() and script == ROOT / "step2_edge_detection.py"
