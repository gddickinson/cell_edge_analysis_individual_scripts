// JS port of pipeline steps 2, 5 and 6 (no DOM), mirroring the repo's Python function by function so the browser gives
// the same edge, sampling points and rectangles. Shared with the sibling repo cell_edge_analysis (same step code);
// step 1 normalisation and the step 7 statistic, which this repo extends, are in intensity_engine.js. Tested against
// Python by intensity_engine.test.mjs (fixture from scripts/make_web_fixture.py).
// Units are pixels throughout, as in the pipeline. Points are [row, col] = [y, x].
import { findContours, gaussianFilter1d } from './contours.js';


// ---- step 2: step2_edge_detection.detect_cell_edge / smooth_edge -----------------------------------------------
export function detectCellEdge(mask, h, w) {
  const cs = findContours(mask, h, w, 0.5);
  let best = [];
  for (const c of cs) if (c.length > best.length) best = c;  // max(..., key=len): the first longest
  return best.map(p => [p[0], p[1]]);
}

export function smoothEdge(edge, sigma) {
  const n = edge.length;
  if (n === 0) return edge;
  const closed = Math.hypot(edge[0][0] - edge[n - 1][0], edge[0][1] - edge[n - 1][1]) < 5;
  const mode = closed ? 'wrap' : 'reflect';
  const r = gaussianFilter1d(edge.map(p => p[0]), sigma, mode), c = gaussianFilter1d(edge.map(p => p[1]), sigma, mode);
  const out = r.map((v, i) => [v, c[i]]);
  if (!closed) { out[0] = [...edge[0]]; out[n - 1] = [...edge[n - 1]]; }
  return out;
}

export function edgeForFrame(mask, h, w, p) {
  const e = detectCellEdge(mask, h, w);
  return p.smooth_edges && e.length > 0 ? smoothEdge(e, p.smoothing_sigma) : e;
}

// ---- step 5: step5_edge_sampling --------------------------------------------------------------------------------
function linspace(a, b, n) {
  if (n === 1) return [a];
  const step = (b - a) / (n - 1), out = [];
  for (let i = 0; i < n; i++) out.push(i * step + a);
  out[n - 1] = b;
  return out;
}

function selectY(cands, ysel) {
  let k = 0;
  for (let i = 1; i < cands.length; i++) {
    if (ysel === 'uppermost' ? cands[i][0] < cands[k][0] : cands[i][0] > cands[k][0]) k = i;
  }
  return cands[k];
}

const xRange = e => { let lo = Infinity, hi = -Infinity; for (const p of e) { if (p[1] < lo) lo = p[1]; if (p[1] > hi) hi = p[1]; } return [lo, hi]; };
const near = (e, x, tol) => e.filter(p => Math.abs(p[1] - x) < tol);

function samplePerFrame(e, p) {
  if (!e.length) return [];
  const [lo, hi] = xRange(e), n = p.n_points;
  const margin = (hi - lo) * 0.05;
  const xs = p.exclude_endpoints ? linspace(lo + margin, hi - margin, n) : linspace(lo, hi, n);
  const out = [];
  for (const x of xs) { const c = near(e, x, (hi - lo) / (n * 2)); if (c.length) out.push([...selectY(c, p.y_selection)]); }
  return out;
}

export function commonXRange(edges, exclude) {
  const r = edges.filter(e => e.length).map(xRange);
  if (!r.length) return [0, 0];
  let lo = Math.max(...r.map(v => v[0])), hi = Math.min(...r.map(v => v[1]));
  if (exclude) { const m = (hi - lo) * 0.05; lo += m; hi -= m; }
  return [lo, hi];
}

function sampleFixedX(e, xs, p) {
  if (!e.length) return [];
  const [lo, hi] = xRange(e), range = hi - lo;
  const width = xs.length > 1 ? range / (xs.length * 2) : range / 10;
  return xs.map(x => { const c = near(e, x, width); return c.length ? [...selectY(c, p.y_selection)] : [NaN, x]; });
}

const roundHalfEven = v => { const f = Math.floor(v), d = v - f; return d > 0.5 || (d === 0.5 && f % 2 !== 0) ? f + 1 : f; };

function sampleDense(e, p) {
  if (!e.length) return [];
  let xs = [...new Set(e.map(q => roundHalfEven(q[1] * 1e6) / 1e6))].sort((a, b) => a - b);
  if (p.exclude_endpoints && xs.length > 2) xs = xs.slice(1, -1);
  const out = [];
  for (const x of xs) { const c = near(e, x, 0.5); if (c.length) out.push([...selectY(c, p.y_selection)]); }
  return out;
}

function sampleDisplacementLike(e, p) {
  if (!e.length) return [];
  const [lo0, hi0] = xRange(e);
  let lo = Math.floor(lo0), hi = Math.ceil(hi0);
  if (p.exclude_endpoints) { lo += 1; hi -= 1; }
  const all = [];
  for (let x = lo; x <= hi; x++) all.push(x);
  let xs = all;
  if (p.target_points_displacement != null && all.length > p.target_points_displacement) {
    const step = Math.max(1, Math.floor(all.length / p.target_points_displacement));
    xs = all.filter((_, i) => i % step === 0);
  }
  const out = [];
  for (const x of xs) { const c = near(e, x, 0.5); if (c.length) out.push([...selectY(c, p.y_selection)]); }
  return out;
}

// step5 sample_all_edges for the frames in `which` (fixed_x needs every frame's edge for the common range).
export function sampleEdges(edges, p, which) {
  const out = new Map();
  if (p.sampling_method === 'fixed_x') {
    const [lo, hi] = commonXRange(edges, p.exclude_endpoints), xs = linspace(lo, hi, p.n_points);
    for (const i of which) out.set(i, sampleFixedX(edges[i], xs, p));
  } else {
    const fn = { dense: sampleDense, displacement_like: sampleDisplacementLike }[p.sampling_method] || samplePerFrame;
    for (const i of which) out.set(i, fn(edges[i], p));
  }
  return out;
}

// ---- step 6: step6_sampling_rectangles ----------------------------------------------------------------------------
export const COVERAGE_TIE_TOL = 1e-9;  // as step6_sampling_rectangles.COVERAGE_TIE_TOL

export function edgeNormal(contour, idx) {
  const n = contour.length;
  if (n < 3) return [0, -1];
  const a = contour[Math.max(0, idx - 2)], b = contour[Math.min(n - 1, idx + 2)];
  let t = [b[0] - a[0], b[1] - a[1]];
  const len = Math.sqrt(t[0] * t[0] + t[1] * t[1]) + 1e-10;
  t = [t[0] / len, t[1] / len];
  let normal = [-t[1], t[0]];
  let s0 = 0, s1 = 0;
  for (const p of contour) { s0 += p[0]; s1 += p[1]; }
  const toC = [s0 / n - contour[idx][0], s1 / n - contour[idx][1]];
  if (normal[0] * toC[0] + normal[1] * toC[1] < 0) normal = [-normal[0], -normal[1]];
  return normal;
}

export function rectangleCorners(pt, normal, width, depth) {
  const hw = width / 2, perp = [normal[1], -normal[0]];
  const a = [pt[0] - perp[0] * hw, pt[1] - perp[1] * hw], b = [pt[0] + perp[0] * hw, pt[1] + perp[1] * hw];
  return [a, [a[0] + normal[0] * depth, a[1] + normal[1] * depth], [b[0] + normal[0] * depth, b[1] + normal[1] * depth], b];
}

function rotate(v, deg) {
  const r = deg * (Math.PI / 180), c = Math.cos(r), s = Math.sin(r);
  return [c * v[0] + -s * v[1], s * v[0] + c * v[1]];
}

const sign = (p1, p2, p3) => (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1]);

// step6 check_cell_coverage: (pixels in cell) / (rectangle area); pixels as flat indices y * w + x.
export function cellCoverage(k, mask, h, w) {
  const v1 = [k[1][0] - k[0][0], k[1][1] - k[0][1]], v2 = [k[3][0] - k[0][0], k[3][1] - k[0][1]];
  const area = Math.abs(v1[0] * v2[1] - v1[1] * v2[0]);
  if (area === 0) return { coverage: 0, pixels: [] };
  const ys = k.map(c => c[0]), xs = k.map(c => c[1]);
  const y0 = Math.max(0, Math.floor(Math.min(...ys))), y1 = Math.min(h, Math.ceil(Math.max(...ys)));
  const x0 = Math.max(0, Math.floor(Math.min(...xs))), x1 = Math.min(w, Math.ceil(Math.max(...xs)));
  if (y1 <= y0 || x1 <= x0) return { coverage: 0, pixels: [] };
  const pixels = [];
  let inCell = 0;
  for (let y = y0; y < y1; y++) {
    for (let x = x0; x < x1; x++) {
      const q = [y, x], d = [sign(q, k[0], k[1]), sign(q, k[1], k[2]), sign(q, k[2], k[3]), sign(q, k[3], k[0])];
      const neg = d.some(v => v < 0), pos = d.some(v => v > 0);
      if (neg && pos) continue;
      pixels.push(y * w + x);
      if (mask[y * w + x] > 0) inCell++;
    }
  }
  return { coverage: pixels.length ? inCell / area : 0, pixels };
}

// step6 create_rectangles_for_frame for one frame's sampled points.
export function rectanglesForFrame(points, edge, mask, h, w, p) {
  return points.map((pt, i) => {
    if (Number.isNaN(pt[0]) || Number.isNaN(pt[1])) {
      return { point_index: i, edge_point: pt, normal: [NaN, NaN], corners: null, coverage: 0, pixels: [],
        accepted: false, rotation_tried: false, rotation_angle: 0 };
    }
    let normal;
    if (p.rotation_method === 'vertical') normal = [1, 0];
    else {
      let best = 0, bd = Infinity;
      edge.forEach((e, j) => { const d = (e[0] - pt[0]) ** 2 + (e[1] - pt[1]) ** 2; if (d < bd) { bd = d; best = j; } });
      normal = edgeNormal(edge, best);
    }
    let corners = rectangleCorners(pt, normal, p.width, p.depth);
    let { coverage, pixels } = cellCoverage(corners, mask, h, w);
    let accepted = coverage >= p.min_cell_coverage, tried = false, angle = 0;
    if (!accepted && p.rotation_method === 'flip') {
      const k2 = rectangleCorners(pt, [-normal[0], -normal[1]], p.width, p.depth), c2 = cellCoverage(k2, mask, h, w);
      if (c2.coverage >= p.min_cell_coverage) {
        corners = k2; coverage = c2.coverage; pixels = c2.pixels; accepted = true; tried = true; angle = 180;
      }
    } else if (!accepted && p.rotation_method === 'search') {
      // step6 search_optimal_rotation: the smallest angle whose coverage is within COVERAGE_TIE_TOL of the best
      const step = 360 / p.rotation_search_angles, cands = [];
      for (let a = 0; a < p.rotation_search_angles; a++) {
        const deg = a * step, k2 = rectangleCorners(pt, rotate(normal, deg), p.width, p.depth);
        cands.push({ deg, k2, ...cellCoverage(k2, mask, h, w) });
      }
      const max = Math.max(...cands.map(c => c.coverage));
      let bc = 0, bk = null, ba = 0, bp = [];
      if (max > 0) {
        const c = cands.find(c => c.coverage >= max - COVERAGE_TIE_TOL);
        bc = c.coverage; bk = c.k2; ba = c.deg; bp = c.pixels;
      }
      if (bc >= p.min_cell_coverage) {
        corners = bk; coverage = bc; pixels = bp; accepted = true; tried = true; angle = ba;
      }
    }
    return { point_index: i, edge_point: pt, normal, corners, coverage, pixels, accepted, rotation_tried: tried,
      rotation_angle: angle };
  });
}

// Steps 2, 5, 6 for the frames in `which` (default: all), then step 7 with `measure(frame, pixels)` on accepted
// rectangles. stack = { masks: [Uint8Array] (binary 0/1), h, w }. Edges of every frame are computed only when
// 'fixed_x' needs them.
export function runPipeline(stack, p, which = null, measure = () => NaN) {
  const T = stack.masks.length, { h, w } = stack;
  which = which ?? [...Array(T).keys()];
  const need = p.sampling_method === 'fixed_x' ? [...Array(T).keys()] : which;
  const edges = new Array(T).fill(null);
  for (const i of need) edges[i] = edgeForFrame(stack.masks[i], h, w, p);
  const sampled = sampleEdges(edges.map(e => e || []), p, which);
  return which.map(i => {
    const pts = sampled.get(i), edge = edges[i];
    const rects = pts.length && edge.length ? rectanglesForFrame(pts, edge, stack.masks[i], h, w, p) : [];
    for (const r of rects) r.intensity = r.accepted ? measure(i, r.pixels) : NaN;
    return { frame: i, edge, sampled: pts, rects };
  });
}
