// Drawing helpers shared by the pages: the frame canvas with mask / edge / rectangles (adapted from the sibling repo
// cell_edge_analysis, like the step 5-7 verification figures), per-column edge curves, and small SVG charts.
import { esc } from './core.js';

// Viridis anchors (the colour map the step 7 figures use), linearly interpolated.
const VIR = [[68, 1, 84], [59, 82, 139], [33, 145, 140], [94, 201, 98], [253, 231, 37]];
export function viridis(t) {
  t = Math.min(1, Math.max(0, Number.isFinite(t) ? t : 0)) * (VIR.length - 1);
  const i = Math.min(VIR.length - 2, Math.floor(t)), f = t - i, a = VIR[i], b = VIR[i + 1];
  return `rgb(${a.map((v, k) => Math.round(v + (b[k] - v) * f)).join(',')})`;
}

export const fmt = (v, d = 2) => (v == null || Number.isNaN(v) ? '—' : Number(v).toFixed(d));

// Contrast limits as the verification figures use them: 1st and 99.5th percentile of the frame.
function limits(img) {
  const s = Float32Array.from(img).sort(), q = p => s[Math.min(s.length - 1, Math.floor((s.length - 1) * p))];
  return [q(0.01), q(0.995)];
}

export function intensityRange(frames) {
  const v = frames.flatMap(f => f.rects.filter(r => r.accepted).map(r => r.intensity)).filter(Number.isFinite);
  return v.length ? [Math.min(...v), Math.max(...v)] : [0, 1];
}

// Draw frame `res.frame` of the stack with overlays into canvas; opts: { mask, edge, rects, points, range }.
export function drawFrame(canvas, stack, res, opts) {
  const { w, h } = stack, i = res.frame, s = Math.max(1, Math.min(8, Math.ceil(900 / Math.max(w, h))));
  canvas.width = w * s; canvas.height = h * s;
  const off = document.createElement('canvas');
  off.width = w; off.height = h;
  const octx = off.getContext('2d'), id = octx.createImageData(w, h), img = stack.images[i], m = stack.masks[i];
  const [lo, hi] = limits(img), span = hi > lo ? hi - lo : 1;
  for (let k = 0; k < w * h; k++) {
    const g = Math.max(0, Math.min(255, Math.round((img[k] - lo) / span * 255)));
    const tint = opts.mask && m[k] ? 0.82 : 1;
    id.data[4 * k] = g * tint; id.data[4 * k + 1] = g; id.data[4 * k + 2] = g * tint; id.data[4 * k + 3] = 255;
  }
  octx.putImageData(id, 0, 0);
  const ctx = canvas.getContext('2d');
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(off, 0, 0, w * s, h * s);
  const X = p => (p[1] + 0.5) * s, Y = p => (p[0] + 0.5) * s;
  if (opts.edge && res.edge.length) {
    ctx.strokeStyle = '#ff4d4d'; ctx.lineWidth = Math.max(1.5, s * 0.4); ctx.beginPath();
    res.edge.forEach((p, k) => (k ? ctx.lineTo(X(p), Y(p)) : ctx.moveTo(X(p), Y(p))));
    ctx.stroke();
  }
  const [a, b] = opts.range;
  if (opts.rects) {
    for (const r of res.rects) {
      if (!r.corners) continue;
      ctx.beginPath();
      r.corners.forEach((p, k) => (k ? ctx.lineTo(X(p), Y(p)) : ctx.moveTo(X(p), Y(p))));
      ctx.closePath();
      if (r.accepted) {
        ctx.globalAlpha = 0.5; ctx.fillStyle = viridis(b > a ? (r.intensity - a) / (b - a) : 0.5); ctx.fill();
        ctx.globalAlpha = 1; ctx.strokeStyle = '#ffffff'; ctx.setLineDash([]);
      } else { ctx.strokeStyle = '#ff5cc8'; ctx.setLineDash([4, 4]); }
      ctx.lineWidth = 1; ctx.stroke(); ctx.setLineDash([]);
    }
  }
  if (opts.points) {
    for (const p of res.sampled) {
      if (Number.isNaN(p[0])) continue;
      ctx.beginPath(); ctx.arc(X(p), Y(p), Math.max(3, s * 0.9), 0, 2 * Math.PI);
      ctx.fillStyle = '#ffd400'; ctx.fill(); ctx.strokeStyle = '#c00'; ctx.lineWidth = 1.5; ctx.stroke();
    }
  }
}

// Per-column edge curves y(x) over the frame: curves = [{ y: [..], color, width, dash }], s = canvas scale.
export function drawCurves(canvas, curves, w, h) {
  const ctx = canvas.getContext('2d'), s = canvas.width / w;
  for (const c of curves) {
    ctx.strokeStyle = c.color; ctx.lineWidth = c.width || 2; ctx.setLineDash(c.dash || []);
    ctx.beginPath();
    let pen = false;
    c.y.forEach((v, x) => {
      if (!Number.isFinite(v)) { pen = false; return; }
      const X = (x + 0.5) * s, Y = (v + 0.5) * s;
      if (pen) ctx.lineTo(X, Y); else ctx.moveTo(X, Y);
      pen = true;
    });
    ctx.stroke();
  }
  ctx.setLineDash([]);
}

export function axes(W, H, m, xr, yr, xl, yl, yTicks = true, nx = 5) {
  const sx = v => m.l + (v - xr[0]) / (xr[1] - xr[0] || 1) * (W - m.l - m.r);
  const sy = v => H - m.b - (v - yr[0]) / (yr[1] - yr[0] || 1) * (H - m.t - m.b);
  const ticks = (r, n = 5) => Array.from({ length: n + 1 }, (_, k) => r[0] + (r[1] - r[0]) * k / n);
  let g = `<rect class="axis-box" x="${m.l}" y="${m.t}" width="${W - m.l - m.r}" height="${H - m.t - m.b}"/>`;
  for (const t of ticks(xr, nx)) g += `<line class="grid-l" x1="${sx(t)}" x2="${sx(t)}" y1="${m.t}" y2="${H - m.b}"/><text x="${sx(t)}" y="${H - m.b + 14}" text-anchor="middle">${+t.toFixed(1)}</text>`;
  if (yTicks) for (const t of ticks(yr, 4)) g += `<line class="grid-l" x1="${m.l}" x2="${W - m.r}" y1="${sy(t)}" y2="${sy(t)}"/><text x="${m.l - 6}" y="${sy(t) + 4}" text-anchor="end">${+t.toPrecision(3)}</text>`;
  g += `<text class="axis-label" x="${(W + m.l - m.r) / 2}" y="${H - 4}" text-anchor="middle">${esc(xl)}</text>
    <text class="axis-label" transform="translate(13 ${(H - m.b + m.t) / 2}) rotate(-90)" text-anchor="middle">${esc(yl)}</text>`;
  return { g, sx, sy };
}

// Line chart of several series over x: series = [{ name, color, pts: [[x, y]], dash }]; marks a highlighted x.
export function lineChart(series, { xl, yl, aria, mark = null, W = 520, H = 280, yZero = false }) {
  const all = series.flatMap(s => s.pts).filter(p => Number.isFinite(p[1]));
  const m = { l: 58, r: 14, t: 12, b: 40 };
  if (!all.length) return `<svg class="plot" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(aria)}"><text x="${W / 2}" y="${H / 2}" text-anchor="middle">no values</text></svg>`;
  const xr = [Math.min(...all.map(p => p[0])), Math.max(...all.map(p => p[0]))];
  const yr = [yZero ? Math.min(0, ...all.map(p => p[1])) : Math.min(...all.map(p => p[1])), Math.max(...all.map(p => p[1]))];
  if (yr[0] === yr[1]) { yr[0] -= 1; yr[1] += 1; }
  if (xr[0] === xr[1]) { xr[0] -= 0.5; xr[1] += 0.5; }
  const span = Math.round(xr[1] - xr[0]), nx = span >= 1 && span <= 10 && Number.isInteger(xr[0]) ? span : 5;
  const { g, sx, sy } = axes(W, H, m, xr, yr, xl, yl, true, nx);
  let body = mark != null ? `<line x1="${sx(mark)}" x2="${sx(mark)}" y1="${m.t}" y2="${H - m.b}" stroke="var(--accent3)" stroke-dasharray="3 3"/>` : '';
  for (const s of series) {
    const pts = s.pts.filter(p => Number.isFinite(p[1]));
    body += `<path d="${pts.map((p, k) => `${k ? 'L' : 'M'}${sx(p[0]).toFixed(1)},${sy(p[1]).toFixed(1)}`).join('')}" fill="none" stroke="${s.color}" stroke-width="2" ${s.dash ? `stroke-dasharray="${s.dash}"` : ''}/>`;
    if (pts.length < 40) body += pts.map(p => `<circle cx="${sx(p[0]).toFixed(1)}" cy="${sy(p[1]).toFixed(1)}" r="3.5" fill="${s.color}"><title>${esc(s.name)}: x ${fmt(p[0], 1)}, ${fmt(p[1], 3)}</title></circle>`).join('');
  }
  const legend = series.map(s => `<span class="lg"><i style="background:${s.color}"></i>${esc(s.name)}</span>`).join('');
  return `<svg class="plot" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(aria)}">${g}${body}</svg><div class="legend small">${legend}</div>`;
}
