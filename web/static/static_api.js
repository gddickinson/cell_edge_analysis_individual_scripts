// Static-site data layer: answers api() calls without the Python server. GET paths come from the JSON exported by
// scripts/build_static.py. The analysis itself runs in the browser (edge_engine.js) on both the static site and the
// local app; the two Python-only POSTs (/tiff for compressed TIFFs, /analyse for the Python check) need the local app.
const files = new Map();
function file(rel) {
  if (!files.has(rel)) files.set(rel, fetch('api/' + rel + '.json').then(r => { if (!r.ok) throw new Error(`${r.status} ${rel}`); return r.json(); }));
  return files.get(rel);
}

export async function staticApi(path, body) {
  const clean = path.split('?')[0].replace(/^\/+/, '');
  if (body) throw new Error(`${clean} needs the local app (Python): see the README, "Run the web app".`);
  return file(clean);
}
