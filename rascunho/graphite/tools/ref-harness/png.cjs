// png.cjs — minimal PNG decoder (8-bit, non-interlaced, grey/RGB/RGBA) → {width, height, rgba}
const zlib = require('zlib');
function decodePNG(buf) {
  let p = 8, w = 0, h = 0, ct = 0, idat = [];
  while (p < buf.length) {
    const len = buf.readUInt32BE(p), type = buf.toString('ascii', p + 4, p + 8), data = buf.subarray(p + 8, p + 8 + len);
    if (type === 'IHDR') { w = data.readUInt32BE(0); h = data.readUInt32BE(4); if (data[8] !== 8 || data[12] !== 0) throw new Error('unsupported png'); ct = data[9]; }
    else if (type === 'IDAT') idat.push(data);
    p += 12 + len;
  }
  const ch = { 0: 1, 2: 3, 4: 2, 6: 4 }[ct], raw = zlib.inflateSync(Buffer.concat(idat)), stride = w * ch;
  const out = Buffer.alloc(w * h * ch);
  let prev = Buffer.alloc(stride);
  for (let y = 0; y < h; y++) {
    const f = raw[y * (stride + 1)], line = raw.subarray(y * (stride + 1) + 1, (y + 1) * (stride + 1));
    const cur = Buffer.alloc(stride);
    for (let i = 0; i < stride; i++) {
      const a = i >= ch ? cur[i - ch] : 0, b = prev[i], c = i >= ch ? prev[i - ch] : 0;
      let v = line[i];
      if (f === 1) v += a; else if (f === 2) v += b; else if (f === 3) v += (a + b) >> 1;
      else if (f === 4) { const pp = a + b - c, pa = Math.abs(pp - a), pb = Math.abs(pp - b), pc = Math.abs(pp - c); v += pa <= pb && pa <= pc ? a : pb <= pc ? b : c; }
      cur[i] = v & 255;
    }
    cur.copy(out, y * stride); prev = cur;
  }
  const rgba = new Uint8Array(w * h * 4);
  for (let i = 0; i < w * h; i++) {
    const s = i * ch;
    if (ch === 1) { rgba[i*4] = rgba[i*4+1] = rgba[i*4+2] = out[s]; rgba[i*4+3] = 255; }
    else if (ch === 2) { rgba[i*4] = rgba[i*4+1] = rgba[i*4+2] = out[s]; rgba[i*4+3] = out[s+1]; }
    else if (ch === 3) { rgba[i*4] = out[s]; rgba[i*4+1] = out[s+1]; rgba[i*4+2] = out[s+2]; rgba[i*4+3] = 255; }
    else { rgba[i*4] = out[s]; rgba[i*4+1] = out[s+1]; rgba[i*4+2] = out[s+2]; rgba[i*4+3] = out[s+3]; }
  }
  return { width: w, height: h, rgba };
}
module.exports = { decodePNG };
