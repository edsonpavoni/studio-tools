// compare.cjs — the same strokes through the reference wasm and through our
// engine, on the same paper (the reference's "noise" texture, study only),
// printed side by side and written as compare.png (reference on top, ours
// below). Run from the project root:
//   node tools/ref-harness/compare.cjs reference/8bitpaint/8bitpaintpencil [--paper noise.png]
const path = require('path'), fs = require('fs');
const { setup, lum, frameRef } = require('./frame.js');
const { decodePNG } = require('./png.cjs');
const DIR = process.argv[2];
const paperFile = (process.argv.indexOf('--paper') >= 0 ? process.argv[process.argv.indexOf('--paper') + 1] : 'noise.png');
const D = Math.PI / 180;
const W = 512, Hh = 512;

// experiments: [label, tool, strokes[]]; a stroke = {x0,y0,x1,y1,p,alt,az,step,reps}
const GRADES = { "4B": 26, "HB": 27, "2H": 28 };   // slots in the pencil app's table
const EXPS = [];
let y = 24;
for (const g of ["4B", "HB", "2H"]) {
  for (let i = 0; i < 10; i++) EXPS.push({ label: `${g} p${(i + 1) / 10}`, grade: g, x0: 20 + i * 49, x1: 20 + i * 49 + 40, y, p: (i + 1) / 10, alt: 90, az: 0, step: 4, reps: 1 });
  y += 36;
}
y += 10;
[90, 60, 45, 30, 20, 10].forEach((alt, i) => EXPS.push({ label: `HB alt${alt}`, grade: "HB", x0: 40 + i * 80, x1: 40 + i * 80, y, y1: y + 90, p: 0.5, alt, az: 0, step: 4, reps: 1, vertical: true }));
y += 110;
[1, 2, 4, 8].forEach((n, i) => EXPS.push({ label: `HB p0.4 x${n}`, grade: "HB", x0: 20 + i * 120, x1: 20 + i * 120 + 90, y, p: 0.4, alt: 90, az: 0, step: 4, reps: n }));
y += 40;
[1, 4, 16, 40].forEach((step, i) => EXPS.push({ label: `HB step${step}`, grade: "HB", x0: 20 + i * 120, x1: 20 + i * 120 + 90, y, p: 0.5, alt: 90, az: 0, step, reps: 1 }));

function drive(tablet, e) {
  const alt = e.alt * D, az = e.az * D;
  for (let r = 0; r < e.reps; r++) {
    const pts = [];
    if (e.vertical) for (let yy = e.y; yy <= e.y1; yy += e.step) pts.push([e.x0, yy]);
    else for (let x = e.x0; x <= e.x1; x += e.step) pts.push([x, e.y]);
    tablet.down(pts[0][0], pts[0][1], alt, az);
    for (const [x, yy] of pts) tablet.move(x, yy, e.p, alt, az);
    tablet.up(pts[pts.length - 1][0], pts[pts.length - 1][1], alt, az);
  }
}

// measurements on a grey frame getter g(x,y) (255 = white)
function measure(g, e) {
  if (e.vertical) {
    const yc = (e.y + e.y1) >> 1, prof = [];
    for (let dx = -40; dx <= 60; dx++) prof.push(255 - g(e.x0 + dx, yc));
    const peak = Math.max(...prof);
    const idx = prof.findIndex((v) => v === peak) - 40;
    const w = prof.filter((v) => v >= peak * 0.1).length;
    return { dark: peak / 255, width: w, off: idx, prof };
  }
  const prof = [];
  for (let dy = -16; dy <= 16; dy++) {
    let s = 0, n = 0;
    for (let x = e.x0 + 8; x <= e.x1 - 8; x++) { s += 255 - g(x, e.y + dy); n++; }
    prof.push(s / n);
  }
  const peak = Math.max(...prof);
  const core = prof.filter((v) => v >= peak * 0.6);
  return { dark: core.reduce((a, b) => a + b, 0) / core.length / 255, width: prof.filter((v) => v >= peak * 0.1).length, prof };
}

(async () => {
  const png = decodePNG(fs.readFileSync(path.join(DIR, 'img', paperFile)));
  // ---- reference
  const { c } = await setup(255, W, Hh, png.rgba);
  c('ViewZoomChangeEvent', [1]); c('SetBrushCorrection', [8]);
  const refTablet = {
    down: (x, y, alt, az) => c('TabletEvent', [x, y, 0, alt, az]),
    move: (x, y, p, alt, az) => c('TabletEvent', [x, y, p, alt, az]),
    up: (x, y, alt, az) => { for (let i = 0; i < 4; i++) c('TabletEvent', [x, y, 0, alt, az]); },
  };
  let grade = null;
  const refRes = [];
  for (const e of EXPS) {
    if (e.grade !== grade) { grade = e.grade; c('BrushSelectionEvent', [GRADES[grade]]); }
    drive(refTablet, e);
    refRes.push(measure(lum, e));
  }
  const refFrame = Uint8ClampedArray.from(frameRef());

  // ---- ours, same paper (luma of the texture), black graphite, same correction
  const { createEngine } = await import('../../engine/engine.js');
  const { paperFromGrey } = await import('../../engine/paper.js');
  const luma = new Uint8Array(512 * 512);
  for (let i = 0; i < luma.length; i++) luma[i] = Math.round(0.299 * png.rgba[i * 4] + 0.587 * png.rgba[i * 4 + 1] + 0.114 * png.rgba[i * 4 + 2]);
  const eng = createEngine({ width: W, height: Hh, paper: paperFromGrey(luma, paperFile) });
  eng.setColor([0, 0, 0]);
  const ourTablet = {
    down: (x, y, alt, az) => eng.strokeBegin(x, y, 0, alt, az),
    move: (x, y, p, alt, az) => eng.strokeMove(x, y, p, alt, az),
    up: (x, y, alt, az) => eng.strokeEnd(x, y, 0, alt, az),
  };
  const ourRes = [];
  for (const e of EXPS) {
    eng.setTool(e.grade);
    drive(ourTablet, e);
  }
  const ourRGBA = eng.toRGBA();
  const ourLum = (x, y) => ourRGBA[(y * W + x) * 4];
  for (const e of EXPS) ourRes.push(measure(ourLum, e));

  // ---- report
  const rows = [];
  EXPS.forEach((e, i) => {
    const r = refRes[i], o = ourRes[i];
    rows.push(`${e.label.padEnd(12)} ref dark ${r.dark.toFixed(2)} w ${String(r.width).padStart(2)}${e.vertical ? ` off ${r.off}` : ''}   ours dark ${o.dark.toFixed(2)} w ${String(o.width).padStart(2)}${e.vertical ? ` off ${o.off}` : ''}   Δdark ${(o.dark - r.dark).toFixed(2)}`);
  });
  console.log(rows.join('\n'));
  const err = EXPS.reduce((s, e, i) => s + Math.abs(ourRes[i].dark - refRes[i].dark), 0) / EXPS.length;
  const werr = EXPS.reduce((s, e, i) => s + Math.abs(ourRes[i].width - refRes[i].width), 0) / EXPS.length;
  console.log(`mean |Δdark| ${err.toFixed(3)}   mean |Δwidth| ${werr.toFixed(2)} px`);
  // profiles for a few
  for (const i of [4, 9, 14, 19, 24, 29, 32, 34]) {
    console.log(EXPS[i].label, '\n  ref ', refRes[i].prof.map((v) => Math.round(v)).join(' '), '\n  ours', ourRes[i].prof.map((v) => Math.round(v)).join(' '));
  }
  // side-by-side png
  const { encodePNG } = await import('../../test/png.mjs');
  const out = new Uint8ClampedArray(W * Hh * 2 * 4);
  out.set(refFrame, 0); out.set(ourRGBA, W * Hh * 4);
  const outFile = path.join(__dirname, 'compare.png');
  fs.writeFileSync(outFile, encodePNG(out, W, Hh * 2));
  console.log('wrote', outFile);
})().catch((e) => { console.error(e); process.exit(1); });
