// About page: what the project is, how to run the scripts, the desktop GUI and the web app, credits.
import { route, app, api, esc } from './core.js';

route('about', async () => {
  const info = await api('/info');
  app().innerHTML = `<p class="kicker">About</p><h1>Cell Edge Analysis · individual scripts</h1>
    <p class="lead">A Python pipeline for analysing PIEZO1 protein localisation and cell edge dynamics in fluorescence
      microscopy, as nine standalone scripts (<code>step1_data_loading.py</code> … <code>step9_correlation_analysis.py</code>)
      with a batch runner and a Tkinter GUI. It detects the cell edge from a mask in every frame, measures PIEZO1
      intensity in rectangles just inside the edge, and correlates that intensity with how the edge moves.</p>
    <p>Compared with the sibling repository <a href="${esc(info.sibling)}" target="_blank" rel="noopener">cell_edge_analysis</a>,
      this one adds configurable intensity normalisation in step 1, a per-rectangle statistic in step 7, axis labels
      that state both (<code>intensity_labels.py</code>), a Help → Analysis Guide, tooltips and presets in the GUI, and
      the exploratory <code>fluorescence_edge_experiments/</code> package (candidate detectors, a labelling app, a tuning
      script and the tuned <code>detector.py</code>).</p>
    <h2>Run the pipeline</h2>
    <pre>pip install -r requirements.txt
# data/&lt;dataset&gt;/&lt;name&gt;${esc(info.file_patterns.image[0])} and &lt;name&gt;${esc(info.file_patterns.mask[0])}
python run_all_steps.py --batch                 # every dataset under data/
python run_all_steps.py --batch --dataset exp1  # one dataset
python summarize_batch_results.py results/      # table of all datasets</pre>
    <p>Defaults live in <code>config.py</code> (<code>PIPELINE_CONFIG</code>), used by <code>run_all_steps.py</code> and the
      GUI; every step script also takes them on the command line (<code>--help</code>), e.g.
      <code>--normalization-method percentile --normalization-region mask --normalization-scope global</code> (step 1) and
      <code>--intensity-statistic max</code> (step 7). Main result per dataset:
      <code>results/&lt;dataset&gt;/step9_results/final_analysis_summary.json</code>.</p>
    <h2>Desktop GUI</h2>
    <pre>python launch_gui.py       # or: python cell_edge_analysis_gui.py</pre>
    <h2>Fluorescence edge experiments</h2>
    <pre>cd fluorescence_edge_experiments
python run_experiments.py          # method comparison on step-1 output
python labeling/label_app.py       # hand-label edges (labels.json)
python tuning/tune_blob.py         # tune the detector against the labels</pre>
    <h2>Run the web app</h2>
    <pre>pip install -r requirements-web.txt
python run_web.py          # http://127.0.0.1:8173</pre>
    <p>Both analysis pages run JavaScript ports in the browser (<code>edge_engine.js</code>, <code>intensity_engine.js</code>,
      <code>fluor_engine.js</code>), here and on the static GitHub Pages site; node tests check them against the repo's
      Python on the demo data. The local app adds TIFF reading with tifffile (compressed files) and "Check with Python"
      buttons.</p>
    <p class="small">${esc(info.demo.note)} It was written by <code>scripts/make_demo_data.py</code>; no measured data are published on this site.</p>
    <h2>Credits</h2>
    <p>George Dickinson. Built with assistance from <a href="https://claude.com/" target="_blank" rel="noopener">Claude
      (Anthropic)</a>. Licence: MIT. Source:
      <a href="https://github.com/gddickinson/${esc(info.repo)}" target="_blank" rel="noopener">github.com/gddickinson/${esc(info.repo)}</a>.</p>`;
});
