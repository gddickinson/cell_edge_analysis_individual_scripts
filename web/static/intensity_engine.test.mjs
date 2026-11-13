// Node test: edge_engine.js + intensity_engine.js (+ tiff.js) against Python reference values in
// tests/fixtures/web_fixture.json (scripts/make_web_fixture.py, from the repo's own step functions).
// Run: node web/static/intensity_engine.test.mjs
import { percentile32, runIntensity, intensityLabel } from './intensity_engine.js';
import { fx, close, fail, pts, demoStack, finish, T } from './testkit.mjs';

const { img, stack } = demoStack();
const [N, H, W] = fx.demo.shape;
if (img.frames.length !== N || img.h !== H || img.w !== W) fail(`demo tiff shape ${img.frames.length}x${img.h}x${img.w}`);
close(img.frames.reduce((s, f) => s + f.reduce((a, v) => a + v, 0), 0), fx.demo.checksum[0], 'demo image checksum', 0, 0);
close(stack.masks.reduce((s, f) => s + f.reduce((a, v) => a + v, 0), 0), fx.demo.checksum[1], 'demo mask checksum', 0, 0);
close(img.um_per_px, 0.16, 'demo pixel size', 1e-6);
for (const p of fx.percentile) close(percentile32(img.frames[0], p.p), p.value, `percentile ${p.p}`, 1e-6);

for (const l of fx.labels) {
  T.checks++;
  if (intensityLabel(l.params) !== l.label) fail(`label: "${intensityLabel(l.params)}" vs "${l.label}"`);
}

for (const c of fx.intensity) {
  const py = c.result, js = runIntensity(stack, py.params, c.frames_requested);
  T.checks++;
  if (js.label !== py.label) fail(`${c.name} label "${js.label}" vs "${py.label}"`);
  if ((js.refs == null) !== (py.references == null)) fail(`${c.name} references presence`);
  else if (js.refs) js.refs.forEach((r, i) => close(r, py.references[i], `${c.name} reference ${i}`, 1e-6));
  if (js.frames.length !== py.frames.length) { fail(`${c.name}: ${js.frames.length} frames vs ${py.frames.length}`); continue; }
  js.frames.forEach((f, k) => {
    const q = py.frames[k], tag = `${c.name} f${q.frame}`;
    if (f.edge.length !== q.edge.n) fail(`${tag} edge length ${f.edge.length} vs ${q.edge.n}`);
    const s = f.edge.reduce((a, p) => [a[0] + p[0], a[1] + p[1]], [0, 0]);
    close(s[0], q.edge.sum[0], `${tag} edge sum y`); close(s[1], q.edge.sum[1], `${tag} edge sum x`);
    pts(f.sampled, q.sampled, `${tag} sampled`, 1e-9);
    if (f.rects.length !== q.rects.length) return fail(`${tag}: ${f.rects.length} rects vs ${q.rects.length}`);
    f.rects.forEach((r, i) => {
      const e = q.rects[i], t = `${tag} rect ${i}`;
      T.checks++;
      if (r.accepted !== e.accepted) fail(`${t} accepted ${r.accepted} vs ${e.accepted}`);
      if (r.pixels.length !== e.n_pixels) fail(`${t} n_pixels ${r.pixels.length} vs ${e.n_pixels}`);
      close(r.coverage, e.coverage, `${t} coverage`);
      close(r.intensity, e.intensity, `${t} intensity`, 2e-6, 1e-6);
      if (r.corners) pts(r.corners, e.corners, `${t} corners`, 1e-9);
    });
  });
}
finish('intensity_engine');
