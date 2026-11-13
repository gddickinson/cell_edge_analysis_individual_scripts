// Intensity scale page: what the step 1 normalisation options and the step 7 per-rectangle statistic (the options this
// repo adds) do to the measured PIEZO1 intensity. Runs steps 1, 2, 5, 6, 7 in the browser (edge_engine.js +
// intensity_engine.js) with the chosen settings and with the pipeline defaults side by side. The local app can re-run
// the frame with the repo's Python (POST /api/analyse).
import { route, app, api, esc, isStatic, download, needsServer } from './core.js';
import { runIntensity, preprocessStack } from './intensity_engine.js';
import { shared, dataPanel } from './stack_io.js';
import { drawFrame, lineChart, intensityRange, fmt } from './plots.js';

const S = { params: null, frame: 0, version: -1, cur: null, def: null };
const STEP1 = ['normalize_frames', 'normalization_method', 'normalization_percentile', 'normalization_region',
  'normalization_scope', 'normalization_scale', 'subtract_background', 'background_percentile'];
const HELP = {
  normalization_method: 'max: the brightest pixel maps to the scale; percentile: a high percentile does, so a few hot pixels cannot set the ceiling.',
  normalization_region: 'frame: reference from the whole image; mask: only from pixels inside the cell mask (ignores debris outside).',
  normalization_scope: 'per_frame: every frame has its own reference; global: one reference for the whole stack (frame-to-frame comparable).',
  intensity_statistic: 'How the pixels inside each sampling rectangle are aggregated (step 7).',
};

const seg = (k, choices, v) => `<div class="field"><span class="flabel" id="l-${k}" title="${esc(HELP[k] || '')}">${k.replace(/_/g, ' ')}</span>
  <div class="seg" role="group" aria-labelledby="l-${k}">${choices.map(c => `<button type="button" data-k="${k}" data-v="${c}" class="${c === v ? 'on' : ''}" aria-pressed="${c === v}">${c}</button>`).join('')}</div></div>`;
const num = (k, v, step = 'any') => `<div class="field"><label for="p-${k}">${k.replace(/_/g, ' ')}</label><input id="p-${k}" data-k="${k}" type="number" min="0" step="${step}" value="${v}"></div>`;
const chk = (k, v) => `<label class="chk" for="p-${k}"><input id="p-${k}" data-k="${k}" type="checkbox" ${v ? 'checked' : ''}>${k.replace(/_/g, ' ')}</label>`;

function controls(info) {
  const p = S.params, c = info.choices;
  return `<div class="params">
    <fieldset><legend>Step 1 · normalisation</legend>${chk('subtract_background', p.subtract_background)}
      ${num('background_percentile', p.background_percentile)}${chk('normalize_frames', p.normalize_frames)}
      ${seg('normalization_method', c.normalization_method, p.normalization_method)}${num('normalization_percentile', p.normalization_percentile)}
      ${seg('normalization_region', c.normalization_region, p.normalization_region)}
      ${seg('normalization_scope', c.normalization_scope, p.normalization_scope)}${num('normalization_scale', p.normalization_scale)}
      <div><button type="button" id="pr-default" class="alt">Default preset</button><button type="button" id="pr-robust" class="alt">Robust preset</button></div></fieldset>
    <fieldset><legend>Step 7 · statistic</legend>${seg('intensity_statistic', c.intensity_statistic, p.intensity_statistic)}
      ${num('intensity_percentile', p.intensity_percentile)}
      <p class="small mute">Sampling (steps 2, 5, 6) uses the pipeline defaults: ${esc(info.defaults.sampling_method)} points,
        ${info.defaults.width}×${info.defaults.depth} px ${esc(info.defaults.rotation_method)} rectangles. All of them are
        on the <a href="${esc(info.sibling)}#/analyse" target="_blank" rel="noopener">full pipeline site</a>.</p></fieldset></div>`;
}

route('intensity', async (args) => {
  const info = await api('/info');
  S.params = S.params || { ...info.defaults };
  app().innerHTML = `<p class="kicker">Steps 1 and 7</p><h1>What does “100” mean?</h1>
    <p class="lead">The pipeline reports PIEZO1 intensity on a normalised scale. By default each frame is divided by its
      single brightest pixel and each rectangle reports its mean, so one hot pixel sets the ceiling and edge values sit
      low on the scale. This repo adds options for both choices and labels every plot with them. Change them here and
      compare with the defaults.</p>
    <div class="callout a small">${isStatic()
      ? 'Runs <b>in your browser</b>: a JavaScript port of the repo\'s step 1, 2, 5, 6 and 7 code, checked against the Python by a test. Nothing is uploaded.'
      : 'Runs in the browser (the same JavaScript port as the static site); this local app can also re-run a frame with the repo\'s Python ("Check with Python").'}</div>
    <div id="data"></div>
    <div class="panel"><h3 style="margin-top:0">Settings</h3><div id="ctl">${controls(info)}</div>
      <p>Axis label: <code id="label"></code></p></div>
    <div id="out"></div>`;
  const panel = dataPanel(document.getElementById('data'), info, {}, () => compute(info, true));
  bind(info);
  if (shared.stack) compute(info, S.version !== shared.version);
  else if (args[0] !== 'empty') panel.demo();
});

function bind(info) {
  const host = document.getElementById('ctl');
  const set = (k, v) => { S.params = { ...S.params, [k]: v }; refresh(info); };
  host.querySelectorAll('.seg button').forEach(b => { b.onclick = () => set(b.dataset.k, b.dataset.v); });
  host.querySelectorAll('input[type=number]').forEach(i => {
    i.onchange = () => { const v = +i.value; if (Number.isFinite(v) && v >= 0 && (!/percentile/.test(i.dataset.k) || v <= 100)) set(i.dataset.k, v); else i.value = S.params[i.dataset.k]; };
  });
  host.querySelectorAll('input[type=checkbox]').forEach(i => { i.onchange = () => set(i.dataset.k, i.checked); });
  document.getElementById('pr-default').onclick = () => { S.params = { ...S.params, ...info.presets.default }; refresh(info); };
  document.getElementById('pr-robust').onclick = () => { S.params = { ...S.params, ...info.presets.robust }; refresh(info); };
  document.getElementById('label').textContent = labelOf();
}

const labelOf = () => (S.cur ? S.cur.label : '');

function refresh(info) {
  document.getElementById('ctl').innerHTML = controls(info);
  bind(info);
  compute(info, false);
}

function compute(info, newStack) {
  if (!shared.stack) return;
  const st = shared.stack;
  if (newStack || S.version !== shared.version) {
    S.version = shared.version; S.frame = Math.min(S.frame, st.images.length - 1);
    S.def = runIntensity(st, info.defaults);
  }
  const same = STEP1.every(k => S.params[k] === info.defaults[k]);
  const pre = same ? S.def.pre : preprocessStack(st.images, st.masks, S.params);
  S.cur = runIntensity(st, S.params, null, pre);
  document.getElementById('label').textContent = S.cur.label;
  render(info);
}

const meanOf = f => { const v = f.rects.filter(r => r.accepted).map(r => r.intensity).filter(Number.isFinite); return v.length ? v.reduce((a, b) => a + b, 0) / v.length : NaN; };

function render(info) {
  const st = shared.stack, T = st.images.length, cur = S.cur, def = S.def;
  const series = (res, name, color, f, dash) => ({ name, color, dash, pts: res.frames.map(fr => [fr.frame, f(res, fr)]) });
  const refChart = cur.refs ? lineChart([
    series(def, 'pipeline default', '#9aa3b8', (r, fr) => r.refs[fr.frame], '5 4'),
    series(cur, 'these settings', 'var(--accent)', (r, fr) => r.refs[fr.frame])],
  { xl: 'frame', yl: 'reference (after background)', aria: 'Normalisation reference per frame', mark: S.frame })
    : '<p class="mute">Normalisation is off: intensities are raw (background-subtracted if chosen) counts.</p>';
  const meanChart = lineChart([
    series(def, 'pipeline default', '#9aa3b8', (r, fr) => meanOf(fr), '5 4'),
    series(cur, 'these settings', 'var(--accent)', (r, fr) => meanOf(fr))],
  { xl: 'frame', yl: 'mean over the edge', aria: 'Mean edge intensity per frame', mark: S.frame });
  document.getElementById('out').innerHTML = `<div class="panel"><h3 style="margin-top:0">Every frame</h3>
    <div class="two"><div><h4>The value the scale is anchored to</h4>${refChart}
      <p class="small mute">What each frame was divided by before ×${fmt(S.params.normalization_scale, 1)}. Hot pixels
        (demo frames 2 and 5) and debris (frame 6) raise a "max" reference; photobleaching lowers it.</p></div>
      <div><h4>Mean rectangle intensity along the edge</h4>${meanChart}
      <p class="small mute">Dashed: ${esc(def.label)}.<br>Solid: ${esc(cur.label)}.${shared.meta.demo ? `<br>In the demo,
        frames 2, 4 and 6 also read low whatever the setting: their DIC mask edge lies 34-66 px inside the cell, so the
        rectangles miss the bright rim (see <a href="#/edges">Fluorescence edge</a>).` : ''}</p></div></div></div>
    <div class="panel"><h3 style="margin-top:0">One frame</h3>
      <div class="ctl"><label for="fr">Frame <b id="fr-n">${S.frame}</b> of ${T - 1}</label>
        <input id="fr" type="range" min="0" max="${T - 1}" value="${S.frame}" ${T > 1 ? '' : 'disabled'}></div>
      <div class="viewer"><div class="stage"><canvas id="cv" role="img" aria-label="Frame with edge and sampling rectangles coloured by intensity"></canvas>
        <p class="small mute">Contrast 1st-99.5th percentile; rectangles coloured by the intensity with these settings.</p></div>
        <div id="prof"></div></div>
      <div><button id="b-csv" type="button">CSV: all frames, both settings</button>
        ${isStatic() ? '' : '<button id="b-py" class="alt" type="button">Check with Python</button>'}<span id="py" class="small" role="status"></span></div>
      ${isStatic() ? needsServer('"Check with Python" (re-running the frame with the repo\'s own step functions)') : ''}</div>`;
  const fr = document.getElementById('fr');
  fr.oninput = () => { S.frame = +fr.value; document.getElementById('fr-n').textContent = S.frame; frameView(); };
  document.getElementById('b-csv').onclick = () => download(`${(shared.meta.image || 'stack').replace(/\.tiff?$/i, '')}_intensity_options.csv`, csv(), 'text/csv');
  const py = document.getElementById('b-py');
  if (py) py.onclick = checkPython;
  frameView();
}

function frameView() {
  const st = shared.stack, f = S.frame, a = S.cur.frames[f], b = S.def.frames[f];
  drawFrame(document.getElementById('cv'), st, a, { mask: true, edge: true, rects: true, points: false, range: intensityRange([a]) });
  const pts = fr => fr.rects.filter(r => r.accepted).map(r => [r.edge_point[1], r.intensity]).sort((p, q) => p[0] - q[0]);
  document.getElementById('prof').innerHTML = `<h4 style="margin-top:0">Along the edge, frame ${f}</h4>` + lineChart([
    { name: 'pipeline default', color: '#9aa3b8', dash: '5 4', pts: pts(b) }, { name: 'these settings', color: 'var(--accent)', pts: pts(a) }],
  { xl: 'edge point x (px)', yl: 'rectangle intensity', aria: `Intensity along the edge in frame ${f}` });
}

function csv() {
  const m = shared.meta, lines = [`# cell_edge_analysis_individual_scripts web export (JS port of steps 1, 2, 5, 6, 7); image ${m.image}; mask ${m.mask}`,
    `# um_per_px ${m.um ?? 'not recorded in the file'} (${m.scaleSource}); coordinates in pixels`,
    `# default: ${S.def.label} | settings: ${S.cur.label}`, `# settings ${JSON.stringify(S.params)}`,
    'frame,point_index,x_px,y_px,accepted,reference_default,reference_settings,intensity_default,intensity_settings'];
  S.cur.frames.forEach((f, i) => f.rects.forEach((r, k) => {
    const d = S.def.frames[i].rects[k], v = x => (Number.isFinite(x) ? x : '');
    lines.push([f.frame, r.point_index, r.edge_point[1], r.edge_point[0], r.accepted, v(S.def.refs?.[i]), v(S.cur.refs?.[i]), v(d?.intensity), v(r.intensity)].join(','));
  }));
  return lines.join('\n') + '\n';
}

async function checkPython() {
  const out = document.getElementById('py'), btn = document.getElementById('b-py'), res = S.cur.frames[S.frame];
  btn.disabled = true; out.textContent = 'Running the Python steps...';
  try {
    const fd = new FormData();
    fd.append('image', shared.files.image, shared.files.image.name); fd.append('mask', shared.files.mask, shared.files.mask.name);
    fd.append('params', JSON.stringify(S.params)); fd.append('frames', String(S.frame));
    const py = await api('/analyse', { body: fd }), q = py.frames[0];
    let d = 0, mism = q.rects.length === res.rects.length ? 0 : Infinity;
    if (Number.isFinite(mism)) q.rects.forEach((r, i) => {
      const j = res.rects[i];
      if (r.accepted !== j.accepted) mism++;
      else if (r.accepted) d = Math.max(d, Math.abs(j.intensity - r.intensity) / Math.max(1e-12, Math.abs(r.intensity)));
    });
    const ok = mism === 0 && d < 1e-5 && py.label === S.cur.label;
    out.innerHTML = `<span class="${ok ? 'status-ok' : 'status-bad'}">Python: label "${esc(py.label)}"; ${q.rects.filter(r => r.accepted).length} accepted; max relative |Δ| intensity ${d.toExponential(1)}; ${mism} acceptance differences.</span>`;
  } catch (e) { out.innerHTML = `<span class="status-bad">${esc(e.message)}</span>`; }
  finally { btn.disabled = false; }
}
