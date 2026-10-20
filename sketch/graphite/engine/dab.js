// dab.js — one dab, per pixel, into an 8-bit density buffer.
//
// This is the hot loop. It knows nothing about strokes, tiles, undo or
// colour: it gets a buffer with a stride and an origin, a clip rectangle,
// the paper, the tool, and the dab's geometry, and it writes density.
// A tiled surface calls it once per touched tile with that tile's origin.
//
// Density is 0..255, 0 = clean paper. Paper height h is 0..1, 1 = tooth top.
// All laws below were recovered from the reference app (research/10–12) and
// rewritten; the "ours" notes mark what we changed.
//
//   pencil   D += gain · max(0, tip(u,v) − (1 − p') − k·(1 − h))      up to the grade's cap
//   kneaded  D −= 255 · max(0, p − k·(1 − h))                           tip model backwards
//   eraser   D  = 0 inside a hard disc, diameter size·(0.55 + 0.45 p')   (soft 1 px rim: ours)
//   smudge   w = max(0, tip − (1 − p') + h − 1); D → (1 − w)·D + w·target
//            target = footprint mean (reference) blended with a carried load (ours)
//
// tip(u,v): depth of a half-ellipsoid lead tip (radius b, length a, tilted to
// the altitude) under the pixel, 0..1 of its height. Upright it is a spherical
// cap: sqrt(1 − ρ²/r²). Pressure p' sinks the tip, so light pressure gives a
// smaller and fainter footprint from one formula.
//
// Rounding (ours, research/15): increments are dithered with a hash of the
// pixel and the dab instead of rounded, so faint deposits still accumulate
// in 8 bits (the reference truncates, which is why its 2H stays faint).

import { paperIndex } from "./paper.js";

const TILT_FLAT = 0.5585053606;   // 32°: below this the lead lies on its side
const TILT_KNEAD = Math.PI / 4;    // 45° for the kneaded eraser
const TILT_PHASE = Math.PI / 4 + 0.2268928;   // 58°: phase of the elongation curve
let dabSeed = 0x9e3779b9;

// 0..1 hash of (x, y, dab) — cheap dither
function dither(x, y) {
  let h = (x * 374761393 + y * 668265263 + dabSeed) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) & 0xffff) / 65536;
}

/**
 * Geometry of a dab from the input sample (allocated once per dab).
 *  x, y        sheet position (float)
 *  pressure    0..1
 *  altitude    rad, π/2 = vertical
 *  azimuth     rad, direction the lead points, 0 = +x, π/2 = +y
 *  paper       for the tooth push-back of tilted pencil dabs
 */
export function dabGeometry(tool, x, y, pressure, altitude, azimuth, paper) {
  const p = pressure < 0 ? 0 : pressure > 1 ? 1 : pressure;
  const cosA = Math.cos(azimuth), sinA = Math.sin(azimuth);
  const alt = altitude < 0 ? 0 : altitude > Math.PI / 2 ? Math.PI / 2 : altitude;
  const s = Math.sin(alt), c = Math.cos(alt);
  const kind = tool.kind;
  const pp = tool.k ? Math.pow(p, tool.k) : p;

  let r, a, b, tiltLimit = TILT_FLAT, tiltPhase = TILT_PHASE;
  if (kind === "pencil") r = tool.size * (1 + pp) / 4;
  else if (kind === "smudge") r = Math.max(tool.size * 0.5, 2);
  else if (kind === "kneaded") { r = Math.max(tool.size, 2) * 0.25; tiltLimit = TILT_KNEAD; tiltPhase = TILT_KNEAD; }
  else /* eraser */ r = Math.max(tool.size * (0.55 + 0.45 * pp) * 0.5, 0.35);   // ours: a block of rubber keeps its width

  a = b = r;
  if (kind !== "eraser" && alt < tiltLimit) {
    const cc = Math.cos(alt + tiltPhase);        // pencil: cos(alt + 58°), kneaded: cos(alt + 45°)
    a = r + cc * cc * Math.max(tool.flatReach - r, 0);
    b = Math.max(r, a / 20);
  }
  const A = Math.sqrt(c * c * a * a + s * s * b * b);   // projected half-length along the azimuth

  // the stylus point is the tip end of the ellipse: slide it forward; a
  // tilted pencil tip also catches on the tooth (more at light pressure)
  let shift = 0;
  if (c > 0 && kind !== "eraser") {
    let m = 0;
    if (kind === "pencil" && paper) {
      const h0 = paper.height[paperIndex(x | 0, y | 0)];
      m = tool.toothCatch * Math.min(Math.sqrt(a * b) / 50, 1) / Math.max(pp, 0.02) * (1 - h0);
    }
    shift = c * (A - b - m);
  }
  const g = { kind, cx: x + cosA * shift, cy: y + sinA * shift, a, b, A, cosA, sinA, p, pp, s, c, r };
  // tip-depth constants (research/11 §4), shared by pencil and smudge
  const a2 = a * a, b2 = b * b, s2 = s * s, c2 = c * c;
  g.Dn = a2 * c2 + b2 * s2;
  g.invD = g.Dn > 1e-5 ? 1 / g.Dn : 0;
  g.invH = 1 / (c * b + Math.sqrt(b2 * c2 + a2 * s2));
  g.cb = c * b; g.k1 = s * c * (a2 - b2);
  g.q0 = a2 * b2 * c2 + b2 * b2 * s2; g.qv = b2 * s2 + a2 * c2; g.qu = b2;
  g.iA = 1 / A; g.ib = 1 / b;
  dabSeed = (dabSeed + 0x9e3779b9) | 0;
  return g;
}

/** Integer bounding box of a dab geometry, inclusive-exclusive. */
export function dabBounds(g) {
  const ex = Math.sqrt(g.A * g.A * g.cosA * g.cosA + g.b * g.b * g.sinA * g.sinA);
  const ey = Math.sqrt(g.A * g.A * g.sinA * g.sinA + g.b * g.b * g.cosA * g.cosA);
  return {
    x0: Math.floor(g.cx - ex), y0: Math.floor(g.cy - ey),
    x1: Math.ceil(g.cx + ex) + 1, y1: Math.ceil(g.cy + ey) + 1,
  };
}

function clipBounds(g, clip) {
  const bb = dabBounds(g);
  return {
    x0: Math.max(bb.x0, clip.x0), x1: Math.min(bb.x1, clip.x1),
    y0: Math.max(bb.y0, clip.y0), y1: Math.min(bb.y1, clip.y1),
  };
}

// depth of the tip under (u along azimuth, v across), 0..1; < 0 outside
function tipDepth(g, u, v) {
  const disc = g.q0 - g.qv * v * v - g.qu * u * u;
  if (disc <= 0) return -1;
  const z = (g.k1 * u - g.a * Math.sqrt(disc)) * g.invD;
  return (g.cb - z) * g.invH;
}

/**
 * Pencil kernel.
 *  buf      Uint8Array density (0 = white paper), row-major
 *  stride   pixels per row of buf
 *  ox, oy   sheet coordinate of buf[0]
 *  clip     {x0,y0,x1,y1} in sheet coords, the region of buf we may touch
 *  paper    {height} from paper.js
 *  flow     per-dab gain multiplier (stroke.js keeps darkness spacing-invariant)
 */
export function dabPencil(buf, stride, ox, oy, clip, paper, tool, g, flow) {
  const { x0, x1, y0, y1 } = clipBounds(g, clip);
  if (x0 >= x1 || y0 >= y1 || g.pp <= 0 || g.invD === 0) return false;
  const H = paper.height;
  const sink = 1 - g.pp;
  const tooth = tool.toothStrength * Math.min(Math.sqrt(g.a * g.b) / 8, 1);
  const Dmax = 255 * (1 - tool.floor);
  const gain = flow * tool.rate * Dmax;
  for (let y = y0; y < y1; y++) {
    const dy = y + 0.5 - g.cy;
    const row = (y - oy) * stride - ox;
    for (let x = x0; x < x1; x++) {
      const dx = x + 0.5 - g.cx;
      const u = dx * g.cosA + dy * g.sinA, v = -dx * g.sinA + dy * g.cosA;
      const eu = u * g.iA, ev = v * g.ib;
      if (eu * eu + ev * ev > 1) continue;
      let val = tipDepth(g, u, v) - sink;
      if (val <= 0) continue;
      val -= tooth * (1 - H[paperIndex(x, y)]);
      if (val <= 0) continue;
      const i = row + x, D = buf[i];
      if (D >= Dmax) continue;
      const nd = D + gain * val + dither(x, y);
      buf[i] = nd > Dmax ? Dmax : nd;
    }
  }
  return true;
}

/** Kneaded eraser: flat coverage p, texture-aware, subtracts a fixed amount. */
export function dabKneaded(buf, stride, ox, oy, clip, paper, tool, g, flow) {
  const { x0, x1, y0, y1 } = clipBounds(g, clip);
  if (x0 >= x1 || y0 >= y1 || g.p <= 0) return false;
  const H = paper.height;
  const k = Math.min(Math.sqrt(g.a * g.b) / 8, 1) * tool.toothStrength;
  const amount = 255 * flow * tool.rate;
  for (let y = y0; y < y1; y++) {
    const dy = y + 0.5 - g.cy;
    const row = (y - oy) * stride - ox;
    for (let x = x0; x < x1; x++) {
      const dx = x + 0.5 - g.cx;
      const u = dx * g.cosA + dy * g.sinA, v = -dx * g.sinA + dy * g.cosA;
      const eu = u * g.iA, ev = v * g.ib;
      if (eu * eu + ev * ev > 1) continue;
      const i = row + x, D = buf[i];
      if (D === 0) continue;
      const lift = g.p - k * (1 - H[paperIndex(x, y)]);
      if (lift <= 0) continue;
      const nd = D - amount * lift + dither(x, y);
      buf[i] = nd > 0 ? nd : 0;
    }
  }
  return true;
}

/** Plastic eraser: hard clear inside the disc; a one-pixel soft rim (ours). */
export function dabEraser(buf, stride, ox, oy, clip, paper, tool, g, flow) {
  const { x0, x1, y0, y1 } = clipBounds(g, clip);
  if (x0 >= x1 || y0 >= y1) return false;
  const r = g.r, ir = 1 / r, rim = r > 1.5 ? r : 1.5;
  for (let y = y0; y < y1; y++) {
    const dy = y + 0.5 - g.cy;
    const row = (y - oy) * stride - ox;
    for (let x = x0; x < x1; x++) {
      const dx = x + 0.5 - g.cx;
      const rho = Math.sqrt(dx * dx + dy * dy) * ir;
      if (rho >= 1) continue;
      const i = row + x, D = buf[i];
      if (D === 0) continue;
      const keep = (1 - rho) * rim;             // 0 at the edge, ≥1 one pixel in
      buf[i] = keep >= 1 ? 0 : D * (1 - keep) + 0.5;
    }
  }
  return true;
}

/**
 * Smudge (finger). Two passes over the footprint. Weight per pixel is the
 * tip depth minus the pressure sink, gated by the paper (deep valleys are
 * not touched). Pass 1 takes the weighted mean; pass 2 pulls each pixel
 * toward the target. The reference target is the mean (a contact-gated
 * flatten); ours blends in a carried load so graphite travels with the
 * finger out of the patch: load follows the mean at tool.pickup, thins by
 * tool.loss per dab. tool.carry = 0 gives the reference exactly.
 */
export function dabSmudge(buf, stride, ox, oy, clip, paper, tool, g, flow, state) {
  const { x0, x1, y0, y1 } = clipBounds(g, clip);
  if (x0 >= x1 || y0 >= y1 || g.pp <= 0 || g.invD === 0) return false;
  const H = paper.height;
  const sink = 1 - g.pp;
  let sum = 0, wsum = 0;
  for (let y = y0; y < y1; y++) {
    const dy = y + 0.5 - g.cy;
    const row = (y - oy) * stride - ox;
    for (let x = x0; x < x1; x++) {
      const dx = x + 0.5 - g.cx;
      const u = dx * g.cosA + dy * g.sinA, v = -dx * g.sinA + dy * g.cosA;
      const eu = u * g.iA, ev = v * g.ib;
      if (eu * eu + ev * ev > 1) continue;
      const w = tipDepth(g, u, v) - sink + H[paperIndex(x, y)] - 1;
      if (w <= 0) continue;
      sum += w * buf[row + x]; wsum += w;
    }
  }
  if (wsum <= 0) return false;
  const mean = sum / wsum;
  if (!(state.load >= 0)) state.load = mean;
  const carry = tool.carry || 0;
  const target = mean + carry * (state.load - mean);
  const rate = flow * tool.rate;
  for (let y = y0; y < y1; y++) {
    const dy = y + 0.5 - g.cy;
    const row = (y - oy) * stride - ox;
    for (let x = x0; x < x1; x++) {
      const dx = x + 0.5 - g.cx;
      const u = dx * g.cosA + dy * g.sinA, v = -dx * g.sinA + dy * g.cosA;
      const eu = u * g.iA, ev = v * g.ib;
      if (eu * eu + ev * ev > 1) continue;
      let w = tipDepth(g, u, v) - sink + H[paperIndex(x, y)] - 1;
      if (w <= 0) continue;
      w *= rate; if (w > 1) w = 1;
      const i = row + x, D = buf[i];
      const nd = D + w * (target - D) + dither(x, y);
      buf[i] = nd < 0 ? 0 : nd > 255 ? 255 : nd;
    }
  }
  state.load = (state.load + (tool.pickup || 0) * (mean - state.load)) * (tool.loss ?? 1);
  return true;
}

/** Dispatch by tool kind. */
export function rasterDab(buf, stride, ox, oy, clip, paper, tool, g, flow, state) {
  switch (tool.kind) {
    case "pencil": return dabPencil(buf, stride, ox, oy, clip, paper, tool, g, flow);
    case "kneaded": return dabKneaded(buf, stride, ox, oy, clip, paper, tool, g, flow);
    case "eraser": return dabEraser(buf, stride, ox, oy, clip, paper, tool, g, flow);
    case "smudge": return dabSmudge(buf, stride, ox, oy, clip, paper, tool, g, flow, state);
  }
  return false;
}
