// The seven candidate edge detectors of fluorescence_edge_experiments/edge_methods.py (+ the tuned detector) on one
// synthetic demo frame, computed by Python (GET /api/methods; exported as JSON for the static site), drawn over the
// frame like the experiments' "*_methods.png" panels, with each method's coverage, gap to the DIC edge and error.
import { api, esc } from './core.js';
import { readTiff } from './tiff.js';
import { drawFrame, drawCurves, fmt } from './plots.js';

const KIND = { dic: 'DIC only', fluor: 'fluorescence only', both: 'DIC + fluorescence' };

export async function methodsPanel(host, info) {
  host.innerHTML = '<div class="panel"><p class="mute">Loading the method comparison...</p></div>';
  try {
    const [d, buf] = await Promise.all([api('/methods'), fetch(info.demo.image).then(r => r.arrayBuffer())]);
    const im = readTiff(buf), stack = { images: im.frames, masks: im.frames.map(f => new Uint8Array(f.length)), h: im.h, w: im.w };
    const on = new Set(d.methods.map(m => m.name));
    host.innerHTML = `<div class="panel"><h3 style="margin-top:0">All candidate methods <span class="small mute">(Python, synthetic demo frame ${d.frame})</span></h3>
      <p class="small">The experiments tried seven detectors (<code>edge_methods.METHODS</code>) before tuning one. Computed
        by the repo's Python when the site was built; the newer tuned detector is shown in white.</p>
      <div class="toggles">${d.methods.map(m => `<label for="m-${m.name}"><input id="m-${m.name}" type="checkbox" checked>
        <i class="sw" style="background:${esc(m.color)}"></i>${esc(m.label)}</label>`).join('')}</div>
      <div class="stage"><canvas id="mcv" role="img" aria-label="Demo frame ${d.frame} with every candidate edge"></canvas></div>
      <div class="scroll"><table><thead><tr><th>method</th><th>uses</th><th>coverage</th><th>gap to DIC (px)</th><th>error vs labels (px)</th></tr></thead>
        <tbody>${d.methods.map(m => `<tr><td><i class="sw" style="background:${esc(m.color)}"></i>${esc(m.label)}</td><td>${KIND[m.kind] || esc(m.kind)}</td>
          <td class="num">${fmt(m.coverage, 2)}</td><td class="num">${fmt(m.gap_to_dic, 1)}</td><td class="num">${fmt(m.error?.median, 1)}</td></tr>`).join('')}</tbody></table></div>
      <p class="small mute">Coverage: fraction of columns with an edge. On the real recording the per-column and ridge
        tracers followed noise in the grainy PIEZO1 signal and the Otsu region fragmented (experiments README); the
        synthetic frame is much cleaner, so they look better here than they did there.</p></div>`;
    const draw = () => {
      const cv = host.querySelector('#mcv');
      drawFrame(cv, stack, { frame: d.frame, edge: [], rects: [], sampled: [] }, { mask: false, range: [0, 1] });
      drawCurves(cv, d.methods.filter(m => on.has(m.name)).map(m => ({ y: m.edge.map(v => (v == null ? NaN : v)), color: m.color, width: m.name === 'detector' ? 3 : 1.8 })), im.w, im.h);
    };
    for (const m of d.methods) host.querySelector(`#m-${m.name}`).onchange = e => { e.target.checked ? on.add(m.name) : on.delete(m.name); draw(); };
    draw();
  } catch (e) {
    host.innerHTML = `<div class="panel"><p class="err">Method comparison unavailable: ${esc(e.message)}</p></div>`;
  }
}
