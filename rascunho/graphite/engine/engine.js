// engine.js — a sheet: density buffer, paper, tools, strokes, undo, colour.
//
// Public surface (everything else in engine/ is internal):
//
//   const eng = createEngine({ width, height, paper: "noise" | "tooth" | "paper" | "smooth" | Uint8Array });
//   eng.setTool("HB" | tool, { size: 24 })           → the tool in use (overrides merged in)
//   eng.setColor([r, g, b])                          → graphite colour for display
//   eng.strokeBegin(x, y, pressure, altitude, azimuth)
//   eng.strokeMove(...);  eng.strokeEnd(...)         → each returns a dirty rect or null
//   eng.undo(); eng.redo(); eng.clear()              → dirty rect or null
//   eng.blitDown(rect, rgba, rgbaWidth, ss)          → downsample ss× into a screen buffer
//   eng.toRGBA(rect, out?, full?)                    → 1:1 RGBA (tests, exports)
//   eng.density, eng.paper, eng.width, eng.height    → read-only please
//
// Coordinates are sheet pixels, origin top-left. The sheet is meant to be
// supersampled: the reference draws into a document 4× the device pixels
// and shows it fitted (research/13), which is what makes a pencil line thin
// and tonal; blitDown does that averaging for a dirty rect. The sheet here
// is one flat buffer; an unbounded tiled sheet can reuse dab.js/stroke.js
// directly, the kernels take a buffer, stride and origin.
// Undo is tile-granular: the first time a stroke touches a 64 px tile, the
// tile is copied; undo restores the copies. Memory stays proportional to
// what was drawn, not to the sheet.

import { makePaper, paperFromGrey } from "./paper.js";
import { TOOLS } from "./tools.js";
import { rasterDab } from "./dab.js";
import { Stroke } from "./stroke.js";

const TILE = 64;

export function createEngine({ width, height, paper = "noise", seed = 7, undoDepth = 40 } = {}) {
  const W = width | 0, Hh = height | 0;
  const density = new Uint8Array(W * Hh);
  const sheetPaper = typeof paper === "string" ? makePaper(paper, seed)
    : paper.height ? paper : paperFromGrey(paper);
  const clip = { x0: 0, y0: 0, x1: W, y1: Hh };
  const tilesX = Math.ceil(W / TILE);

  let tool = TOOLS.HB;
  let color = tool.color;
  let stroke = null;
  let dirty = null;                 // dirty rect of the current call
  let touched = null;               // Map tileId → Uint8Array copy (before)
  const undoStack = [], redoStack = [];

  // LUT: density → channel value, for the current colour. Density is linear
  // light; the screen gets a 1/2.2 encode (research/11 §7), which keeps light
  // strokes light.
  const lut = new Uint8Array(256 * 3);
  function buildLut() {
    for (let d = 0; d < 256; d++) {
      const dark = 1 - Math.pow(1 - d / 255, 1 / 2.2);
      for (let c = 0; c < 3; c++) lut[d * 3 + c] = Math.round(255 - (255 - color[c]) * dark);
    }
  }
  buildLut();

  function snapshotTile(tx, ty) {
    const id = ty * tilesX + tx;
    if (touched.has(id)) return;
    const copy = new Uint8Array(TILE * TILE);
    const x0 = tx * TILE, y0 = ty * TILE;
    const w = Math.min(TILE, W - x0), h = Math.min(TILE, Hh - y0);
    for (let y = 0; y < h; y++) copy.set(density.subarray((y0 + y) * W + x0, (y0 + y) * W + x0 + w), y * TILE);
    touched.set(id, copy);
  }
  function restoreTiles(map) {
    const inverse = new Map();
    for (const [id, copy] of map) {
      const tx = id % tilesX, ty = (id / tilesX) | 0;
      const x0 = tx * TILE, y0 = ty * TILE;
      const w = Math.min(TILE, W - x0), h = Math.min(TILE, Hh - y0);
      const cur = new Uint8Array(TILE * TILE);
      for (let y = 0; y < h; y++) {
        const off = (y0 + y) * W + x0;
        cur.set(density.subarray(off, off + w), y * TILE);
        density.set(copy.subarray(y * TILE, y * TILE + w), off);
      }
      inverse.set(id, cur);
      growDirty(x0, y0, x0 + w, y0 + h);
    }
    return inverse;
  }
  function growDirty(x0, y0, x1, y1) {
    if (!dirty) dirty = { x0, y0, x1, y1 };
    else {
      if (x0 < dirty.x0) dirty.x0 = x0; if (y0 < dirty.y0) dirty.y0 = y0;
      if (x1 > dirty.x1) dirty.x1 = x1; if (y1 > dirty.y1) dirty.y1 = y1;
    }
  }

  // per-dab write: snapshot tiles, rasterise, grow dirty rect
  function write(g, flow, state) {
    const ex = g.A + 1, ey = g.A + 1;   // conservative
    const x0 = Math.max(0, Math.floor(g.cx - ex)), x1 = Math.min(W, Math.ceil(g.cx + ex) + 1);
    const y0 = Math.max(0, Math.floor(g.cy - ey)), y1 = Math.min(Hh, Math.ceil(g.cy + ey) + 1);
    if (x0 >= x1 || y0 >= y1) return;
    for (let ty = (y0 / TILE) | 0; ty <= ((y1 - 1) / TILE) | 0; ty++)
      for (let tx = (x0 / TILE) | 0; tx <= ((x1 - 1) / TILE) | 0; tx++) snapshotTile(tx, ty);
    if (rasterDab(density, W, 0, 0, clip, sheetPaper, tool, g, flow, state)) growDirty(x0, y0, x1, y1);
  }

  function takeDirty() { const d = dirty; dirty = null; return d; }

  const api = {
    width: W, height: Hh, density, paper: sheetPaper,
    get tool() { return tool; },
    get color() { return color; },

    /** name from TOOLS, or a tool object; optional overrides merged in */
    setTool(t, over) {
      const base = typeof t === "string" ? TOOLS[t] : t;
      if (!base) throw new Error("unknown tool " + t);
      tool = over ? Object.freeze({ ...base, ...over }) : base;
      return tool;
    },
    /** colour of the graphite for display, [r,g,b] */
    setColor(rgb) { color = rgb; buildLut(); },

    strokeBegin(x, y, p, alt, az) {
      if (stroke) api.strokeEnd(x, y, 0, alt, az);
      touched = new Map();
      stroke = new Stroke(tool, write, { paper: sheetPaper });
      stroke.begin(x, y, p, alt, az);
      return takeDirty();
    },
    strokeMove(x, y, p, alt, az) {
      if (!stroke) return api.strokeBegin(x, y, p, alt, az);
      stroke.move(x, y, p, alt, az);
      return takeDirty();
    },
    strokeEnd(x, y, p = 0, alt, az) {
      if (!stroke) return null;
      stroke.end(x, y, p, alt, az);
      stroke = null;
      if (touched.size) {
        undoStack.push(touched);
        if (undoStack.length > undoDepth) undoStack.shift();
        redoStack.length = 0;
      }
      touched = null;
      return takeDirty();
    },
    get drawing() { return !!stroke; },

    undo() {
      if (stroke) api.strokeEnd(stroke.sx, stroke.sy, 0);
      const m = undoStack.pop(); if (!m) return null;
      redoStack.push(restoreTiles(m));
      return takeDirty();
    },
    redo() {
      const m = redoStack.pop(); if (!m) return null;
      undoStack.push(restoreTiles(m));
      return takeDirty();
    },
    get canUndo() { return undoStack.length > 0; },
    get canRedo() { return redoStack.length > 0; },

    clear() {
      density.fill(0); undoStack.length = 0; redoStack.length = 0;
      growDirty(0, 0, W, Hh); return takeDirty();
    },

    /**
     * Downsampled blit (research/13: the reference draws into a document 4×
     * the screen and shows it fitted, which is what makes its line thin and
     * tonal). `ss` sheet pixels per screen pixel; `out` is a whole-screen
     * RGBA buffer of width outW. The rect (sheet px) is widened to whole
     * screen pixels; returns the screen rect written {x0,y0,x1,y1}.
     */
    blitDown(rect, out, outW, ss) {
      const sx0 = Math.max(0, Math.floor(rect.x0 / ss)), sy0 = Math.max(0, Math.floor(rect.y0 / ss));
      const sx1 = Math.min(Math.floor(W / ss), Math.ceil(rect.x1 / ss)), sy1 = Math.min(Math.floor(Hh / ss), Math.ceil(rect.y1 / ss));
      if (sx0 >= sx1 || sy0 >= sy1) return null;
      const inv = 1 / (ss * ss);
      for (let sy = sy0; sy < sy1; sy++) {
        let o = (sy * outW + sx0) * 4;
        const base = sy * ss * W;
        for (let sx = sx0; sx < sx1; sx++, o += 4) {
          let sum = 0, i = base + sx * ss;
          for (let yy = 0; yy < ss; yy++, i += W) for (let xx = 0; xx < ss; xx++) sum += density[i + xx];
          const d3 = Math.round(sum * inv) * 3;
          out[o] = lut[d3]; out[o + 1] = lut[d3 + 1]; out[o + 2] = lut[d3 + 2]; out[o + 3] = 255;
        }
      }
      return { x0: sx0, y0: sy0, x1: sx1, y1: sy1 };
    },

    /**
     * Density → RGBA (graphite on white) for a rect. `out` may be reused;
     * it must hold (x1-x0)*(y1-y0)*4 bytes. With `full` = true, `out` is a
     * whole-sheet buffer (an ImageData's data) and only the rect is updated,
     * ready for ctx.putImageData(img, 0, 0, x0, y0, w, h).
     */
    toRGBA(rect = clip, out, full = false) {
      const x0 = Math.max(0, rect.x0), y0 = Math.max(0, rect.y0);
      const x1 = Math.min(W, rect.x1), y1 = Math.min(Hh, rect.y1);
      const w = x1 - x0, h = y1 - y0;
      if (full) {
        // `out` is a whole-sheet RGBA buffer (W*Hh*4); only the rect is rewritten
        for (let y = y0; y < y1; y++) {
          let i = y * W + x0, o = i * 4;
          for (let x = x0; x < x1; x++, i++) {
            const d3 = density[i] * 3;
            out[o++] = lut[d3]; out[o++] = lut[d3 + 1]; out[o++] = lut[d3 + 2]; out[o++] = 255;
          }
        }
        return out;
      }
      if (!out || out.length < w * h * 4) out = new Uint8ClampedArray(w * h * 4);
      let o = 0;
      for (let y = y0; y < y1; y++) {
        let i = y * W + x0;
        for (let x = x0; x < x1; x++, i++) {
          const d3 = density[i] * 3;
          out[o++] = lut[d3]; out[o++] = lut[d3 + 1]; out[o++] = lut[d3 + 2]; out[o++] = 255;
        }
      }
      return out;
    },
  };
  return api;
}

export { TOOLS, PENCIL_GRADES } from "./tools.js";
export { makePaper, PAPER_KINDS } from "./paper.js";
export { tiltToSpherical } from "./stroke.js";
