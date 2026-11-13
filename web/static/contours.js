// Pure-JS ports of the two library routines step2_edge_detection.py relies on (no DOM; node-tested against Python):
//  - findContours: skimage.measure.find_contours(array, level) with the defaults the pipeline uses
//    (fully_connected='low', positive_orientation='low'): marching squares, then segment assembly in the same order,
//    so the contours, their point order and their order in the list match skimage's.
//  - gaussianFilter1d: scipy.ndimage.gaussian_filter1d(x, sigma, mode='wrap' | 'reflect'), truncate 4.0.
// Coordinates are (row, col) with pixel centres at integers, as in skimage.

function frac(from, to, level) {
  return to === from ? 0 : (level - from) / (to - from);
}

// Marching-squares segments, in skimage's scan order (rows, then columns) and per-case orientation.
function segments(a, h, w, level) {
  const out = [];
  for (let r0 = 0; r0 < h - 1; r0++) {
    for (let c0 = 0; c0 < w - 1; c0++) {
      const r1 = r0 + 1, c1 = c0 + 1;
      const ul = a[r0 * w + c0], ur = a[r0 * w + c1], ll = a[r1 * w + c0], lr = a[r1 * w + c1];
      if (Number.isNaN(ul) || Number.isNaN(ur) || Number.isNaN(ll) || Number.isNaN(lr)) continue;
      let sq = 0;
      if (ul > level) sq += 1;
      if (ur > level) sq += 2;
      if (ll > level) sq += 4;
      if (lr > level) sq += 8;
      if (sq === 0 || sq === 15) continue;
      const top = [r0, c0 + frac(ul, ur, level)], bottom = [r1, c0 + frac(ll, lr, level)];
      const left = [r0 + frac(ul, ll, level), c0], right = [r0 + frac(ur, lr, level), c1];
      switch (sq) {
        case 1: out.push([top, left]); break;
        case 2: out.push([right, top]); break;
        case 3: out.push([right, left]); break;
        case 4: out.push([left, bottom]); break;
        case 5: out.push([top, bottom]); break;
        case 6: out.push([right, top], [left, bottom]); break;  // vertex_connect_high = False
        case 7: out.push([right, bottom]); break;
        case 8: out.push([bottom, right]); break;
        case 9: out.push([top, left], [bottom, right]); break;  // vertex_connect_high = False
        case 10: out.push([bottom, top]); break;
        case 11: out.push([bottom, left]); break;
        case 12: out.push([left, right]); break;
        case 13: out.push([top, right]); break;
        case 14: out.push([left, top]); break;
      }
    }
  }
  return out;
}

const key = p => p[0] + ',' + p[1];

// skimage _assemble_contours: join segments end to end, keeping the earliest-created contour when two meet.
function assemble(segs) {
  let index = 0;
  const contours = new Map(), starts = new Map(), ends = new Map();
  for (const [from, to] of segs) {
    const kf = key(from), kt = key(to);
    if (kf === kt) continue;
    const t = starts.get(kt); starts.delete(kt);
    const hd = ends.get(kf); ends.delete(kf);
    if (t && hd) {
      const [tail, tailNum] = t, [head, headNum] = hd;
      if (tail === head) {
        head.push(to);
      } else if (tailNum > headNum) {
        for (const p of tail) head.push(p);
        contours.delete(tailNum);
        starts.set(key(head[0]), [head, headNum]);
        ends.set(key(head[head.length - 1]), [head, headNum]);
      } else {
        const old = tail.slice();  // prepend head in place (the maps hold this array)
        tail.length = 0;
        for (const p of head) tail.push(p);
        for (const p of old) tail.push(p);
        starts.delete(key(head[0]));
        contours.delete(headNum);
        starts.set(key(tail[0]), [tail, tailNum]);
        ends.set(key(tail[tail.length - 1]), [tail, tailNum]);
      }
    } else if (!t && !hd) {
      const c = [from, to];
      contours.set(index, c);
      starts.set(kf, [c, index]);
      ends.set(kt, [c, index]);
      index++;
    } else if (!hd) {
      const [tail, tailNum] = t;
      tail.unshift(from);
      starts.set(kf, [tail, tailNum]);
    } else {
      const [head, headNum] = hd;
      head.push(to);
      ends.set(kt, [head, headNum]);
    }
  }
  return [...contours.keys()].sort((a, b) => a - b).map(k => contours.get(k));
}

// All iso-contours of a (h x w) row-major array at `level`; each contour is an array of [row, col] points.
export function findContours(a, h, w, level) {
  if (h < 2 || w < 2) throw new Error('Input array must be at least 2x2.');
  return assemble(segments(a, h, w, level));
}

// scipy _gaussian_kernel1d(sigma, 0, radius): normalised exp(-x^2 / (2 sigma^2)) for x = -radius..radius.
export function gaussianKernel(sigma, radius) {
  const s2 = sigma * sigma, phi = [];
  let sum = 0;
  for (let x = -radius; x <= radius; x++) { const v = Math.exp(-0.5 / s2 * x * x); phi.push(v); sum += v; }
  return phi.map(v => v / sum);
}

export function extend(i, n, mode) {
  if (i >= 0 && i < n) return i;
  if (mode === 'wrap') return ((i % n) + n) % n;
  if (mode === 'nearest') return i < 0 ? 0 : n - 1;
  const p = 2 * n, j = ((i % p) + p) % p;  // 'reflect': d c b a | a b c d | d c b a
  return j < n ? j : p - 1 - j;
}

// scipy.ndimage.gaussian_filter1d for a 1-D array (truncate = 4.0), summed in scipy's symmetric-kernel order.
export function gaussianFilter1d(x, sigma, mode = 'reflect') {
  const n = x.length, radius = Math.trunc(4.0 * sigma + 0.5), w = gaussianKernel(sigma, radius);
  const out = new Array(n);
  for (let i = 0; i < n; i++) {
    let s = x[i] * w[radius];
    for (let d = radius; d >= 1; d--) s += (x[extend(i - d, n, mode)] + x[extend(i + d, n, mode)]) * w[radius - d];
    out[i] = s;
  }
  return out;
}
