// Home page: hero, facts from the repo (/api/info), links to the pages and to the sibling site.
import { route, app, api, esc, isStatic } from './core.js';

route('home', async () => {
  const info = await api('/info'), c = info.choices;
  const combos = c.normalization_method.length * c.normalization_region.length * c.normalization_scope.length;
  app().innerHTML = `<section class="hero"><p class="kicker">PIEZO1 · cell edge dynamics · individual scripts</p>
    <h1 class="glow">Cell edge analysis, script by script</h1>
    <p class="lead">${esc(info.description)}</p>
    <a class="btn" href="#/intensity">Compare intensity settings</a><a class="btn alt" href="#/edges">Find the edge from fluorescence</a></section>
    <div class="tiles">
      <div class="tile"><b>9</b><span>step scripts (step1 … step9)</span></div>
      <div class="tile"><b>${combos}</b><span>normalisation reference choices (step 1)</span></div>
      <div class="tile"><b>${c.intensity_statistic.length}</b><span>per-rectangle statistics (step 7)</span></div>
      <div class="tile"><b>7 + 1</b><span>fluorescence edge methods + tuned detector</span></div></div>
    <div class="callout a small">This site focuses on what the individual-scripts repo adds. The full nine-step
      analyser (edge sampling and rectangle options, CSV export) is on the sibling site:
      <a href="${esc(info.sibling)}" target="_blank" rel="noopener">cell_edge_analysis</a>.
      ${isStatic() ? 'Everything here runs in your browser; your images are not uploaded.' : ''}</div>
    <div class="grid">
      <a class="card" href="#/intensity"><b>Intensity scale</b><span>Step 1 normalisation (max or percentile, whole frame or in-mask, per frame or whole stack) and the step 7 statistic, against the defaults, with the self-describing axis label.</span></a>
      <a class="card" href="#/edges"><b>Fluorescence edge</b><span>The tuned detector from fluorescence_edge_experiments on every frame, the DIC-vs-fluorescence gap, errors against labels, and all seven candidate methods.</span></a>
      <a class="card" href="#/guide"><b>Analysis guide</b><span>The desktop GUI's Help → Analysis Guide: purpose, maths and defaults of every step.</span></a>
      <a class="card" href="#/about"><b>About</b><span>How to run the scripts, the GUI and this web app; credits.</span></a>
    </div>`;
});
