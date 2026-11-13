// Loading an image + mask TIFF stack pair (or the synthetic demo) for the Intensity and Fluorescence-edge pages.
// Uncompressed TIFFs are read in the browser (tiff.js); the local app also reads compressed ones with tifffile.
// The loaded stack is shared by both pages (kept in `shared`), so it survives switching pages.
import { api, esc, isStatic, needsServer } from './core.js';
import { readTiff, fromServer, TiffError } from './tiff.js';

export const shared = { stack: null, meta: null, files: null, labels: null, version: 0 };

async function loadTiff(file) {
  const buf = await file.arrayBuffer();
  try { return readTiff(buf); } catch (e) {
    if (!(e instanceof TiffError) || isStatic()) throw new Error(`${file.name}: ${e.message}`);
    const fd = new FormData(); fd.append('file', file, file.name);
    return fromServer(await api('/tiff', { body: fd }));
  }
}

async function fetchFile(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} ${url}`);
  return new File([await r.blob()], url.split('/').pop());
}

// labels.json as written by fluorescence_edge_experiments/labeling (label_io): {frames: {"<i>": {y: [...]}}}
export function parseLabels(text, w) {
  const d = JSON.parse(text), out = {};
  for (const [k, v] of Object.entries(d.frames || {})) {
    if (Array.isArray(v.y) && v.y.length === w) out[+k] = v.y.map(t => (t == null ? NaN : +t));
  }
  if (!Object.keys(out).length) throw new Error(`no per-frame "y" arrays of length ${w} (the image width) in the labels file`);
  return out;
}

export async function setStack(imageFile, maskFile, demo, labelsText = null) {
  const [im, mk] = await Promise.all([loadTiff(imageFile), loadTiff(maskFile)]);
  if (im.w !== mk.w || im.h !== mk.h) throw new Error(`Image frames are ${im.w}×${im.h} px but mask frames are ${mk.w}×${mk.h} px.`);
  if (im.frames.length !== mk.frames.length) throw new Error(`The image stack has ${im.frames.length} frames but the mask stack has ${mk.frames.length}.`);
  shared.stack = { images: im.frames, masks: mk.frames.map(f => Uint8Array.from(f, v => (v > 0 ? 1 : 0))), h: im.h, w: im.w };
  shared.meta = { image: imageFile.name, mask: maskFile.name, um: im.um_per_px, scaleSource: im.scale_source, demo };
  shared.files = { image: imageFile, mask: maskFile };
  shared.labels = labelsText ? parseLabels(labelsText, im.w) : null;
  shared.version++;
}

export async function loadDemo(info) {
  const [a, b, l] = await Promise.all([fetchFile(info.demo.image), fetchFile(info.demo.mask), fetchFile(info.demo.labels)]);
  await setStack(a, b, true, await l.text());
}

export function sourceNote(info) {
  if (!shared.meta) return '<span class="mute">No stack loaded yet.</span>';
  const { stack: st, meta: m } = shared;
  const scale = m.um ? `${(+m.um).toFixed(4)} µm/px (${esc(m.scaleSource)})` : 'pixel size not recorded in the file (results are in pixels)';
  const lab = shared.labels ? `; labels for ${Object.keys(shared.labels).length} frame(s)` : '';
  return `${m.demo ? `<span class="sim-badge">SYNTHETIC</span> ${esc(info.demo.note.replace(/^SYNTHETIC /, 'Synthetic '))}<br>` : ''}
    <b>${esc(m.image)}</b> + <b>${esc(m.mask)}</b>: ${st.images.length} frame${st.images.length > 1 ? 's' : ''} of ${st.w}×${st.h} px; ${scale}${lab}.`;
}

// The data panel: file inputs (+ optional labels), Load / Demo buttons; onLoaded() after a successful load.
export function dataPanel(host, info, { labels = false } = {}, onLoaded) {
  host.innerHTML = `<div class="panel"><h3 style="margin-top:0">Data</h3>
    <div class="row">
      <div><label for="f-img">PIEZO1 stack (TIFF, e.g. name${esc(info.file_patterns.image[0])})</label><input id="f-img" type="file" accept=".tif,.tiff"></div>
      <div><label for="f-msk">Cell mask stack (TIFF, e.g. name${esc(info.file_patterns.mask[0])}; nonzero = cell)</label><input id="f-msk" type="file" accept=".tif,.tiff"></div>
      ${labels ? '<div><label for="f-lab">Optional: edge labels (labels.json from the labelling app)</label><input id="f-lab" type="file" accept=".json"></div>' : ''}
    </div>
    <button id="b-load" type="button">Load stacks</button><button id="b-demo" class="alt" type="button">Use the synthetic demo</button>
    <p id="src" class="small" role="status">${sourceNote(info)}</p></div>`;
  const $ = id => host.querySelector('#' + id);
  const status = (html, bad) => { $('src').innerHTML = bad ? `<span class="status-bad">${html}</span>` : html; };
  const run = async (fn) => {
    $('b-load').disabled = $('b-demo').disabled = true;
    status('Reading...');
    try { await fn(); status(sourceNote(info)); onLoaded(); }
    catch (e) { status(esc(e.message) + (isStatic() && /compressed|BigTIFF/.test(e.message) ? ' ' + needsServer('Opening compressed TIFFs') : ''), true); }
    finally { $('b-load').disabled = $('b-demo').disabled = false; }
  };
  $('b-load').onclick = () => {
    const a = $('f-img').files[0], b = $('f-msk').files[0], l = labels ? $('f-lab').files[0] : null;
    if (!a || !b) return status('Choose both an image stack and a mask stack.', true);
    run(async () => setStack(a, b, false, l ? await l.text() : null));
  };
  $('b-demo').onclick = () => run(() => loadDemo(info));
  return { demo: () => $('b-demo').click() };
}
