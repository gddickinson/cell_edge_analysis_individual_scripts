// JS port of what this repo adds to the intensity measurement (no DOM): step 1 background subtraction and the
// configurable normalisation (step1_data_loading.subtract_background / _compute_reference / normalize_frames:
// method max|percentile, region frame|mask, scope per_frame|global, scale), the step 7 per-rectangle statistic
// (step7_intensity_extraction.extract_intensity_from_rectangle: mean|max|percentile) and the axis label
// (intensity_labels.build_intensity_label). float32 arithmetic where numpy uses it. Tested against Python by
// intensity_engine.test.mjs.
import { runPipeline } from './edge_engine.js';

const f32 = Math.fround;

// numpy.percentile (linear) of float32 values, with numpy's float32 _lerp.
export function percentile32(values, p) {
  const s = Float32Array.from(values).sort(), n = s.length;
  const v = (n - 1) * (p / 100), i = Math.floor(v), g = f32(v - i);
  const a = s[i], b = s[Math.min(i + 1, n - 1)], d = f32(b - a);
  return g >= 0.5 ? f32(b - f32(d * f32(1 - g))) : f32(a + f32(d * g));
}

// step1 subtract_background for one frame: minus the frame's background_percentile, clipped at 0.
export function subtractBackground(raw, pct) {
  const img = Float32Array.from(raw), bg = percentile32(img, pct);
  for (let i = 0; i < img.length; i++) img[i] = Math.max(f32(img[i] - bg), 0);
  return img;
}

// step1 _compute_reference: brightest value, or the given percentile (0 for no values).
export function computeReference(values, method, pct) {
  if (!values.length) return 0;
  if (method === 'percentile') return percentile32(values, pct);
  let mx = -Infinity;
  for (const v of values) if (v > mx) mx = v;
  return mx;
}

function inMask(img, mask) {
  const out = [];
  for (let k = 0; k < img.length; k++) if (mask[k] > 0) out.push(img[k]);
  return out;
}

// The reference each frame is divided by (normalize_frames), from the background-subtracted frames.
// Same fallbacks as Python: an empty mask (or all masks empty for 'global') uses the whole frame (stack).
export function references(frames, masks, p) {
  const useMask = p.normalization_region === 'mask', m = p.normalization_method, q = p.normalization_percentile;
  if (p.normalization_scope === 'global') {
    let vals = [];
    if (useMask) for (let i = 0; i < frames.length; i++) vals = vals.concat(inMask(frames[i], masks[i]));
    if (!vals.length) { vals = new Float32Array(frames.reduce((s, f) => s + f.length, 0)); let o = 0; for (const f of frames) { vals.set(f, o); o += f.length; } }
    const r = computeReference(vals, m, q);
    return frames.map(() => r);
  }
  return frames.map((f, i) => {
    const v = useMask ? inMask(f, masks[i]) : [];
    return computeReference(v.length ? v : f, m, q);
  });
}

// Step 1 on a stack: { frames: [Float32Array], refs: [number] | null } (refs as the frames were divided by).
export function preprocessStack(images, masks, p) {
  let frames = images.map(f => (p.subtract_background ? subtractBackground(f, p.background_percentile) : Float32Array.from(f)));
  if (!p.normalize_frames) return { frames, refs: null };
  const refs = references(frames, masks, p), scale = f32(p.normalization_scale);
  frames = frames.map((f, i) => {
    const r = f32(refs[i]), out = Float32Array.from(f);
    if (refs[i] > 0) for (let k = 0; k < out.length; k++) out[k] = f32(out[k] / r);
    if (p.normalization_scale !== 1.0) for (let k = 0; k < out.length; k++) out[k] = f32(out[k] * scale);
    return out;
  });
  return { frames, refs };
}

// step7 extract_intensity_from_rectangle on pixels (flat indices) of a preprocessed frame.
export function rectangleStatistic(img, pixels, statistic, pct) {
  if (!pixels.length) return NaN;
  if (statistic === 'max') { let mx = -Infinity; for (const k of pixels) if (img[k] > mx) mx = img[k]; return mx; }
  if (statistic === 'percentile') return percentile32(pixels.map(k => img[k]), pct);
  let s = 0;
  for (const k of pixels) s += img[k];
  return s / pixels.length;
}

// ---- intensity_labels ------------------------------------------------------------------------------------------
const ordinal = p => `${Number(p) === Math.trunc(Number(p)) ? Math.trunc(Number(p)) : +Number(p).toPrecision(6)}th`;

export function describeNormalization(meta) {
  if (!meta || !meta.normalized) return 'raw';
  const scope = meta.normalization_scope === 'global' || meta.normalization_scope === 'stack' ? 'stack' : 'per-frame';
  const ref = meta.normalization_method === 'percentile' ? `${ordinal(meta.normalization_percentile ?? 99.9)} pct` : 'max';
  const phrase = [scope, ...(meta.normalization_region === 'mask' ? ['in-mask'] : []), ref].join(' ');
  const scale = Number(meta.normalization_scale ?? 1);
  if (Math.abs(scale - 100) < 1e-9) return `% of ${phrase}`;
  if (Math.abs(scale - 1) < 1e-9) return `fraction of ${phrase}`;
  return `×${+scale.toPrecision(6)} of ${phrase}`;
}

export function describeStatistic(statistic, pct = 95) {
  return statistic === 'max' ? 'max' : statistic === 'percentile' ? `${ordinal(pct)} pct` : 'mean';
}

// build_intensity_label for the web parameters (step 1 options + step 7 statistic).
export function intensityLabel(p, base = 'PIEZO1 intensity') {
  const meta = { normalized: p.normalize_frames, normalization_method: p.normalization_method,
    normalization_percentile: p.normalization_percentile, normalization_region: p.normalization_region,
    normalization_scope: p.normalization_scope, normalization_scale: p.normalization_scale };
  return `${base} (${describeStatistic(p.intensity_statistic, p.intensity_percentile)}, ${describeNormalization(meta)})`;
}

// Steps 1, 2, 5, 6, 7 as web/analysis.run: stack = { images: [Float32Array], masks: [Uint8Array 0/1], h, w }.
// pre (optional) is a preprocessStack result to reuse when only step 2-7 parameters change.
export function runIntensity(stack, p, which = null, pre = null) {
  pre = pre || preprocessStack(stack.images, stack.masks, p);
  const frames = runPipeline(stack, p, which,
    (i, pixels) => rectangleStatistic(pre.frames[i], pixels, p.intensity_statistic, p.intensity_percentile));
  return { frames, refs: pre.refs, label: intensityLabel(p), pre };
}
