// brush.js — graphite pencil, eraser and finger smudge, rasterised per pixel
// into RGBA tiles. Everything that decides the feel lives in the constants below.

// ---------------------------------------------------------------- tunables
export const PAPER_RGB = [252, 251, 248];        // sheet colour (tiles start here)
export const PAPER_SIZE = 512;                   // seamless tooth tile, sheet pixels
export const PAPER_SEED = 1931;                  // same paper every load
export const GRAIN_EDGE = 1.2;                   // tooth range (× the local coverage) over which a hit fades from full flow to nothing; smaller = drier, more binary
export const DITHER = 0.25;                      // per-dab threshold jitter, so overlapping dabs and later passes fill different pixels
export const PRESSURE_GAMMA = 0.85;               // pressure → coverage curve (cover = fill × p^gamma); <1 lifts the mid range
export const SIZE_MIN = 0.6;                     // dab radius at zero pressure, fraction of size
export const SPACING = 0.3;                      // dab step as a fraction of the dab radius
export const RAMP_EVENTS = 10;                   // pressure fades in over this many samples...
export const RAMP_PX = 14;                       // ...or this many sheet px of travel, whichever comes first
export const TILT_DEAD = 0.35;                   // tilt below this fraction counts as upright (altitude > ~58°: a normal grip)
export const TILT_LENGTH = 1.6;                  // flat pencil: dab stretches along the azimuth
export const TILT_WIDTH = 0.5;                   // ...and widens a little
export const TILT_SHIFT = 0.6;                   // ...and moves toward the lead side
export const TILT_LIGHTEN = 0.45;                // ...and covers less of the tooth (side of the lead)
export const TILT_FLOW = 0.3;                    // ...and deposits less per hit
export const ERASER_SIZE = 2.6;                  // eraser radius relative to the pencil size
export const ERASER_FLOW = 0.5;
export const SMUDGE_RADIUS = 22;                 // finger, sheet pixels (fixed)
export const SMUDGE_STRENGTH = 0.6;              // how much of the carried graphite is laid down
export const SMUDGE_PICKUP = 0.5;                // how much the finger picks up again per dab

// size = radius in sheet px at mid pressure; flow = darkness per hit at full coverage (× the local coverage, multiply toward the colour);
// hardness = flat core of the dab (0..1, the rest ramps the coverage down to the rim); fill = how much of
// the tooth the lead covers at full pressure (cover = fill × p^gamma, >1 reaches into the valleys);
// grain = how strongly the tooth breaks the stroke (0 = flat marker, 1 = full paper).
export const PRESETS = {
  '2H': { size: 2.0, flow: 0.14, hardness: 0.65, fill: 1.10, grain: 1.0 },
  'HB': { size: 3.0, flow: 0.26, hardness: 0.70, fill: 1.45, grain: 1.0 },
  '4B': { size: 3.6, flow: 0.36, hardness: 0.65, fill: 1.60, grain: 0.9 },
};
export const DEFAULT_SETTINGS = { size: 1, hardness: null, grain: null, smoothing: 0.2 };

// ---------------------------------------------------------------- paper
function mulberry32(seed) {
  return () => {
    seed = (seed + 0x6D2B79F5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const fade = (t) => t * t * t * (t * (t * 6 - 15) + 10);

// Paper tooth, the height a pixel's fibres stand at: 0 = highest peak (graphite lands first),
// 255 = deepest valley. Rank-normalised so a coverage c darkens exactly a fraction c of pixels.
// The strong octaves sit at 1–2 px: the deposit is particles, not clouds. Wraps at PAPER_SIZE.
// Returns { tooth, dither }: dither is white noise the dab reads at a random offset, so two
// overlapping dabs do not threshold the very same pixels.
export function makePaper() {
  const N = PAPER_SIZE, rnd = mulberry32(PAPER_SEED);
  const acc = new Float32Array(N * N);
  // [cell px, amplitude]
  const octaves = [[32, 0.1], [8, 0.15], [4, 0.3], [2, 0.9], [1, 0.45]];
  for (const [cell, amp] of octaves) {
    if (cell === 1) { for (let i = 0; i < acc.length; i++) acc[i] += (rnd() - 0.5) * amp; continue; }
    const g = N / cell;
    const lattice = new Float32Array(g * g);
    for (let i = 0; i < lattice.length; i++) lattice[i] = rnd();
    for (let y = 0; y < N; y++) {
      const fy = y / cell, iy = Math.floor(fy), ty = fade(fy - iy);
      const r0 = (iy % g) * g, r1 = ((iy + 1) % g) * g;
      for (let x = 0; x < N; x++) {
        const fx = x / cell, ix = Math.floor(fx), tx = fade(fx - ix);
        const c0 = ix % g, c1 = (ix + 1) % g;
        const top = lattice[r0 + c0] + (lattice[r0 + c1] - lattice[r0 + c0]) * tx;
        const bot = lattice[r1 + c0] + (lattice[r1 + c1] - lattice[r1 + c0]) * tx;
        acc[y * N + x] += (top + (bot - top) * ty - 0.5) * amp;
      }
    }
  }
  // rank-normalise to a uniform 0..255 through a 4096-bin histogram
  let lo = Infinity, hi = -Infinity;
  for (let i = 0; i < acc.length; i++) { if (acc[i] < lo) lo = acc[i]; if (acc[i] > hi) hi = acc[i]; }
  const B = 4096, hist = new Uint32Array(B), scale = (B - 1) / (hi - lo);
  for (let i = 0; i < acc.length; i++) hist[((acc[i] - lo) * scale) | 0]++;
  const lut = new Uint8Array(B);
  for (let b = 0, run = 0; b < B; b++) { run += hist[b]; lut[b] = Math.min(255, Math.round((run - hist[b] / 2) / acc.length * 255)); }
  const tooth = new Uint8Array(N * N);
  for (let i = 0; i < acc.length; i++) tooth[i] = lut[((acc[i] - lo) * scale) | 0];
  const dither = new Uint8Array(N * N);
  for (let i = 0; i < dither.length; i++) dither[i] = (rnd() * 256) | 0;
  return { tooth, dither };
}

// ---------------------------------------------------------------- tilt
// Pointer Events spec: altitude π/2 = upright; azimuth 0 = +x, π/2 = +y (down the screen).
export function tiltAngles(e) {
  if (typeof e.altitudeAngle === 'number' && typeof e.azimuthAngle === 'number') {
    return { altitude: e.altitudeAngle, azimuth: e.azimuthAngle };
  }
  const tx = (e.tiltX || 0) * Math.PI / 180, ty = (e.tiltY || 0) * Math.PI / 180;
  if (tx === 0 && ty === 0) return { altitude: Math.PI / 2, azimuth: 0 };
  const tanX = Math.tan(tx), tanY = Math.tan(ty);
  return { altitude: Math.atan2(1, Math.hypot(tanX, tanY)), azimuth: Math.atan2(tanY, tanX) };
}

// ---------------------------------------------------------------- pixel loops
// Calls fn(data, originX, originY, lx0, ly0, lx1, ly1) once per tile overlapping the
// inclusive sheet rect, with the clipped span in tile-local pixels.
function eachTileSpan(sheet, x0, y0, x1, y1, fn) {
  const T = sheet.TILE;
  for (let ty = Math.floor(y0 / T); ty <= Math.floor(y1 / T); ty++) {
    for (let tx = Math.floor(x0 / T); tx <= Math.floor(x1 / T); tx++) {
      const ox = tx * T, oy = ty * T;
      fn(sheet.tile(tx, ty), ox, oy,
        Math.max(0, x0 - ox), Math.max(0, y0 - oy), Math.min(T - 1, x1 - ox), Math.min(T - 1, y1 - oy));
    }
  }
  sheet.markDirty(x0, y0, x1, y1);
}

const smooth01 = (t) => (t <= 0 ? 0 : t >= 1 ? 1 : t * t * (3 - 2 * t));

// One elliptical dab. d = { cx, cy, rx, ry, cos, sin, flow, cover, hardness, grain, colour, erase, dx, dy }
// Graphite lands on a pixel when the lead's coverage there (cover × profile) exceeds the paper
// tooth (+ a little dither); where it lands it darkens by flow, elsewhere nothing. The edge of the
// stroke is where the thinning coverage drops below the tooth, so it is ragged, not a soft ramp.
export function stampDab(sheet, paper, d) {
  const ex = Math.hypot(d.rx * d.cos, d.ry * d.sin), ey = Math.hypot(d.rx * d.sin, d.ry * d.cos);
  const x0 = Math.floor(d.cx - ex), x1 = Math.ceil(d.cx + ex);
  const y0 = Math.floor(d.cy - ey), y1 = Math.ceil(d.cy + ey);
  const N = PAPER_SIZE, M = N - 1, T = sheet.TILE;
  const tooth = paper.tooth, dither = paper.dither, dox = d.dx & M, doy = d.dy & M;
  const [cr, cg, cb] = d.colour, [pr, pg, pb] = PAPER_RGB;
  const invRx = 1 / d.rx, invRy = 1 / d.ry, soft = 1 / Math.max(0.02, 1 - d.hardness), h2 = d.hardness * d.hardness;
  const flow = d.flow, grain = d.grain, erase = d.erase;
  const cover = d.cover * 255, invEdge = 1 / GRAIN_EDGE, dith = DITHER * grain, mid = 127.5 * (1 - grain), flowC = flow / 255;
  const ucos = d.cos * invRx, usin = d.sin * invRx, vcos = d.cos * invRy, vsin = d.sin * invRy;
  eachTileSpan(sheet, x0, y0, x1, y1, (data, ox, oy, lx0, ly0, lx1, ly1) => {
    for (let ly = ly0; ly <= ly1; ly++) {
      const py = oy + ly, dy = py + 0.5 - d.cy, prow = (py & M) * N, drow = ((py + doy) & M) * N;
      const uy = dy * usin, vy = dy * vcos;
      let i = (ly * T + lx0) * 4;
      for (let lx = lx0; lx <= lx1; lx++, i += 4) {
        const px = ox + lx, dx = px + 0.5 - d.cx;
        const u = dx * ucos + uy, v = vy - dx * vsin;
        const r2 = u * u + v * v;
        if (r2 >= 1) continue;
        const profile = r2 < h2 ? 1 : smooth01((1 - Math.sqrt(r2)) * soft);
        if (erase) {
          const a = flow * profile;
          data[i] += (pr - data[i]) * a;
          data[i + 1] += (pg - data[i + 1]) * a;
          data[i + 2] += (pb - data[i + 2]) * a;
          continue;
        }
        // the fibre height this pixel presents to the lead (grain flattens it toward the middle), against
        // the lead's coverage here: peaks under the core get full flow, the rim and the valleys get less or nothing
        const t = mid + tooth[prow + (px & M)] * grain + (dither[drow + ((px + dox) & M)] - 127.5) * dith;
        const c = cover * profile;
        const s = (c - t) * invEdge / c + 0.5;
        if (s <= 0) continue;
        const a = (s >= 1 ? flowC : flowC * s * s * (3 - 2 * s)) * c;
        data[i] *= 1 - a * (1 - cr);
        data[i + 1] *= 1 - a * (1 - cg);
        data[i + 2] *= 1 - a * (1 - cb);
      }
    }
  });
}

// ---------------------------------------------------------------- pencil / eraser stroke
export class PencilStroke {
  constructor(sheet, paper, { preset, settings, colour, erase }) {
    this.sheet = sheet; this.paper = paper;
    this.p = PRESETS[preset]; this.s = settings; this.colour = colour; this.erase = erase;
    this.last = null; this.n = 0; this.carry = 0; this.dabs = 0; this.travel = 0;
    this.smooth = null;
    this.rng = mulberry32((Math.random() * 2 ** 31) | 0);   // dither offsets, one per dab
  }

  // x, y in sheet px; pressure 0..1; altitude/azimuth radians
  addSample(x, y, pressure, altitude, azimuth) {
    this.n++;
    const k = 1 - Math.min(0.95, this.s.smoothing);
    if (!this.smooth) this.smooth = { x, y };
    else { this.smooth.x += (x - this.smooth.x) * k; this.smooth.y += (y - this.smooth.y) * k; }
    const cur = { x: this.smooth.x, y: this.smooth.y, p: pressure, alt: altitude, az: azimuth };
    // touchdown ramp: pressure fades in over the first samples, or the first px of travel when
    // samples are sparse (mouse, dropped events), so a fast first stroke is not faint all along
    const rampN = Math.min(1, this.n / RAMP_EVENTS);
    if (!this.last) { this.dab(cur, rampN); this.last = cur; return; }
    const dist = Math.hypot(cur.x - this.last.x, cur.y - this.last.y);
    const step = Math.max(0.35, SPACING * this.radius(cur.p));
    let t = this.carry / dist;
    const a = this.last;
    while (t <= 1 && dist > 0) {
      const ramp = Math.max(rampN, Math.min(1, (this.travel + t * dist) / RAMP_PX));
      this.dab({ x: a.x + (cur.x - a.x) * t, y: a.y + (cur.y - a.y) * t,
        p: a.p + (cur.p - a.p) * t, alt: a.alt + (cur.alt - a.alt) * t, az: lerpAngle(a.az, cur.az, t) }, ramp);
      t += step / dist;
    }
    this.carry = dist > 0 ? (t - 1) * dist : this.carry;
    this.travel += dist;
    this.last = cur;
  }

  radius(p) {
    const r = this.p.size * this.s.size * (SIZE_MIN + (1 - SIZE_MIN) * p);
    return this.erase ? r * ERASER_SIZE : r;
  }

  dab(q, ramp = 1) {
    const t = Math.max(0, Math.min(1, ((1 - q.alt / (Math.PI / 2)) - TILT_DEAD) / (1 - TILT_DEAD)));
    const p = Math.max(0, Math.min(1, q.p)) * ramp;
    const r = this.radius(p), pg = Math.pow(p, PRESSURE_GAMMA);
    const cos = Math.cos(q.az), sin = Math.sin(q.az), shift = r * TILT_SHIFT * t;
    const hardness = this.s.hardness ?? this.p.hardness;
    stampDab(this.sheet, this.paper, {
      cx: q.x + cos * shift, cy: q.y + sin * shift,
      rx: r * (1 + TILT_LENGTH * t), ry: r * (1 + TILT_WIDTH * t), cos, sin,
      flow: this.erase ? ERASER_FLOW : this.p.flow * (1 - TILT_FLOW * t),
      cover: pg * this.p.fill * (1 - TILT_LIGHTEN * t),
      hardness: this.erase ? Math.min(hardness, 0.5) : hardness,
      grain: this.s.grain ?? this.p.grain, colour: this.colour, erase: this.erase,
      dx: (this.rng() * PAPER_SIZE) | 0, dy: (this.rng() * PAPER_SIZE) | 0,
    });
    this.dabs++;
  }
}

function lerpAngle(a, b, t) {
  let d = b - a;
  while (d > Math.PI) d -= 2 * Math.PI;
  while (d < -Math.PI) d += 2 * Math.PI;
  return a + d * t;
}

// ---------------------------------------------------------------- finger smudge
export class SmudgeStroke {
  constructor(sheet) {
    this.sheet = sheet; this.R = SMUDGE_RADIUS; this.last = null; this.dabs = 0; this.carry = 0;
    const side = this.R * 2 + 1;
    this.buf = new Float32Array(side * side * 3);    // the graphite carried on the finger, RGB
    this.tmp = new Float32Array(side * side * 3);
  }

  addSample(x, y) {
    if (!this.last) { this.pickup(x, y, 1); this.last = { x, y }; return; }
    const dist = Math.hypot(x - this.last.x, y - this.last.y), step = Math.max(1, this.R * SMUDGE_STEP);
    let t = this.carry / dist;
    while (t <= 1 && dist > 0) {
      this.apply(this.last.x + (x - this.last.x) * t, this.last.y + (y - this.last.y) * t);
      t += step / dist;
    }
    this.carry = dist > 0 ? (t - 1) * dist : this.carry;
    this.last = { x, y };
  }

  // visit every pixel of the finger disk: fn(data, i, bufIndex, weight)
  disk(cx, cy, fn) {
    const R = this.R, side = R * 2 + 1, bx = Math.round(cx) - R, by = Math.round(cy) - R, T = this.sheet.TILE;
    eachTileSpan(this.sheet, bx, by, bx + side - 1, by + side - 1, (data, ox, oy, lx0, ly0, lx1, ly1) => {
      for (let ly = ly0; ly <= ly1; ly++) {
        const py = oy + ly, dy = py - by - R;
        for (let lx = lx0; lx <= lx1; lx++) {
          const px = ox + lx, dx = px - bx - R, q = (dx * dx + dy * dy) / (R * R);
          if (q >= 1) continue;
          const wgt = (1 - q) * (1 - q);
          fn(data, (ly * T + lx) * 4, ((py - by) * side + (px - bx)) * 3, wgt);
        }
      }
    });
  }

  pickup(cx, cy, amount) {
    const buf = this.buf;
    this.disk(cx, cy, (data, i, b, wgt) => {
      const m = amount === 1 ? 1 : amount * wgt;
      buf[b] += (data[i] - buf[b]) * m;
      buf[b + 1] += (data[i + 1] - buf[b + 1]) * m;
      buf[b + 2] += (data[i + 2] - buf[b + 2]) * m;
    });
  }

  apply(cx, cy) {
    const buf = this.buf;
    this.disk(cx, cy, (data, i, b, wgt) => {
      const f = SMUDGE_STRENGTH * wgt;
      data[i] += (buf[b] - data[i]) * f;
      data[i + 1] += (buf[b + 1] - data[i + 1]) * f;
      data[i + 2] += (buf[b + 2] - data[i + 2]) * f;
      const m = SMUDGE_PICKUP * wgt;
      buf[b] += (data[i] - buf[b]) * m;
      buf[b + 1] += (data[i + 1] - buf[b + 1]) * m;
      buf[b + 2] += (data[i + 2] - buf[b + 2]) * m;
    });
    this.soften();
    this.dabs++;
  }

  // separable 3-tap blur of the carried graphite, so it smears instead of re-stamping its pattern
  soften() {
    const k = SMUDGE_BLUR;
    if (k <= 0) return;
    const side = this.R * 2 + 1, w = side * 3, buf = this.buf, tmp = this.tmp, c = 1 - k, e = k / 2;
    for (let y = 0; y < side; y++) {
      const row = y * w;
      for (let x = 0; x < side; x++) {
        const i = row + x * 3, l = x > 0 ? i - 3 : i, r = x < side - 1 ? i + 3 : i;
        tmp[i] = buf[i] * c + (buf[l] + buf[r]) * e;
        tmp[i + 1] = buf[i + 1] * c + (buf[l + 1] + buf[r + 1]) * e;
        tmp[i + 2] = buf[i + 2] * c + (buf[l + 2] + buf[r + 2]) * e;
      }
    }
    for (let y = 0; y < side; y++) {
      const row = y * w, up = y > 0 ? row - w : row, dn = y < side - 1 ? row + w : row;
      for (let i = row, u = up, d = dn; i < row + w; i++, u++, d++) buf[i] = tmp[i] * c + (tmp[u] + tmp[d]) * e;
    }
  }
}
