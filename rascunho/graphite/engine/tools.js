// tools.js — what each tool is, as numbers.
//
// Every tool is a plain frozen object the stroke conditioner and the dab
// kernels read. Nothing here is code; change a number, change the feel.
//
// Units. Sizes are in "document pixels", the reference app's unit: 4 per
// device pixel on the iPad (the sheet is supersampled 4×, see engine.js),
// so size 16 is a 2 CSS px line. Pressure exponents, floors and rates are
// 0..1 or plain multipliers. Lengths in px are document pixels.
//
// The pencil law is the one recovered from the reference (research/11):
//   radius = size · (1 + p') / 4,  p' = pressure ^ k,  k from the hardness
//   slider (40 → 0.625); darkness floors 4B 0 · HB 30/255 · 2H 137/255.
// The other grades are our extrapolation along the same scale.

/** hardness slider 0–100 → pressure exponent k (50 = linear, lower = softer feel) */
export function hardnessToK(h) {
  return h >= 50 ? 1 + 3 * (h - 50) / 50 : 1 / (1 + 3 * (50 - h) / 50);
}

// Shared by every tool: how the stroke conditioner treats the input.
const INPUT = {
  spacing: 0.2,       // dab spacing, fraction of the minor radius (whole px, min 1)
  correction: 8,      // moving-average window = 2c+1 sub-samples (reference default 8)
  rampPx: 0,          // pressure ramp from touchdown over this many px (0 = none)
};

export const PENCIL_DEFAULTS = {
  ...INPUT,
  kind: "pencil",
  size: 16,           // full width at full pressure (radius = size·(1+p')/4)
  hardness: 40,       // 0–100; p' = p^k, k = hardnessToK(hardness)
  floor: 0,           // lightness this grade cannot go below (0 = black, 0.54 = 2H)
  rate: 1,            // gain per dab (1 = reference)
  toothStrength: 1,   // how much the paper subtracts (0 = marker)
  toothCatch: 6,      // tilted tip catches on the tooth: push-back in px at light pressure
  flatReach: 600,     // length of the lead side when lying flat (reference 600)
  rampPx: 10,
  color: [38, 38, 44],
};

function pencil(name, over) {
  const t = { ...PENCIL_DEFAULTS, name, ...over };
  t.k = hardnessToK(t.hardness);
  return Object.freeze(t);
}

export const TOOLS = Object.freeze({
  // Hard grades: light, fine, crisp; the floor keeps them from going dark.
  "4H": pencil("4H", { size: 14, hardness: 60, floor: 0.66, color: [70, 72, 80] }),
  "2H": pencil("2H", { size: 15, hardness: 50, floor: 0.537, color: [58, 60, 68] }),
  // The everyday pencil.
  "HB": pencil("HB", { size: 16, hardness: 40, floor: 0.118 }),
  "2B": pencil("2B", { size: 16, hardness: 40, floor: 0.04 }),
  // Soft grades: black, a little wider, light touch already marks.
  "4B": pencil("4B", { size: 16, hardness: 40, floor: 0, color: [30, 30, 34] }),
  "6B": pencil("6B", { size: 19, hardness: 36, floor: 0, color: [26, 26, 30] }),

  // Plastic eraser. Reference: a hard capsule of diameter p^k·size, default
  // 100, no texture. Ours: a one-pixel soft rim, a width that only grows
  // 55→100 % with pressure, and a real eraser's size (240 ≈ 4 mm on the
  // iPad at medium pressure).
  eraser: Object.freeze({
    ...INPUT, kind: "eraser", name: "eraser",
    size: 240, hardness: 50, k: 1, correction: 6,
  }),

  // Kneaded eraser. Reference: the pencil tip run backwards, radius size/4,
  // flat coverage = pressure, lifts a fixed amount, peaks first, tilt
  // ellipse below 45°. Ours: default 320 (radius 80 ≈ 5 mm).
  kneaded: Object.freeze({
    ...INPUT, kind: "kneaded", name: "kneaded",
    size: 320, rate: 1, toothStrength: 1, flatReach: 600,
  }),

  // Finger smudge. Reference ("Smudge1"): contact-gated flatten toward the
  // footprint mean, radius size/2, pressure sinks the tip but does not
  // change the size. Ours: carry/pickup/loss let graphite travel with the
  // finger; rate < 1 softens each pass.
  smudge: Object.freeze({
    ...INPUT, kind: "smudge", name: "smudge",
    size: 100, hardness: 50, k: 1, rate: 0.6, flatReach: 600, correction: 10,
    carry: 0.2,          // share of the carried load in the target (0 = reference)
    pickup: 0.3,         // how fast the load follows what is under the finger
    loss: 0.99,          // load kept per dab (graphite thins as it spreads)
  }),
});

export const PENCIL_GRADES = ["4H", "2H", "HB", "2B", "4B", "6B"];
