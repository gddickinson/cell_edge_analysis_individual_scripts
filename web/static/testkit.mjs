// Shared helpers for the node tests (*.test.mjs): the fixture, the demo stack and tolerant comparisons.
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { readTiff } from './tiff.js';

const here = dirname(fileURLToPath(import.meta.url));
export const root = join(here, '..', '..');
export const fx = JSON.parse(readFileSync(join(root, 'tests', 'fixtures', 'web_fixture.json'), 'utf8'));
export const load = rel => readTiff(new Uint8Array(readFileSync(join(root, rel))).buffer);
export const readJson = rel => JSON.parse(readFileSync(join(root, rel), 'utf8'));

export const T = { fails: 0, checks: 0 };
export const fail = msg => { T.fails++; if (T.fails <= 25) console.error('FAIL', msg); };
export function close(a, b, what, rtol = 1e-9, atol = 1e-9) {
  T.checks++;
  const na = a == null || Number.isNaN(a), nb = b == null || Number.isNaN(b);
  if (na || nb) { if (na !== nb) fail(`${what}: ${a} vs ${b}`); return; }
  if (Math.abs(a - b) > atol + rtol * Math.abs(b)) fail(`${what}: ${a} vs ${b}`);
}
export function arr(a, b, what, rtol, atol) {
  if (a.length !== b.length) return fail(`${what}: length ${a.length} vs ${b.length}`);
  for (let i = 0; i < a.length; i++) close(a[i], b[i], `${what}[${i}]`, rtol, atol);
}
export const pts = (a, b, what, tol) => {
  if (a.length !== b.length) return fail(`${what}: ${a.length} points vs ${b.length}`);
  a.forEach((p, i) => { close(p[0], b[i][0], `${what}[${i}].y`, tol); close(p[1], b[i][1], `${what}[${i}].x`, tol); });
};
export function demoStack() {
  const img = load(fx.demo.image), msk = load(fx.demo.mask);
  return { img, stack: { images: img.frames, masks: msk.frames.map(f => Uint8Array.from(f, v => (v > 0 ? 1 : 0))), h: img.h, w: img.w } };
}
export function finish(name) {
  if (T.fails) { console.error(`${name}: ${T.fails} of ${T.checks} checks failed`); process.exit(1); }
  console.log(`${name}: all ${T.checks} checks agree with Python`);
}
