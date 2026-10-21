// render.mjs — draw the engine's test sheet to a PNG and print measurements.
//
//   node test/render.mjs [out.png] [--paper noise|tooth|paper|smooth] [--rate 1] [--flat 600]
//   --rate  pencil gain per dab (1 = reference)   --flat  flat-lead reach in px
//   Also writes <out>-4x.png, a 4× crop of the HB/2B/4B ladders and the tilt row.
//
// Rows (top to bottom):
//   1. pressure ladder 0.1 … 1.0 for 4H 2H HB 2B 4B 6B (one stroke each)
//   2. HB tilt: altitude 90 60 45 30 20 degrees, lead pointing +x, stroke along +y
//   3. HB build-up: 1 2 4 8 passes at p 0.4; then speed test (event steps 1/4/16/40 px)
//   4. 4B patch: left as drawn, erased (plastic), kneaded, smudged out of the patch
// Prints: mean darkness per stroke core, apparent width, ms per dab.

import { writeFileSync } from "node:fs";
import { performance } from "node:perf_hooks";
import { createEngine, PENCIL_GRADES } from "../engine/engine.js";
import { encodePNG } from "./png.mjs";

const args = process.argv.slice(2);
const out = args.find((a) => !a.startsWith("--")) || new URL("./render.png", import.meta.url).pathname;
const opt = (k, d) => { const i = args.indexOf("--" + k); return i >= 0 ? args[i + 1] : d; };
const paper = opt("paper", "noise");
const rate = +opt("rate", "1");
const flat = +opt("flat", "600");

const W = 1100, H = 760;
const eng = createEngine({ width: W, height: H, paper });
const DEG = Math.PI / 180;

let dabTime = 0, dabCount = 0;
function stroke(tool, pts, over) {
  const base = eng.setTool(tool);
  eng.setTool(tool, base.kind === "pencil" ? { rate, flatReach: flat, ...over } : over);
  const t0 = performance.now();
  const [x0, y0, p0, a0 = 90, z0 = 0] = pts[0];
  eng.strokeBegin(x0, y0, p0, a0 * DEG, z0 * DEG);
  for (let i = 1; i < pts.length; i++) {
    const [x, y, p, a = 90, z = 0] = pts[i];
    eng.strokeMove(x, y, p, a * DEG, z * DEG);
  }
  const [xe, ye, , ae = 90, ze = 0] = pts[pts.length - 1];
  eng.strokeEnd(xe, ye, 0, ae * DEG, ze * DEG);
  dabTime += performance.now() - t0;
}
function line(tool, x0, y0, x1, y1, p, { step = 2, alt = 90, az = 0 } = {}, over) {
  const n = Math.max(1, Math.round(Math.hypot(x1 - x0, y1 - y0) / step));
  const pts = [];
  for (let i = 0; i <= n; i++) pts.push([x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n, p, alt, az]);
  stroke(tool, pts, over);
}
// darkness stats of a horizontal stroke: mean of the core row band, width at 10% of peak
function measureH(x0, x1, yc) {
  const prof = [];
  for (let y = yc - 20; y <= yc + 20; y++) {
    let s = 0; for (let x = x0 + 10; x < x1 - 10; x++) s += eng.density[y * W + x];
    prof.push(s / (x1 - x0 - 20));
  }
  const peak = Math.max(...prof);
  const core = prof.filter((v) => v >= peak * 0.6);
  const width = prof.filter((v) => v >= peak * 0.1).length;
  return { peak: peak / 255, core: core.reduce((a, b) => a + b, 0) / core.length / 255, width };
}

const report = [];
// Row 1: pressure ladders per grade
let y = 40;
for (const g of PENCIL_GRADES) {
  const row = [];
  for (let i = 0; i < 10; i++) {
    const p = (i + 1) / 10, x0 = 40 + i * 100;
    line(g, x0, y, x0 + 80, y, p);
    row.push(measureH(x0, x0 + 80, y));
  }
  report.push(`${g.padEnd(3)} core ` + row.map((m) => m.core.toFixed(2)).join(" ") + "  width " + row.map((m) => m.width).join(" "));
  y += 32;
}
// Row 2: tilt, HB, vertical strokes
y += 20;
const tiltRow = [];
[90, 70, 55, 40, 25, 15].forEach((alt, i) => {
  const x = 60 + i * 110;
  line("HB", x, y, x, y + 110, 0.5, { alt, az: 0 });
  // perpendicular profile at mid height
  const yc = y + 55; const prof = [];
  for (let dx = -24; dx <= 24; dx++) prof.push(eng.density[yc * W + x + dx]);
  const peak = Math.max(...prof); const idx = prof.indexOf(peak) - 24;
  tiltRow.push(`alt${alt}: peak ${(peak / 255).toFixed(2)} at ${idx >= 0 ? "+" : ""}${idx}px width ${prof.filter((v) => v >= peak * 0.1).length}`);
});
report.push("HB tilt (p 0.5): " + tiltRow.join(" | "));
// also 4B flat shading patch to the right
for (let k = 0; k < 14; k++) line("4B", 760 + k * 6, y, 760 + k * 6, y + 110, 0.6, { alt: 25, az: 0 });
for (let k = 0; k < 14; k++) line("4B", 880 + k * 6, y, 880 + k * 6, y + 110, 0.6, { alt: 90, az: 0 });

// Row 3: build-up and speed
y += 150;
const bu = [];
[1, 2, 4, 8].forEach((n, i) => {
  const x0 = 40 + i * 130;
  for (let k = 0; k < n; k++) line("HB", x0, y, x0 + 100, y, 0.4);
  bu.push(`${n}x ${measureH(x0, x0 + 100, y).core.toFixed(2)}`);
});
report.push("HB build-up p0.4: " + bu.join("  "));
const sp = [];
[1, 4, 16, 40].forEach((step, i) => {
  const x0 = 580 + i * 130;
  line("HB", x0, y, x0 + 100, y, 0.5, { step });
  sp.push(`step${step} ${measureH(x0, x0 + 100, y).core.toFixed(2)}`);
});
report.push("HB event step (p0.5): " + sp.join("  "));

// Row 4: patches
y += 60;
function patch(tool, x, yy, p) { for (let k = 0; k < 16; k++) line(tool, x, yy + k * 5, x + 110, yy + k * 5, p); }
const px = [40, 300, 560, 820];
px.forEach((x) => patch("4B", x, y, 0.8));
const before = measureH(px[0], px[0] + 110, y + 38).core;
line("eraser", px[1] - 20, y + 38, px[1] + 130, y + 38, 0.7);
line("kneaded", px[2] - 20, y + 38, px[2] + 130, y + 38, 0.7);
line("smudge", px[3] + 20, y + 38, px[3] + 110 + 170, y + 38, 0.6, { step: 3 });
const er = eng.density[(y + 38) * W + px[1] + 55] / 255, kn = eng.density[(y + 38) * W + px[2] + 55] / 255;
const smOut = [20, 60, 100, 140].map((d) => (eng.density[(y + 38) * W + px[3] + 110 + d] / 255).toFixed(2));
report.push(`4B patch ${before.toFixed(2)} → eraser ${er.toFixed(2)}, kneaded ${kn.toFixed(2)}, smudge tail +20/60/100/140px: ${smOut.join(" ")}`);

// a word sample at the bottom right: quick scribble
let s = []; for (let i = 0; i <= 200; i++) { const t = i / 200; s.push([40 + t * 1000, 700 + Math.sin(t * 40) * 18, 0.3 + 0.6 * Math.abs(Math.sin(t * 9)), 60, 90]); }
stroke("2B", s);

const rgba = eng.toRGBA();
writeFileSync(out, encodePNG(rgba, W, H));
console.log(report.join("\n"));
console.log(`dab time total ${dabTime.toFixed(1)} ms; paper mean ${eng.paper.mean.toFixed(2)} contrast ${eng.paper.contrast.toFixed(2)}`);
console.log("wrote", out);

// 4x nearest-neighbour crop of the HB/2B/4B ladders and the tilt row, for grain
{
  const cx0 = 540, cy0 = 90, cw = 270, ch = 190, S = 4;
  const crop = new Uint8ClampedArray(cw * S * ch * S * 4);
  for (let yy = 0; yy < ch * S; yy++) for (let xx = 0; xx < cw * S; xx++) {
    const si = ((cy0 + (yy / S | 0)) * W + cx0 + (xx / S | 0)) * 4, di = (yy * cw * S + xx) * 4;
    crop[di] = rgba[si]; crop[di + 1] = rgba[si + 1]; crop[di + 2] = rgba[si + 2]; crop[di + 3] = 255;
  }
  const zoomOut = out.replace(/\.png$/, "-4x.png");
  writeFileSync(zoomOut, encodePNG(crop, cw * S, ch * S));
  console.log("wrote", zoomOut);
}
