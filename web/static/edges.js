// Fluorescence edge page: the exploratory fluorescence_edge_experiments package. The tuned detector (detector.py
// fluor_edge, ported in fluor_engine.js) runs in the browser on every frame with adjustable parameters, next to the
// DIC mask edge, with the per-frame DIC-vs-fluorescence gap (the experiments' QC metric) and, when labels are loaded,
// each edge's error against them (the tuning score). The seven candidate methods are shown from Python (/api/methods,
// precomputed on the demo). The local app can re-run a frame with the Python detector (POST /api/fluor).
import { route, app, api, esc, isStatic, needsServer } from './core.js';
import { preprocessStack } from './intensity_engine.js';
import { fluorEdge, edgeDic, frameError, gapBetween, median } from './fluor_engine.js';
import { shared, dataPanel } from './stack_io.js';
import { drawFrame, drawCurves, lineChart, fmt } from './plots.js';
import { methodsPanel } from './edges_methods.js';

const S = { params: null, frame: 0, version: -1, pre: null, res: [], token: 0 };
const SPEC = [
  ['blur', 'Gaussian blur sigma (px)', 1, 40, 1], ['thr_scale', 'threshold × Otsu', 0.3, 1.6, 0.05],
  ['close', 'closing radius (px)', 0, 15, 1], ['band', 'band around the DIC edge (± px)', 0, 300, 5],
  ['median_size', 'despike median window (columns)', 1, 41, 1], ['curve_sigma', 'curve smoothing sigma (columns)', 1, 30, 1],
];
const COL = { dic: '#ff4d4d', fluor: '#5dff9e', truth: '#ffffff' };

route('edges', async (args) => {
  const info = await api('/info');
  S.params = S.params || { ...info.detector };
  S.info = info;
  app().innerHTML = `<p class="kicker">Exploratory · fluorescence_edge_experiments</p><h1>Edge from the fluorescence</h1>
    <p class="lead">Every measurement in the pipeline is placed relative to the cell edge, and that edge comes from a
      mask segmented on the DIC image. In some frames the DIC edge sits on the PIEZO1 signal, in others it is drawn far
      from it. The experiments in this repo find the edge from the fluorescence instead. The tuned detector blurs the
      PIEZO1 image, thresholds it at Otsu, closes and fills the region, and takes its top edge within a band around the
      DIC edge, falling back to the DIC edge where there is no signal. It is <b>not wired into the pipeline</b>.</p>
    <div class="callout a small">The detector runs <b>in your browser</b> (a JavaScript port of <code>detector.py</code>
      and the scipy / scikit-image calls it makes, checked against Python by a test) on step-1 output with the pipeline's
      default settings, as the experiments read it.</div>
    <div id="data"></div>
    <div class="panel"><h3 style="margin-top:0">Detector settings <span class="small mute">(defaults: detector.BEST, tuned on 10 hand-labelled frames)</span></h3>
      <div class="params" id="ctl"></div>
      <label class="chk" for="p-restrict"><input id="p-restrict" type="checkbox" ${S.params.restrict_to_dic ? 'checked' : ''}>restrict to the DIC edge's x-extent</label>
      <button id="p-reset" class="alt" type="button">Reset to detector.BEST</button></div>
    <div id="out"></div>
    <div id="methods"></div>
    <div class="panel"><h3 style="margin-top:0">On the real recording</h3>
      <p class="small">From <code>fluorescence_edge_experiments/tuning/RESULTS.md</code> (10 hand-labelled frames of one
        real dataset; the data are not published here). Median |error| against the labels, px:</p>
      <div class="scroll"><table><thead><tr><th></th><th>DIC mask</th><th>blob baseline</th><th>tuned detector</th></tr></thead>
        <tbody><tr><td>median over frames</td><td class="num">28.9</td><td class="num">20.6</td><td class="num">14.7</td></tr>
        <tr><td>mean over frames</td><td class="num">37.5</td><td class="num">24.9</td><td class="num">16.5</td></tr>
        <tr><td>leave-one-out median</td><td class="num">—</td><td class="num">—</td><td class="num">18.0</td></tr></tbody></table></div>
      <p class="small mute">RESULTS.md also notes that the parameters were tuned on one dataset and need re-validating on
        more data, and the experiments' README asks the open question of what the edge should represent: the membrane's
        outer rim or the bright-signal region boundary.</p></div>`;
  controls();
  const panel = dataPanel(document.getElementById('data'), info, { labels: true }, () => compute());
  document.getElementById('p-restrict').onchange = e => { S.params.restrict_to_dic = e.target.checked; compute(); };
  document.getElementById('p-reset').onclick = () => { S.params = { ...info.detector }; document.getElementById('p-restrict').checked = S.params.restrict_to_dic; controls(); compute(); };
  methodsPanel(document.getElementById('methods'), info);
  if (shared.stack) compute();
  else panel.demo();
});

function controls() {
  const host = document.getElementById('ctl');
  host.innerHTML = SPEC.map(([k, l, a, b, s]) => `<div class="ctl"><label for="d-${k}">${l} <b id="v-${k}">${S.params[k]}</b></label>
    <input id="d-${k}" type="range" min="${a}" max="${b}" step="${s}" value="${S.params[k]}"></div>`).join('');
  for (const [k] of SPEC) {
    const el = document.getElementById(`d-${k}`);
    el.oninput = () => { document.getElementById(`v-${k}`).textContent = el.value; };
    el.onchange = () => { S.params[k] = +el.value; compute(); };
  }
}

async function compute() {
  if (!shared.stack) return;
  const st = shared.stack, token = ++S.token, T = st.images.length;
  if (S.version !== shared.version) {
    S.pre = preprocessStack(st.images, st.masks, S.info.defaults).frames;
    S.version = shared.version; S.frame = Math.min(S.frame, T - 1);
  }
  S.res = [];
  const status = () => { const o = document.getElementById('out'); if (o && S.res.length < T) o.innerHTML = `<div class="panel"><p class="mute" role="status">Detecting edges: frame ${S.res.length + 1} of ${T}...</p></div>`; };
  status();
  for (let i = 0; i < T; i++) {
    await new Promise(r => setTimeout(r, 0));
    if (token !== S.token) return;
    const dic = edgeDic(st.masks[i], st.h, st.w), fl = fluorEdge(S.pre[i], st.masks[i], st.h, st.w, S.params);
    const truth = shared.labels ? shared.labels[i] : null;
    S.res.push({ frame: i, dic, fluor: fl, truth, gap: gapBetween(fl, dic),
      eDic: truth ? frameError(dic, truth) : null, eFl: truth ? frameError(fl, truth) : null });
    status();
  }
  render();
}

function render() {
  const T = S.res.length, lab = S.res.some(r => r.truth);
  const pts = f => S.res.map(r => [r.frame, f(r)]);
  const md = f => { const v = S.res.map(f).filter(x => x != null && Number.isFinite(x)); return v.length ? median(v) : null; };
  const errs = lab ? `<div class="tiles"><div class="tile"><b>${fmt(md(r => r.eDic?.median), 1)}</b><span>DIC edge: median error vs labels (px)</span></div>
      <div class="tile"><b>${fmt(md(r => r.eFl?.median), 1)}</b><span>detector: median error vs labels (px)</span></div>
      <div class="tile"><b>${fmt(md(r => r.gap), 1)}</b><span>median DIC-vs-detector gap (px)</span></div></div>` : '';
  const chart = lineChart([
    { name: 'gap: detector vs DIC edge', color: 'var(--accent3)', pts: pts(r => r.gap ?? NaN) },
    ...(lab ? [{ name: 'DIC edge error vs labels', color: COL.dic, pts: pts(r => r.eDic?.median ?? NaN) },
      { name: 'detector error vs labels', color: COL.fluor, pts: pts(r => r.eFl?.median ?? NaN) }] : [])],
  { xl: 'frame', yl: 'median |Δy| (px)', aria: 'Per-frame gap and errors', mark: S.frame, yZero: true });
  document.getElementById('out').innerHTML = `<div class="panel"><h3 style="margin-top:0">Every frame</h3>${errs}<div class="chart-w">${chart}</div>
    <p class="small mute">The gap (median |detector − DIC| over columns, <code>run_experiments.gap_between</code>) flags
      frames where the DIC edge is suspect, without labels. Errors are <code>tune_blob.frame_error</code>: the median
      |edge − label| over columns where both are defined.${shared.meta.demo ? ` Synthetic demo: the DIC mask edge was
      displaced from the true edge by ${esc(S.info.demo.dic_offset_px.join(', '))} px in frames 0-${T - 1}; the labels
      are the true edge. The synthetic signal is cleaner than real data, so every method does better here.` : ''}</p></div>
    <div class="panel"><h3 style="margin-top:0">One frame</h3>
      <div class="ctl"><label for="fr">Frame <b id="fr-n">${S.frame}</b> of ${T - 1}</label>
        <input id="fr" type="range" min="0" max="${T - 1}" value="${S.frame}" ${T > 1 ? '' : 'disabled'}></div>
      <div class="stage"><canvas id="cv" role="img" aria-label="Frame with the DIC edge, the detector edge and the labels"></canvas></div>
      <div class="legend small"><span class="lg"><i style="background:${COL.dic}"></i>DIC mask edge</span>
        <span class="lg"><i style="background:${COL.fluor}"></i>detector edge</span>${lab ? `<span class="lg"><i style="background:${COL.truth}"></i>labels (dashed)</span>` : ''}</div>
      <p id="fr-sum" class="small"></p>
      <div>${isStatic() ? '' : '<button id="b-py" class="alt" type="button">Check with Python</button>'}<span id="py" class="small" role="status"></span></div>
      ${isStatic() ? needsServer('"Check with Python" (re-running the frame with detector.py)') : ''}</div>`;
  const fr = document.getElementById('fr');
  fr.oninput = () => { S.frame = +fr.value; document.getElementById('fr-n').textContent = S.frame; frameView(); };
  const py = document.getElementById('b-py');
  if (py) py.onclick = checkPython;
  frameView();
}

function frameView() {
  const st = shared.stack, r = S.res[S.frame], cv = document.getElementById('cv');
  drawFrame(cv, st, { frame: S.frame, edge: [], rects: [], sampled: [] }, { mask: false, range: [0, 1] });
  const curves = [{ y: r.dic, color: COL.dic }, { y: r.fluor, color: COL.fluor, width: 2.5 }];
  if (r.truth) curves.push({ y: r.truth, color: COL.truth, dash: [6, 5], width: 1.5 });
  drawCurves(cv, curves, st.w, st.h);
  document.getElementById('fr-sum').innerHTML = `Frame ${S.frame}: gap ${fmt(r.gap, 1)} px` +
    (r.truth ? `; median error vs labels: DIC ${fmt(r.eDic?.median, 1)} px, detector ${fmt(r.eFl?.median, 1)} px.` : '.');
}

async function checkPython() {
  const out = document.getElementById('py'), btn = document.getElementById('b-py'), r = S.res[S.frame];
  btn.disabled = true; out.textContent = 'Running detector.py...';
  try {
    const fd = new FormData();
    fd.append('image', shared.files.image, shared.files.image.name); fd.append('mask', shared.files.mask, shared.files.mask.name);
    fd.append('params', JSON.stringify(S.params)); fd.append('frames', String(S.frame));
    const q = (await api('/fluor', { body: fd })).frames[0];
    let d = 0, nan = 0;
    q.fluor.forEach((v, i) => { const a = r.fluor[i]; if ((v == null) !== !Number.isFinite(a)) nan++; else if (v != null) d = Math.max(d, Math.abs(a - v)); });
    out.innerHTML = `<span class="${d < 1e-6 && !nan ? 'status-ok' : 'status-bad'}">Python detector: max |Δy| ${d.toExponential(1)} px over ${q.fluor.length} columns; ${nan} defined/undefined differences.</span>`;
  } catch (e) { out.innerHTML = `<span class="status-bad">${esc(e.message)}</span>`; }
  finally { btn.disabled = false; }
}
