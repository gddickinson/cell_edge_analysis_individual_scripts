// JS port of the tuned fluorescence edge detector (fluorescence_edge_experiments/detector.py fluor_edge) and the DIC
// baseline (edge_methods.edge_dic), with the library calls they make: scipy.ndimage gaussian_filter (reflect),
// skimage threshold_otsu (256-bin histogram), binary_closing with skimage disk, binary_fill_holes, label (largest
// component), median_filter and gaussian_filter1d (nearest), numpy interp. No DOM. Edges are per-column y(x) arrays
// (NaN where undefined), 'uppermost' geometry. Tested against Python by fluor_engine.test.mjs.
import { gaussianKernel, gaussianFilter1d, extend } from './contours.js';

const f32 = Math.fround;

// edge_methods.top_edge_from_binary(binary, 'uppermost')
export function topEdge(bin, h, w) {
  const y = new Float64Array(w).fill(NaN);
  for (let x = 0; x < w; x++) for (let r = 0; r < h; r++) if (bin[r * w + x]) { y[x] = r; break; }
  return y;
}
export const edgeDic = (mask, h, w) => topEdge(mask, h, w);

// scipy.ndimage.gaussian_filter(image, sigma) in float64, mode 'reflect', truncate 4: axis 0 then axis 1.
export function gaussian2d(img, h, w, sigma) {
  const r = Math.trunc(4.0 * sigma + 0.5), k = gaussianKernel(sigma, r);
  const tmp = new Float64Array(h * w), out = new Float64Array(h * w);
  for (let x = 0; x < w; x++) {
    for (let y = 0; y < h; y++) {
      let s = img[y * w + x] * k[r];
      for (let d = r; d >= 1; d--) s += (img[extend(y - d, h, 'reflect') * w + x] + img[extend(y + d, h, 'reflect') * w + x]) * k[r - d];
      tmp[y * w + x] = s;
    }
  }
  for (let y = 0; y < h; y++) {
    const o = y * w;
    for (let x = 0; x < w; x++) {
      let s = tmp[o + x] * k[r];
      for (let d = r; d >= 1; d--) s += (tmp[o + extend(x - d, w, 'reflect')] + tmp[o + extend(x + d, w, 'reflect')]) * k[r - d];
      out[o + x] = s;
    }
  }
  return out;
}

// edge_methods._safe_otsu -> skimage.filters.threshold_otsu(finite values); null without contrast.
export function otsu(values) {
  let lo = Infinity, hi = -Infinity, n = 0;
  for (const v of values) if (Number.isFinite(v)) { n++; if (v < lo) lo = v; if (v > hi) hi = v; }
  if (!n || lo === hi) return null;
  const nb = 256, step = (hi - lo) / nb, edges = new Float64Array(nb + 1);
  for (let i = 0; i <= nb; i++) edges[i] = i * step + lo;  // numpy linspace
  edges[nb] = hi;
  const counts = new Float64Array(nb);
  for (const v of values) {
    if (!Number.isFinite(v)) continue;
    let i = Math.trunc(((v - lo) / (hi - lo)) * nb);
    if (i === nb) i--;
    if (v < edges[i]) i--;
    if (v >= edges[i + 1] && i !== nb - 1) i++;
    counts[i]++;
  }
  const c = Array.from({ length: nb }, (_, i) => (edges[i] + edges[i + 1]) / 2);
  const w1 = new Float64Array(nb), w2 = new Float64Array(nb), m1 = new Float64Array(nb), m2 = new Float64Array(nb);
  let a = 0, s = 0;
  for (let i = 0; i < nb; i++) { a = f32(a + counts[i]); s += counts[i] * c[i]; w1[i] = a; m1[i] = s / a; }
  a = 0; s = 0;
  for (let i = nb - 1; i >= 0; i--) { a = f32(a + counts[i]); s += counts[i] * c[i]; w2[i] = a; m2[i] = s / a; }
  let best = -Infinity, idx = 0;
  for (let i = 0; i < nb - 1; i++) {
    const v = f32(w1[i] * w2[i + 1]) * (m1[i] - m2[i + 1]) ** 2;  // float32 weights product, as numpy
    if (v > best) { best = v; idx = i; }
  }
  return c[idx];
}

// skimage.morphology.disk(r) offsets [dy, dx]
function disk(r) {
  const o = [];
  for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) if (dy * dy + dx * dx <= r * r) o.push([dy, dx]);
  return o;
}

// scipy binary_closing(bin, disk(r)): dilation then erosion, border_value 0 (outside the image counts as background).
export function binaryClosing(bin, h, w, r) {
  const off = disk(r), dil = new Uint8Array(h * w), out = new Uint8Array(h * w);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    for (const [dy, dx] of off) {
      const yy = y + dy, xx = x + dx;
      if (yy >= 0 && yy < h && xx >= 0 && xx < w && bin[yy * w + xx]) { dil[y * w + x] = 1; break; }
    }
  }
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    let all = 1;
    for (const [dy, dx] of off) {
      const yy = y + dy, xx = x + dx;
      if (yy < 0 || yy >= h || xx < 0 || xx >= w || !dil[yy * w + xx]) { all = 0; break; }
    }
    out[y * w + x] = all;
  }
  return out;
}

// 4-connected flood of `sel` pixels from the given seeds; returns the visited mask.
function flood(sel, h, w, seeds) {
  const seen = new Uint8Array(h * w), st = [];
  for (const s of seeds) if (sel[s] && !seen[s]) { seen[s] = 1; st.push(s); }
  while (st.length) {
    const p = st.pop(), y = Math.floor(p / w), x = p - y * w;
    for (const q of [y > 0 ? p - w : -1, y < h - 1 ? p + w : -1, x > 0 ? p - 1 : -1, x < w - 1 ? p + 1 : -1]) {
      if (q >= 0 && sel[q] && !seen[q]) { seen[q] = 1; st.push(q); }
    }
  }
  return seen;
}

// scipy binary_fill_holes: background not 4-connected to the image border becomes foreground.
export function fillHoles(bin, h, w) {
  const bg = bin.map(v => (v ? 0 : 1)), border = [];
  for (let x = 0; x < w; x++) border.push(x, (h - 1) * w + x);
  for (let y = 0; y < h; y++) border.push(y * w, y * w + w - 1);
  const outside = flood(bg, h, w, border);
  return bin.map((_, i) => (outside[i] ? 0 : 1));
}

// edge_methods.largest_component: ndimage.label (4-connected, numbered in raster order), first largest kept.
export function largestComponent(bin, h, w) {
  const lab = new Int32Array(h * w), sizes = [0];
  let n = 0;
  for (let p = 0; p < h * w; p++) {
    if (!bin[p] || lab[p]) continue;
    n++;
    let size = 0;
    const st = [p];
    lab[p] = n;
    while (st.length) {
      const q = st.pop(), y = Math.floor(q / w), x = q - y * w;
      size++;
      for (const r of [y > 0 ? q - w : -1, y < h - 1 ? q + w : -1, x > 0 ? q - 1 : -1, x < w - 1 ? q + 1 : -1]) {
        if (r >= 0 && bin[r] && !lab[r]) { lab[r] = n; st.push(r); }
      }
    }
    sizes.push(size);
  }
  if (n <= 1) return Uint8Array.from(bin, v => (v ? 1 : 0));
  let best = 1;
  for (let k = 2; k <= n; k++) if (sizes[k] > sizes[best]) best = k;
  return Uint8Array.from(lab, v => (v === best ? 1 : 0));
}

// numpy.interp for interior gaps of y over its defined span [a, b] (in place on a copy of the segment).
function fillGaps(seg) {
  const xs = [], ys = [];
  seg.forEach((v, i) => { if (Number.isFinite(v)) { xs.push(i); ys.push(v); } });
  let j = 0;
  return seg.map((v, i) => {
    if (Number.isFinite(v)) return v;
    while (xs[j + 1] < i) j++;
    const slope = (ys[j + 1] - ys[j]) / (xs[j + 1] - xs[j]);
    return slope * (i - xs[j]) + ys[j];
  });
}

function span(y) {
  let a = -1, b = -1;
  y.forEach((v, i) => { if (Number.isFinite(v)) { if (a < 0) a = i; b = i; } });
  return [a, b];
}

// detector._despike: median_filter(size, mode='nearest') of the defined span with gaps interpolated.
export function despike(y, size) {
  const valid = y.filter(Number.isFinite).length;
  if (valid < Math.max(size, 5)) return y;
  const [a, b] = span(y), seg = fillGaps(Array.from(y.slice(a, b + 1))), n = seg.length;
  const lo = -Math.floor(size / 2), out = Float64Array.from(y);
  for (let i = 0; i < n; i++) {
    const win = [];
    for (let d = lo; d < lo + size; d++) win.push(seg[extend(i + d, n, 'nearest')]);
    win.sort((p, q) => p - q);
    out[a + i] = win[size >> 1];
  }
  return out;
}

// edge_methods.smooth_curve: gaussian_filter1d(mode='nearest') of the defined span with gaps interpolated.
export function smoothCurve(y, sigma) {
  if (y.filter(Number.isFinite).length < 3) return y;
  const [a, b] = span(y), seg = gaussianFilter1d(fillGaps(Array.from(y.slice(a, b + 1))), sigma, 'nearest');
  const out = new Float64Array(y.length).fill(NaN);
  seg.forEach((v, i) => { out[a + i] = v; });
  return out;
}

// detector.top_edge_banded: uppermost foreground row within +/- band rows of the DIC edge (NaN DIC -> NaN).
export function topEdgeBanded(bin, h, w, dic, band) {
  const y = new Float64Array(w).fill(NaN);
  for (let x = 0; x < w; x++) {
    if (!Number.isFinite(dic[x])) continue;
    for (let r = 0; r < h; r++) if (bin[r * w + x] && r >= dic[x] - band && r <= dic[x] + band) { y[x] = r; break; }
  }
  return y;
}

// detector.fluor_edge(image, mask, **p) for one frame. image: float array (step-1 output), mask: 0/1.
export function fluorEdge(img, mask, h, w, p) {
  const dic = edgeDic(mask, h, w), b = gaussian2d(img, h, w, p.blur), t = otsu(b);
  if (t === null) return Float64Array.from(dic);
  let bin = Uint8Array.from(b, v => (v > t * p.thr_scale ? 1 : 0));
  if (p.close > 0) bin = binaryClosing(bin, h, w, p.close);
  bin = largestComponent(fillHoles(bin, h, w), h, w);
  let y = topEdgeBanded(bin, h, w, dic, p.band);
  y = y.map((v, i) => (Number.isFinite(v) ? v : dic[i]));
  y = smoothCurve(despike(y, p.median_size), p.curve_sigma);
  if (p.restrict_to_dic) y = y.map((v, i) => (Number.isFinite(dic[i]) ? v : NaN));
  return y;
}

// tune_blob.frame_error: median |pred - truth| over columns where both are defined (null with < 5), and coverage.
export function frameError(pred, truth) {
  const d = [];
  pred.forEach((v, i) => { const t = truth[i]; if (Number.isFinite(v) && t != null && Number.isFinite(t)) d.push(Math.abs(v - t)); });
  return d.length < 5 ? null : { median: median(d), scored: d.length / pred.length };
}

// run_experiments.gap_between: median |a - b| over columns where both are defined (null if none).
export function gapBetween(a, b) {
  const d = [];
  a.forEach((v, i) => { if (Number.isFinite(v) && Number.isFinite(b[i])) d.push(Math.abs(v - b[i])); });
  return d.length ? median(d) : null;
}

export function median(v) {
  const s = [...v].sort((p, q) => p - q), n = s.length;
  return n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2;
}
