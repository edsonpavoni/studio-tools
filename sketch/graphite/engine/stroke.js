// stroke.js — from pointer samples to dabs.
//
// A Stroke takes raw samples (x, y, pressure, altitude, azimuth), conditions
// them, and emits dabs at a fixed spacing along the path with pressure and
// tilt interpolated between samples. Rendering is delegated to a
// `write(geometry, flow, state)` callback so the same stroke logic drives a
// flat buffer, a tiled sheet, or a test harness.
//
// Conditioning (research/10, the reference pipeline, our variations noted):
//  1. sub-sampling: each pointer event becomes 4 points on a quadratic curve
//     through the last three raw points, pressure linear between the last two
//  2. correction: a moving average over 2·correction+1 sub-samples of x, y
//     and pressure (default 8 → 17 samples ≈ 4 events); tilt from the middle
//     of the window
//  3. spacing: one dab every max(1, floor(tool.spacing × minor radius)) px,
//     the reference's whole-pixel rule (small tips pack dabs denser)
//  4. start: a touchdown ramp over tool.rampPx (ours; the reference host ramps
//     over 10 events on iOS); a tap still leaves one dab (ours)
//  5. end: pressure 0 is fed through the window, so the stroke tapers out
//     over one window length and the smoothed position catches up with the pen

import { dabGeometry } from "./dab.js";

const TAU = Math.PI * 2;
const SUBSAMPLES = 4;

export class Stroke {
  /**
   * @param tool   a tool object (tools.js)
   * @param write  (geometry, flow, state) => void, called per dab
   * @param opts   { correction: 0..99 (window = 2c+1), spacing, paper }
   */
  constructor(tool, write, opts = {}) {
    this.tool = tool;
    this.write = write;
    this.paper = opts.paper || null;
    this.spacing = opts.spacing ?? tool.spacing;
    const corr = Math.max(0, Math.min(99, opts.correction ?? tool.correction ?? 8));
    this.win = 2 * corr + 1;
    this.hist = new Float64Array(this.win * 5);   // ring of [x, y, p, alt, az]
    this.head = 0; this.count = 0;
    this.sumX = 0; this.sumY = 0; this.sumP = 0;
    this.raw = [];                  // last 3 raw points
    this.state = { load: NaN };     // smudge carry
    this.started = false;
    this.dabs = 0;
    this.travel = 0;                // distance since touchdown
    this.sx = 0; this.sy = 0; this.sp = 0; this.salt = Math.PI / 2; this.saz = 0;  // last smoothed
    this.carry = 0;                 // leftover distance to the next dab
  }

  /** First sample. Fills the window with it and lays one dab (a tap marks). */
  begin(x, y, pressure, altitude = Math.PI / 2, azimuth = 0) {
    this.started = true;
    this.raw = [[x, y, pressure, altitude, azimuth]];
    this.head = 0; this.count = 0; this.sumX = this.sumY = this.sumP = 0;
    for (let i = 0; i < this.win; i++) this.#push(x, y, pressure, altitude, azimuth);
    this.sx = x; this.sy = y; this.sp = pressure; this.salt = altitude; this.saz = azimuth;
    this.carry = 0; this.travel = 0; this.dabs = 0;
    this.state.load = NaN;
    this.#dab(x, y, this.#ramped(pressure), altitude, azimuth);
  }

  /** Subsequent samples. Returns the number of dabs emitted. */
  move(x, y, pressure, altitude = Math.PI / 2, azimuth = 0) {
    if (!this.started) { this.begin(x, y, pressure, altitude, azimuth); return 1; }
    const raw = this.raw;
    raw.push([x, y, pressure, altitude, azimuth]);
    if (raw.length > 3) raw.shift();
    let n = 0;
    if (raw.length < 3) {
      const [px, py, pp] = raw[0];
      for (let i = 1; i <= SUBSAMPLES; i++) {
        const t = i / SUBSAMPLES;
        n += this.#feed(px + (x - px) * t, py + (y - py) * t, pp + (pressure - pp) * t, altitude, azimuth);
      }
      return n;
    }
    // quadratic through the last three points: from mid(p0,p1) to mid(p1,p2), control p1
    const [p0, p1, p2] = raw;
    const ax = (p0[0] + p1[0]) / 2, ay = (p0[1] + p1[1]) / 2;
    const bx = (p1[0] + p2[0]) / 2, by = (p1[1] + p2[1]) / 2;
    for (let i = 1; i <= SUBSAMPLES; i++) {
      const t = i / SUBSAMPLES, u = 1 - t;
      const qx = u * u * ax + 2 * u * t * p1[0] + t * t * bx;
      const qy = u * u * ay + 2 * u * t * p1[1] + t * t * by;
      n += this.#feed(qx, qy, p1[2] + (p2[2] - p1[2]) * t, altitude, azimuth);
    }
    return n;
  }

  /** Lift. Feeds zero pressure through the window: taper + catch-up. */
  end(x, y, pressure = 0, altitude = Math.PI / 2, azimuth = 0) {
    if (!this.started) return 0;
    let n = 0;
    for (let i = 0; i < this.win; i++) n += this.#feed(x, y, 0, altitude, azimuth);
    this.started = false;
    return n;
  }

  // one sub-sample through the moving average, then dabs along the smoothed segment
  #feed(x, y, p, alt, az) {
    this.#push(x, y, p, alt, az);
    const nx = this.sumX / this.win, ny = this.sumY / this.win, np = this.sumP / this.win;
    // tilt from the middle of the window
    const mid = ((this.head - 1 - (this.win >> 1)) % this.win + this.win) % this.win;
    const nalt = this.hist[mid * 5 + 3], naz = this.hist[mid * 5 + 4];
    let daz = naz - this.saz; daz -= Math.round(daz / TAU) * TAU;

    const dx = nx - this.sx, dy = ny - this.sy;
    const dist = Math.sqrt(dx * dx + dy * dy);
    let n = 0;
    if (dist > 0) {
      let t = 0;
      const p0 = this.sp, a0 = this.salt, z0 = this.saz;
      while (true) {
        const r = this.#radiusAt(p0 + (np - p0) * t);
        // whole-pixel step like the reference: small radii pack dabs denser
        const step = Math.max(1, Math.floor(this.spacing * r));
        const need = step - this.carry;
        if (dist * (1 - t) < need) { this.carry += dist * (1 - t); break; }
        t += need / dist;
        this.carry = 0;
        const pr = p0 + (np - p0) * t;
        this.travel += need;
        if (pr > 0.002) this.#dab(this.sx + dx * t, this.sy + dy * t, this.#ramped(pr), a0 + (nalt - a0) * t, z0 + daz * t);
        n++;
      }
    }
    this.sx = nx; this.sy = ny; this.sp = np; this.salt = nalt; this.saz = this.saz + daz;
    return n;
  }

  #push(x, y, p, alt, az) {
    const h = this.hist, i = this.head * 5;
    if (this.count === this.win) { this.sumX -= h[i]; this.sumY -= h[i + 1]; this.sumP -= h[i + 2]; }
    else this.count++;
    h[i] = x; h[i + 1] = y; h[i + 2] = p; h[i + 3] = alt; h[i + 4] = az;
    this.sumX += x; this.sumY += y; this.sumP += p;
    this.head = (this.head + 1) % this.win;
  }

  // minor radius of the footprint at pressure p (spacing is a fraction of it)
  #radiusAt(p) {
    const t = this.tool, q = p < 0 ? 0 : p > 1 ? 1 : p;
    switch (t.kind) {
      case "pencil": return t.size * (1 + Math.pow(q, t.k)) / 4;
      case "smudge": return Math.max(t.size * 0.5, 2);
      case "kneaded": return Math.max(t.size, 2) * 0.25;
      default: return Math.max(t.size * (0.55 + 0.45 * Math.pow(q, t.k || 1)) * 0.5, 0.35);
    }
  }

  #ramped(p) {
    const r = this.tool.rampPx;
    if (!r || this.travel >= r) return p;
    return p * (0.25 + 0.75 * this.travel / r);
  }

  #dab(x, y, p, alt, az) {
    const g = dabGeometry(this.tool, x, y, p, alt, az, this.paper);
    const flow = 1;                      // gain per dab as the reference (spacing 0.2 of the radius)
    this.write(g, flow, this.state);
    this.dabs++;
  }
}

/** Pointer Events tilt (degrees) → altitude/azimuth (radians). */
export function tiltToSpherical(tiltX, tiltY) {
  const tx = (tiltX * Math.PI) / 180, ty = (tiltY * Math.PI) / 180;
  if (tx === 0 && ty === 0) return { altitude: Math.PI / 2, azimuth: 0 };
  const azimuth = Math.atan2(Math.tan(ty), Math.tan(tx));
  const tanAlt = 1 / Math.sqrt(Math.tan(tx) ** 2 + Math.tan(ty) ** 2);
  return { altitude: Math.atan(tanAlt), azimuth };
}
