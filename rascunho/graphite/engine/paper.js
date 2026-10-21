// paper.js — the sheet's tooth as a tileable height field.
//
// A pencil mark is the lead meeting the peaks of the paper. Everything that
// makes graphite look like graphite on a screen comes from reading this map
// per pixel while a dab is written. The map is fixed to sheet coordinates, so
// two strokes crossing the same spot see the same grain and build up there.
//
// Height is Float32 in [0,1], 1 = tooth top (touched first, full deposit),
// 0 = deepest pit (only a soft lead pressed hard reaches it). Period is a
// power of two so lookups are a mask, not a modulo.
//
// Recipe (research/14-paper-textures.md): seeded white noise, blurred with
// wrap-around at several scales (so the tile is seamless), summed with
// weights, then rank-mapped onto a target tone distribution. Measured from
// the reference app: its default "noise" is plain i.i.d. white noise with
// half the pixels at the top; its "paper" is a 1/f mottle; its scanned
// papers are band-limited bumps of 0.3–1.1 mm with 10–30 % clipped tops.

export const PAPER_SIZE = 512;        // period in sheet pixels (≈ 49 mm at 264 ppi)
const MASK = PAPER_SIZE - 1;
const SHIFT = 9;                       // log2(PAPER_SIZE)
const N = PAPER_SIZE * PAPER_SIZE;

function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Three box blurs ≈ a gaussian; running sums with wrap, O(N) per pass.
function boxPass(src, dst, n, radius, horizontal) {
  const w = 2 * radius + 1, inv = 1 / w;
  for (let line = 0; line < n; line++) {
    const base = horizontal ? line * n : line;
    const step = horizontal ? 1 : n;
    let acc = 0;
    for (let i = -radius; i <= radius; i++) acc += src[base + (((i % n) + n) % n) * step];
    for (let i = 0; i < n; i++) {
      dst[base + i * step] = acc * inv;
      const out = ((i - radius) % n + n) % n, inn = (i + radius + 1) % n;
      acc += src[base + inn * step] - src[base + out * step];
    }
  }
}
function blurWrap(buf, tmp, n, sigmaX, sigmaY) {
  // box width for 3 passes ≈ sqrt(12σ²/3 + 1)
  const rx = Math.max(0, Math.round((Math.sqrt(4 * sigmaX * sigmaX + 1) - 1) / 2));
  const ry = Math.max(0, Math.round((Math.sqrt(4 * sigmaY * sigmaY + 1) - 1) / 2));
  for (let k = 0; k < 3; k++) {
    if (rx > 0) { boxPass(buf, tmp, n, rx, true); buf.set(tmp); }
    if (ry > 0) { boxPass(buf, tmp, n, ry, false); buf.set(tmp); }
  }
}

/** octaves: [sigmaX, sigmaY, amplitude]; returns zero-mean unit-ish field */
function octaveField(octaves, seed) {
  const rnd = mulberry32(seed);
  const h = new Float32Array(N), a = new Float32Array(N), tmp = new Float32Array(N);
  for (const [sx, sy, amp] of octaves) {
    for (let i = 0; i < N; i++) a[i] = rnd() - 0.5;
    if (sx > 0 || sy > 0) blurWrap(a, tmp, PAPER_SIZE, sx, sy);
    let m = 0, v = 0;
    for (let i = 0; i < N; i++) { m += a[i]; v += a[i] * a[i]; }
    m /= N; const sd = Math.sqrt(v / N - m * m) || 1;
    for (let i = 0; i < N; i++) h[i] += amp * (a[i] - m) / sd;
  }
  return h;
}

// Rank of every pixel in [0,1): sort a copy, binary-search each value.
function ranks(h) {
  const sorted = Float32Array.from(h).sort();
  const q = new Float32Array(N);
  for (let i = 0; i < N; i++) {
    let lo = 0, hi = N;
    const v = h[i];
    while (lo < hi) { const mid = (lo + hi) >>> 1; if (sorted[mid] < v) lo = mid + 1; else hi = mid; }
    q[i] = lo / N;
  }
  return q;
}

// Tone tables measured from the reference app (level 0..255, probability).
const TONES = {
  noise: {
    L: [108, 116, 124, 132, 140, 148, 156, 164, 172, 180, 188, 196, 204, 212, 220, 228, 236, 244, 252],
    P: [.068, .0076, .0099, .0109, .0129, .0157, .0168, .0193, .0203, .022, .0273, .0267, .0334, .0396, .0403, .0432, .0386, .0379, .5096],
  },
};
function toneTable(q, { L, P }) {
  const cum = []; let c = 0; const tot = P.reduce((s, p) => s + p, 0);
  for (const p of P) { c += p / tot; cum.push(c); }
  const out = new Float32Array(N);
  for (let i = 0; i < N; i++) {
    let l = 0; while (l < cum.length - 1 && q[i] >= cum[l]) l++;
    out[i] = L[l] / 255;
  }
  return out;
}

const KINDS = {
  // The reference default: i.i.d. salt, 51 % of pixels at the top.
  noise: { octaves: [[0, 0, 1]], tone: (q) => null, table: TONES.noise },
  // The reference "paper": 1/f mottle, here continuous instead of 13 levels.
  // Target: ~gaussian, mean 0.71, sd 0.15, clipped at 1.
  paper: {
    octaves: [[0, 0, .12], [.58, .45, .85], [1.1, 1, .15], [2.2, 2, .28], [4.4, 4, .2], [8.8, 8, .2], [17, 16, .17]],
    tone: (q) => Math.min(1, 0.71 + 0.15 * probit(q)),
  },
  // Ours: band-limited bumps ≈ 0.4 mm (σ 3×2 px, a little directional) with
  // a clipped plateau (top 22 % at 1), a 1 px octave and fine salt. Reads as
  // a drawing paper: light strokes catch the plateau islands, pressure fills
  // the pits.
  tooth: {
    octaves: [[0, 0, .30], [0.7, 0.6, .35], [3.0, 2.0, 1.0], [6, 4.5, .25], [14, 12, .08]],
    // bright field with a tail of pits: bottom 5 % fall to 0.2, most sit 0.6–1
    tone: (q) => (q >= 0.78 ? 1 : 0.2 + 0.8 * Math.pow(q / 0.78, 0.45)),
  },
  // Hot press: almost no tooth, faint salt.
  smooth: {
    octaves: [[0, 0, .5], [1.2, 1.2, 1.0], [5, 5, .3]],
    tone: (q) => 0.6 + 0.4 * q,
  },
};

// inverse normal CDF (Acklam), good to 1e-9
function probit(p) {
  if (p <= 0) return -6; if (p >= 1) return 6;
  const a = [-3.969683028665376e1, 2.209460984245205e2, -2.759285104469687e2, 1.38357751867269e2, -3.066479806614716e1, 2.506628277459239];
  const b = [-5.447609879822406e1, 1.615858368580409e2, -1.556989798598866e2, 6.680131188771972e1, -1.328068155288572e1];
  const c = [-7.784894002430293e-3, -3.223964580411365e-1, -2.400758277161838, -2.549732539343734, 4.374664141464968, 2.938163982698783];
  const d = [7.784695709041462e-3, 3.224671290700398e-1, 2.445134137142996, 3.754408661907416];
  const pl = 0.02425, ph = 1 - pl;
  let q, r;
  if (p < pl) { q = Math.sqrt(-2 * Math.log(p)); return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1); }
  if (p > ph) { q = Math.sqrt(-2 * Math.log(1 - p)); return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1); }
  q = p - 0.5; r = q * q;
  return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1);
}

/**
 * Procedural paper. kind: "tooth" (default) | "noise" | "paper" | "smooth".
 * Returns { height: Float32Array(PAPER_SIZE²), size, kind, mean, contrast, plateau }.
 */
export function makePaper(kind = "tooth", seed = 7) {
  const spec = KINDS[kind] || KINDS.tooth;
  const q = ranks(octaveField(spec.octaves, seed));
  let h;
  if (spec.table) h = toneTable(q, spec.table);
  else { h = new Float32Array(N); for (let i = 0; i < N; i++) h[i] = spec.tone(q[i]); }
  return stats(h, kind);
}

/** Paper from a greyscale 8-bit image, PAPER_SIZE² (own scans; make them tileable first). */
export function paperFromGrey(u8, kind = "scan") {
  const h = new Float32Array(N);
  for (let i = 0; i < N; i++) h[i] = u8[i] / 255;
  return stats(h, kind);
}

function stats(h, kind) {
  let sum = 0, sum2 = 0, top = 0;
  for (let i = 0; i < N; i++) { sum += h[i]; sum2 += h[i] * h[i]; if (h[i] >= 0.999) top++; }
  const mean = sum / N;
  return { height: h, size: PAPER_SIZE, kind, mean, contrast: Math.sqrt(sum2 / N - mean * mean), plateau: top / N };
}

/** Index into the height field for sheet pixel (x, y), any sign. */
export function paperIndex(x, y) {
  return ((y & MASK) << SHIFT) | (x & MASK);
}

export const PAPER_KINDS = Object.keys(KINDS);
