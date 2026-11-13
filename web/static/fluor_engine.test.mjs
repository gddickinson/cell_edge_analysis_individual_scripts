// Node test: fluor_engine.js (port of fluorescence_edge_experiments/detector.py) against Python reference values in
// tests/fixtures/web_fixture.json (scripts/make_web_fixture.py). The detector reads step-1 output, so the demo stack
// is preprocessed with the pipeline's default step 1 (intensity_engine.js, tested separately).
// Run: node web/static/fluor_engine.test.mjs
import { gaussian2d, otsu, binaryClosing, fillHoles, largestComponent, despike, smoothCurve, fluorEdge, edgeDic,
  frameError, gapBetween } from './fluor_engine.js';
import { preprocessStack } from './intensity_engine.js';
import { fx, close, fail, arr, demoStack, finish, readJson, T } from './testkit.mjs';

const P = fx.fluor_parts, num = v => (v == null ? NaN : v);
for (const g of P.gaussian) {
  const h = g.img.length, w = g.img[0].length;
  arr(gaussian2d(Float64Array.from(g.img.flat()), h, w, g.sigma), g.out.flat(), `gaussian2d s=${g.sigma}`, 1e-12, 1e-12);
}
const { stack } = demoStack();
// the pipeline's default step 1 (config.PIPELINE_CONFIG): the parameters of the fixture's 'defaults' intensity case
const pre = preprocessStack(stack.images, stack.masks, fx.intensity.find(c => c.name === 'defaults').result.params);
for (const o of P.otsu) {
  const v = o.values ?? gaussian2d(Float64Array.from(pre.frames[o.demo_frame]), stack.h, stack.w, o.blur);
  close(otsu(v), o.t, `otsu ${o.demo_frame ?? ''}`, 1e-12, 1e-12);
}
for (const [k, b] of P.binary.entries()) {
  const h = b.bin.length, w = b.bin[0].length, bin = Uint8Array.from(b.bin.flat());
  for (const [name, js, py] of [['closing', binaryClosing(bin, h, w, 3), b.closing3], ['fill', fillHoles(bin, h, w), b.fill],
    ['largest', largestComponent(bin, h, w), b.largest]]) {
    T.checks++;
    const d = py.flat().findIndex((v, i) => v !== js[i]);
    if (d >= 0) fail(`binary ${k} ${name}: first difference at ${d}`);
  }
}
for (const [k, c] of P.curves.entries()) {
  const y = Float64Array.from(c.y, num);
  arr(despike(y, 5), c.despike.map(num), `despike ${k}`, 1e-12, 1e-12);
  arr(despike(y, 4), c.despike4.map(num), `despike4 ${k}`, 1e-12, 1e-12);
  arr(smoothCurve(y, 3.0), c.smooth.map(num), `smooth ${k}`, 1e-12, 1e-12);
}
const labels = readJson('web/static/demo/demo_labels.json').frames;
for (const c of fx.fluor) {
  for (const f of c.result.frames) {
    const t = `${c.name} f${f.frame}`, img = pre.frames[f.frame], m = stack.masks[f.frame];
    const dic = edgeDic(m, stack.h, stack.w), fl = fluorEdge(img, m, stack.h, stack.w, c.result.params);
    arr(dic, f.dic.map(num), `${t} dic`, 0, 0);
    arr(fl, f.fluor.map(num), `${t} fluor`, 1e-9, 1e-9);
    close(gapBetween(fl, dic), f.gap, `${t} gap`);
    const truth = labels[f.frame].y, ed = frameError(dic, truth), ef = frameError(fl, truth);
    close(ed && ed.median, f.error_dic && f.error_dic.median, `${t} error dic`);
    close(ef && ef.median, f.error_fluor && f.error_fluor.median, `${t} error fluor`);
  }
}
finish('fluor_engine');
