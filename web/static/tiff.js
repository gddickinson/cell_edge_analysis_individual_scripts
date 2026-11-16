// Small pure-JS TIFF stack reader (no library, no DOM): baseline uncompressed TIFF, one sample per pixel, 8/16/32-bit
// integer or 32/64-bit float, either byte order, every page of the IFD chain (or ImageJ's "images=N" contiguous planes
// when only the first page has an IFD). Each page is one frame, as step1_data_loading.py reads a stack with tifffile.
// Pixel size, as web/tiff_io.py reports it: OME-XML PhysicalSizeX, else ImageJ "unit=" + XResolution, else
// ResolutionUnit = cm + XResolution; null when the file records none. Compressed files are refused with a clear message.

const TYPE_SIZE = { 1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8, 16: 8 };
const UM = { micron: 1, microns: 1, um: 1, 'µm': 1, '\\u00B5m': 1, '\\u00b5m': 1, nm: 1e-3, mm: 1e3 };
export class TiffError extends Error {}

function readIfd(dv, off, le) {
  const n = dv.getUint16(off, le), tags = {};
  for (let i = 0; i < n; i++) {
    const e = off + 2 + i * 12, tag = dv.getUint16(e, le), type = dv.getUint16(e + 2, le), count = dv.getUint32(e + 4, le);
    const size = (TYPE_SIZE[type] || 1) * count, at = size <= 4 ? e + 8 : dv.getUint32(e + 8, le);
    if (type === 2) { tags[tag] = new TextDecoder('latin1').decode(new Uint8Array(dv.buffer, dv.byteOffset + at, count)).replace(/\0+$/, ''); continue; }
    const vals = [];
    for (let k = 0; k < count; k++) {
      if (type === 3 || type === 8) vals.push(dv.getUint16(at + 2 * k, le));
      else if (type === 4 || type === 9) vals.push(dv.getUint32(at + 4 * k, le));
      else if (type === 5) vals.push(dv.getUint32(at + 8 * k, le) / dv.getUint32(at + 8 * k + 4, le));
      else if (type === 1 || type === 7) vals.push(dv.getUint8(at + k));
      else if (type === 11) vals.push(dv.getFloat32(at + 4 * k, le));
      else if (type === 12) vals.push(dv.getFloat64(at + 8 * k, le));
      else vals.push(0);
    }
    tags[tag] = vals;
  }
  return { tags, next: dv.getUint32(off + 2 + n * 12, le) };
}

function sampleGetter(dv, bits, fmt, le) {
  if (bits === 8) return fmt === 2 ? o => dv.getInt8(o) : o => dv.getUint8(o);
  if (bits === 16) return fmt === 2 ? o => dv.getInt16(o, le) : o => dv.getUint16(o, le);
  if (bits === 32) return fmt === 3 ? o => dv.getFloat32(o, le) : fmt === 2 ? o => dv.getInt32(o, le) : o => dv.getUint32(o, le);
  if (bits === 64 && fmt === 3) return o => dv.getFloat64(o, le);
  throw new TiffError(`${bits}-bit samples (format ${fmt}) are not supported: 8, 16 or 32-bit integer, or 32/64-bit float.`);
}

function pixelSize(tags) {
  const desc = tags[270] || '', xres = (tags[282] || [0])[0];
  const ome = desc.match(/PhysicalSizeX="([0-9.eE+-]+)"/);
  if (ome) {
    const u = desc.match(/PhysicalSizeXUnit="([^"]+)"/), f = UM[u ? u[1] : 'µm'];
    if (f) return { um: +ome[1] * f, source: 'OME-XML PhysicalSizeX' };
  }
  const unit = (desc.match(/^unit=(.*)$/m) || [])[1];
  if (desc.startsWith('ImageJ') && unit && UM[unit.trim()] && xres > 0) return { um: UM[unit.trim()] / xres, source: 'ImageJ unit + XResolution' };
  if ((tags[296] || [2])[0] === 3 && xres > 0) return { um: 1e4 / xres, source: 'TIFF XResolution (pixels per cm)' };
  return { um: null, source: 'not recorded in the file' };
}

// ArrayBuffer -> { frames: [Float32Array], w, h, bits, um_per_px, scale_source }
export function readTiff(buf) {
  const dv = new DataView(buf), bo = dv.getUint16(0);
  if (bo !== 0x4949 && bo !== 0x4D4D) throw new TiffError('Not a TIFF file.');
  const le = bo === 0x4949, magic = dv.getUint16(2, le);
  if (magic === 43) throw new TiffError('BigTIFF files need the local app (Python tifffile).');
  if (magic !== 42) throw new TiffError('Not a TIFF file.');
  const ifds = [];
  for (let off = dv.getUint32(4, le), guard = 0; off && guard < 100000; guard++) {
    const r = readIfd(dv, off, le);
    ifds.push(r.tags); off = r.next;
  }
  const first = ifds[0], w = first[256][0], h = first[257][0];
  const bits = (first[258] || [1])[0], fmt = (first[339] || [1])[0];
  if ((first[259] || [1])[0] !== 1) throw new TiffError('This TIFF is compressed; the browser reader opens uncompressed TIFFs only. Use the local app (Python tifffile reads it) or save it uncompressed in Fiji.');
  if ((first[277] || [1])[0] !== 1) throw new TiffError('RGB / multi-sample TIFFs are not supported: save a single-channel stack.');
  const get = sampleGetter(dv, bits, fmt, le), bpp = bits / 8;
  const plane = tags => {
    if (tags[256][0] !== w || tags[257][0] !== h) throw new TiffError('All pages must have the same size.');
    const out = new Float32Array(w * h), offs = tags[273], counts = tags[279];
    let i = 0;
    for (let s = 0; s < offs.length && i < out.length; s++) {
      const end = offs[s] + (counts ? counts[s] : out.length * bpp);
      for (let o = offs[s]; o < end && i < out.length; o += bpp) out[i++] = get(o);
    }
    return out;
  };
  let frames = ifds.filter(t => !((t[254] || [0])[0] & 1)).map(plane);  // skip reduced-resolution thumbnails
  const nIj = +((first[270] || '').match(/^images=(\d+)$/m) || [])[1];
  if (frames.length === 1 && nIj > 1 && first[273].length === 1) {  // ImageJ: planes stored back to back
    frames = [];
    for (let k = 0; k < nIj; k++) {
      const out = new Float32Array(w * h), base = first[273][0] + k * w * h * bpp;
      if (base + w * h * bpp > buf.byteLength) throw new TiffError('The file is shorter than its ImageJ header says.');
      for (let i = 0; i < out.length; i++) out[i] = get(base + i * bpp);
      frames.push(out);
    }
  }
  const scale = pixelSize(first);
  return { frames, w, h, bits, um_per_px: scale.um, scale_source: scale.source };
}

// Same shape from the local app's POST /api/tiff (tifffile; float32 base64, shape [T, H, W]).
export function fromServer(r) {
  const bin = atob(r.data), bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  const flat = new Float32Array(bytes.buffer), [T, h, w] = r.shape, frames = [];
  for (let t = 0; t < T; t++) frames.push(flat.slice(t * h * w, (t + 1) * h * w));
  return { frames, w, h, bits: 32, um_per_px: r.um_per_px, scale_source: r.scale_source };
}
