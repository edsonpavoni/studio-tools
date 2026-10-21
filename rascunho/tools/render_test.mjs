#!/usr/bin/env node
// render_test.mjs — offline harness for brush.js. Simulates Pencil strokes into a fake
// tile sheet, writes tools/render_test.png (device px) and tools/render_test-8x.png
// (8× nearest-neighbour crop of the medium line) so the marks can be compared with
// tools/reference/8bitpaint-detail-8x.png. No npm: PNG is written with zlib + Buffer.
//
//   node tools/render_test.mjs [--preset HB] [--bench]
import { readFileSync, writeFileSync } from 'node:fs';
import { deflateSync } from 'node:zlib';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { makePaper, PencilStroke, PRESETS, DEFAULT_SETTINGS, PAPER_RGB } from '../brush.js';

const here = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const opt = (name, fallback) => { const i = args.indexOf('--' + name); return i >= 0 ? args[i + 1] : fallback; };
const PRESET = opt('preset', 'HB');
const W = 720, H = 560, TILE = 256;
const GRAPHITE = [0.16, 0.16, 0.18];
const UP = Math.PI / 2;

// ---------------------------------------------------------------- fake sheet
function makeSheet() {
  const tiles = new Map();
  return {
    TILE, tiles,
    tile(tx, ty) {
      const key = tx + ',' + ty;
      let t = tiles.get(key);
      if (!t) {
        t = new Uint8ClampedArray(TILE * TILE * 4);
        for (let i = 0; i < t.length; i += 4) { t[i] = PAPER_RGB[0]; t[i + 1] = PAPER_RGB[1]; t[i + 2] = PAPER_RGB[2]; t[i + 3] = 255; }
        tiles.set(key, t);
      }
      return t;
    },
    markDirty() {},
    // flatten to a W×H RGB buffer
    flatten(w, h) {
      const out = Buffer.alloc(w * h * 3);
      for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
        const t = tiles.get(Math.floor(x / TILE) + ',' + Math.floor(y / TILE));
        const o = (y * w + x) * 3;
        if (!t) { out[o] = PAPER_RGB[0]; out[o + 1] = PAPER_RGB[1]; out[o + 2] = PAPER_RGB[2]; continue; }
        const i = ((y % TILE) * TILE + (x % TILE)) * 4;
        out[o] = t[i]; out[o + 1] = t[i + 1]; out[o + 2] = t[i + 2];
      }
      return out;
    },
  };
}

// ---------------------------------------------------------------- png
const crcTable = new Int32Array(256).map((_, n) => { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; return c; });
function crc32(buf) { let c = -1; for (let i = 0; i < buf.length; i++) c = crcTable[(c ^ buf[i]) & 255] ^ (c >>> 8); return (c ^ -1) >>> 0; }
function chunk(type, data) {
  const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
  const td = Buffer.concat([Buffer.from(type, 'ascii'), data]);
  const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(td));
  return Buffer.concat([len, td, crc]);
}
function writePng(path, rgb, w, h) {
  const raw = Buffer.alloc((w * 3 + 1) * h);
  for (let y = 0; y < h; y++) { raw[y * (w * 3 + 1)] = 0; rgb.copy(raw, y * (w * 3 + 1) + 1, y * w * 3, (y + 1) * w * 3); }
  const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4); ihdr[8] = 8; ihdr[9] = 2; ihdr[10] = 0; ihdr[11] = 0; ihdr[12] = 0;
  writeFileSync(path, Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', ihdr), chunk('IDAT', deflateSync(raw, { level: 6 })), chunk('IEND', Buffer.alloc(0))]));
}
function zoomCrop(rgb, w, x0, y0, cw, ch, z) {
  const out = Buffer.alloc(cw * z * ch * z * 3);
  for (let y = 0; y < ch * z; y++) for (let x = 0; x < cw * z; x++) {
    const s = ((y0 + Math.floor(y / z)) * w + x0 + Math.floor(x / z)) * 3, o = (y * cw * z + x) * 3;
    out[o] = rgb[s]; out[o + 1] = rgb[s + 1]; out[o + 2] = rgb[s + 2];
  }
  return out;
}

// ---------------------------------------------------------------- strokes
// Every stroke is a list of samples {x, y, p, alt, az} fed at Pencil rate: STEP px apart.
const STEP = 3;   // px between samples: 100 mm/s at 264 ppi and 240 Hz is ~4 px; 3 is a slightly slower hand
function runStroke(sheet, paper, samples, preset = PRESET, settings = DEFAULT_SETTINGS) {
  const s = new PencilStroke(sheet, paper, { preset, settings, colour: GRAPHITE, erase: false });
  for (const q of samples) s.addSample(q.x, q.y, q.p, q.alt ?? UP, q.az ?? 0);
  return s.dabs;
}
function line(x0, y0, x1, y1, p, extra = {}) {
  const n = Math.max(2, Math.round(Math.hypot(x1 - x0, y1 - y0) / (extra.step || STEP)));
  const out = [];
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    out.push({ x: x0 + (x1 - x0) * t, y: y0 + (y1 - y0) * t, p: typeof p === 'function' ? p(t) : p, alt: extra.alt, az: extra.az });
  }
  return out;
}
function arc(cx, cy, r, a0, a1, p, step = STEP) {
  const n = Math.max(2, Math.round(Math.abs(a1 - a0) * r / step)), out = [];
  for (let i = 0; i <= n; i++) {
    const t = i / n, a = a0 + (a1 - a0) * t;
    out.push({ x: cx + Math.cos(a) * r, y: cy + Math.sin(a) * r, p: typeof p === 'function' ? p(t) : p });
  }
  return out;
}

function renderScene(sheet, paper) {
  let dabs = 0;
  // 1. three straight lines: light / medium / heavy
  dabs += runStroke(sheet, paper, line(40, 60, 440, 64, 0.2));
  dabs += runStroke(sheet, paper, line(40, 110, 440, 114, 0.5));
  dabs += runStroke(sheet, paper, line(40, 160, 440, 164, 0.85));
  // 2. curve with pressure ramping 0.1 → 0.9
  dabs += runStroke(sheet, paper, arc(250, 420, 190, Math.PI * 1.1, Math.PI * 1.9, (t) => 0.1 + 0.8 * t));
  // 3. 55° tilted stroke (altitude 35°), lead pointing up-left of the path, mid pressure
  dabs += runStroke(sheet, paper, line(40, 300, 440, 300, 0.5, { alt: 35 * Math.PI / 180, az: -Math.PI * 0.6 }));
  // 4. cross-hatch block: three overlapping passes at mid pressure
  for (let pass = 0; pass < 3; pass++) {
    const ang = [0.35, -0.9, 0.0][pass];
    for (let k = -6; k <= 6; k++) {
      const cx = 590, cy = 120, L = 70, dx = Math.cos(ang), dy = Math.sin(ang);
      const ox = -dy * k * 9, oy = dx * k * 9;
      dabs += runStroke(sheet, paper, line(cx - dx * L + ox, cy - dy * L + oy, cx + dx * L + ox, cy + dy * L + oy, 0.5));
    }
  }
  // 5. slow tiny circle: radius 9 px, samples 0.5 px apart, two laps
  dabs += runStroke(sheet, paper, arc(590, 300, 9, 0, Math.PI * 4, 0.55, 0.5));
  // 6. the three presets side by side, upright, medium pressure
  let y = 380;
  for (const name of Object.keys(PRESETS)) { dabs += runStroke(sheet, paper, line(500, y, 700, y + 2, 0.5), name); y += 30; }
  // 7. same at light pressure
  y = 480;
  for (const name of Object.keys(PRESETS)) { dabs += runStroke(sheet, paper, line(500, y, 700, y + 2, 0.2), name); y += 22; }
  return dabs;
}

// ---------------------------------------------------------------- main
const paper = makePaper();
const sheet = makeSheet();
const t0 = performance.now();
const dabs = renderScene(sheet, paper);
const ms = performance.now() - t0;
const rgb = sheet.flatten(W, H);
writePng(join(here, 'render_test.png'), rgb, W, H);
// 8× crop around the medium line (same framing idea as the reference detail)
writePng(join(here, 'render_test-8x.png'), zoomCrop(rgb, W, 150, 92, 160, 40, 8), 160 * 8, 40 * 8);

// darkness profile across the medium line, averaged along x (shows tube / edge ramp)
const prof = [];
for (let y = 100; y <= 124; y++) { let s = 0; for (let x = 100; x < 400; x++) s += rgb[(y * W + x) * 3]; prof.push(Math.round(255 - s / 300)); }
console.log(`scene: ${dabs} dabs in ${ms.toFixed(1)} ms (${Math.round(dabs / ms * 1000)} dabs/s incl. stroke overhead)`);
console.log('medium line darkness by row (0 = paper, 255 = black):', prof.join(' '));
const dark = (y0, y1, x0 = 100, x1 = 400) => { let m = 0, c = 0; for (let y = y0; y <= y1; y++) for (let x = x0; x < x1; x++) { const v = 255 - rgb[(y * W + x) * 3]; m = Math.max(m, v); c += v > 128 ? 1 : 0; } return { max: m, blackish: c }; };
console.log('light line:', dark(52, 72), 'medium:', dark(102, 122), 'heavy:', dark(152, 172));

if (args.includes('--bench')) {
  const b = makeSheet(), s = new PencilStroke(b, paper, { preset: PRESET, settings: DEFAULT_SETTINGS, colour: GRAPHITE, erase: false });
  const N = 20000, tb = performance.now();
  for (let i = 0; i < N; i++) s.dab({ x: 100 + (i % 300) * 0.5, y: 100 + ((i / 300) | 0) * 0.5, p: 0.5, alt: UP, az: 0 });
  const bms = performance.now() - tb;
  console.log(`bench: ${N} mid-pressure ${PRESET} dabs in ${bms.toFixed(1)} ms = ${Math.round(N / bms * 1000)} dabs/s`);
}
