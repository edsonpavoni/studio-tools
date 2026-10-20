// sheet.js — an unbounded, tiled, multi-colour sheet on the graphite engine.
//
// The engine (graphite/engine/) knows one flat buffer and one colour. This wraps
// its kernels into tiles created on first touch, one 8-bit density layer per
// colour used (the reference app's "one layer, one colour", composited with
// multiply), tile-local undo, a downsampled (SS×) blit into per-tile canvases
// the page draws through its view transform, PNG round-trips for autosave,
// and a PNG export of the drawn region.
//
// Units: "sheet px" are engine pixels, SS per device pixel (the reference draws
// into a document 4× the screen and shows it fitted: that is the thin tonal
// line). A tile is TILE sheet px = TILE/SS device px.
//
// Tile canvases are white where untouched (the LUT is channel / paper channel):
// the page and exportPng multiply them over the paper colour, and over a
// picture placed under the sheet when there is one, so graphite sits on both.

import { Stroke } from './graphite/engine/stroke.js';
import { rasterDab } from './graphite/engine/dab.js';
import { makePaper } from './graphite/engine/paper.js';
import { TOOLS } from './graphite/engine/tools.js';

export const SS = 4;                       // sheet px per device px
export const TILE = 1024;                  // sheet px per tile
export const TILE_DEV = TILE / SS;         // device px per tile (256)
const SNAP = 128;                          // undo snapshot block, sheet px
const SNAP_PER_TILE = TILE / SNAP;
export const PAPER_RGB = [245, 242, 235];  // --paper #f5f2eb
const UNDO_DEPTH = 40;
const UNDO_BYTES = 160 * 1024 * 1024;       // a wide eraser scrub snapshots every colour layer it crosses: cap the memory

const hexToRgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
const key = (tx, ty) => `${tx},${ty}`;

// density → (channel / paper channel), per colour; 1 = untouched paper
function makeLut(rgb) {
  const lut = new Float32Array(256 * 3);
  for (let d = 0; d < 256; d++) {
    const dark = 1 - Math.pow(1 - d / 255, 1 / 2.2);                  // the engine's 1/2.2 encode
    for (let c = 0; c < 3; c++) lut[d * 3 + c] = (PAPER_RGB[c] - (PAPER_RGB[c] - rgb[c]) * dark) / PAPER_RGB[c];
  }
  return lut;
}

export function createSheet({ paper = 'noise', seed = 7 } = {}) {
  const sheetPaper = makePaper(paper, seed);
  const tiles = new Map();                 // "tx,ty" → tile
  const luts = new Map();                  // colour key → lut
  let tool = TOOLS.HB, colour = '#2a2a2a';
  let stroke = null, touched = null;       // touched: Map snapKey → {tile, layer, bx, by, copy}
  const undoStack = [], redoStack = [];
  let undoBytes = 0;
  const bytesOf = (m) => m.size * SNAP * SNAP;
  function pushUndo(m) {
    undoStack.push(m); undoBytes += bytesOf(m);
    while (undoStack.length > 1 && (undoStack.length > UNDO_DEPTH || undoBytes > UNDO_BYTES)) undoBytes -= bytesOf(undoStack.shift());
  }
  const dirtyTiles = new Set();
  const smudgeStates = new Map();          // colour key → {load} for the current smudge stroke
  const scratch = document.createElement('canvas'); scratch.width = scratch.height = TILE;
  const sctx = scratch.getContext('2d', { willReadFrequently: true });

  function lutFor(k) { let l = luts.get(k); if (!l) { l = makeLut(hexToRgb(k)); luts.set(k, l); } return l; }

  function newTile(tx, ty) {
    const canvas = document.createElement('canvas'); canvas.width = canvas.height = TILE_DEV;
    const ctx = canvas.getContext('2d', { alpha: false });
    ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, TILE_DEV, TILE_DEV);   // tiles are white-based: the page multiplies them over paper (and a picture)
    const t = { tx, ty, layers: new Map(), canvas, ctx, img: ctx.createImageData(TILE_DEV, TILE_DEV),
      dirty: null, saveDirty: new Set(), saveGen: new Map(), x0: tx * TILE, y0: ty * TILE };
    tiles.set(key(tx, ty), t);
    return t;
  }
  const tileAt = (tx, ty) => tiles.get(key(tx, ty)) || newTile(tx, ty);
  function layerOf(t, k, create) {
    let l = t.layers.get(k);
    if (!l && create) { l = new Uint8Array(TILE * TILE); t.layers.set(k, l); }
    return l;
  }

  function touchSave(t, k) {                // a layer changed: it needs saving, and any save already in flight is stale
    t.saveDirty.add(k); t.saveGen.set(k, (t.saveGen.get(k) || 0) + 1);
  }

  function growDirty(t, x0, y0, x1, y1) {   // tile-local sheet px
    const d = t.dirty;
    if (!d) t.dirty = { x0, y0, x1, y1 };
    else { if (x0 < d.x0) d.x0 = x0; if (y0 < d.y0) d.y0 = y0; if (x1 > d.x1) d.x1 = x1; if (y1 > d.y1) d.y1 = y1; }
    dirtyTiles.add(t);
  }

  function snapshot(t, k, layer, lx0, ly0, lx1, ly1) {   // copy the undo blocks under a local rect, once per stroke
    for (let by = (ly0 / SNAP) | 0; by <= ((ly1 - 1) / SNAP) | 0; by++) {
      for (let bx = (lx0 / SNAP) | 0; bx <= ((lx1 - 1) / SNAP) | 0; bx++) {
        const id = `${t.tx},${t.ty},${k},${bx},${by}`;
        if (touched.has(id)) continue;
        const copy = new Uint8Array(SNAP * SNAP);
        for (let y = 0; y < SNAP; y++) {
          const off = (by * SNAP + y) * TILE + bx * SNAP;
          copy.set(layer.subarray(off, off + SNAP), y * SNAP);
        }
        touched.set(id, { t, k, bx, by, copy });
      }
    }
  }

  // per-dab write: find the tiles under the dab, the layers it affects, snapshot, rasterise
  function write(g, flow) {
    const e = g.A + 1;
    const X0 = Math.floor(g.cx - e), X1 = Math.ceil(g.cx + e) + 1, Y0 = Math.floor(g.cy - e), Y1 = Math.ceil(g.cy + e) + 1;
    const pencil = tool.kind === 'pencil';
    for (let ty = Math.floor(Y0 / TILE); ty <= Math.floor((Y1 - 1) / TILE); ty++) {
      for (let tx = Math.floor(X0 / TILE); tx <= Math.floor((X1 - 1) / TILE); tx++) {
        const t = pencil ? tileAt(tx, ty) : tiles.get(key(tx, ty));
        if (!t) continue;                                          // erasing/smudging empty paper: nothing to do
        const clip = { x0: Math.max(t.x0, X0), y0: Math.max(t.y0, Y0), x1: Math.min(t.x0 + TILE, X1), y1: Math.min(t.y0 + TILE, Y1) };
        if (clip.x0 >= clip.x1 || clip.y0 >= clip.y1) continue;
        const keys = pencil ? [colour] : [...t.layers.keys()];
        let changed = false;
        for (const k of keys) {
          const layer = layerOf(t, k, pencil);
          snapshot(t, k, layer, clip.x0 - t.x0, clip.y0 - t.y0, clip.x1 - t.x0, clip.y1 - t.y0);
          let st = smudgeStates.get(k); if (!st) { st = { load: NaN }; smudgeStates.set(k, st); }
          if (rasterDab(layer, TILE, t.x0, t.y0, clip, sheetPaper, tool, g, flow, st)) { changed = true; touchSave(t, k); }
        }
        if (changed) growDirty(t, clip.x0 - t.x0, clip.y0 - t.y0, clip.x1 - t.x0, clip.y1 - t.y0);
      }
    }
  }

  // composite a tile-local rect (sheet px) of all layers into the tile canvas
  function blitTile(t, r) {
    const sx0 = Math.floor(r.x0 / SS), sy0 = Math.floor(r.y0 / SS);
    const sx1 = Math.min(TILE_DEV, Math.ceil(r.x1 / SS)), sy1 = Math.min(TILE_DEV, Math.ceil(r.y1 / SS));
    if (sx0 >= sx1 || sy0 >= sy1) return null;
    const data = t.img.data, layers = [...t.layers.entries()].map(([k, l]) => [lutFor(k), l]);
    const inv = 1 / (SS * SS);
    for (let sy = sy0; sy < sy1; sy++) {
      let o = (sy * TILE_DEV + sx0) * 4;
      for (let sx = sx0; sx < sx1; sx++, o += 4) {
        let f0 = 1, f1 = 1, f2 = 1;
        for (const [lut, layer] of layers) {
          let sum = 0, i = sy * SS * TILE + sx * SS;
          for (let yy = 0; yy < SS; yy++, i += TILE) for (let xx = 0; xx < SS; xx++) sum += layer[i + xx];
          const d3 = Math.round(sum * inv) * 3;
          f0 *= lut[d3]; f1 *= lut[d3 + 1]; f2 *= lut[d3 + 2];
        }
        data[o] = 255 * f0; data[o + 1] = 255 * f1; data[o + 2] = 255 * f2; data[o + 3] = 255;   // 255 = untouched; paper comes from the multiply
      }
    }
    t.ctx.putImageData(t.img, 0, 0, sx0, sy0, sx1 - sx0, sy1 - sy0);
    return { x0: sx0, y0: sy0, x1: sx1, y1: sy1 };     // device px within the tile
  }

  function restore(map) {                   // apply snapshots, return the inverse set
    const inverse = new Map();
    for (const [id, s] of map) {
      const layer = layerOf(s.t, s.k, true), cur = new Uint8Array(SNAP * SNAP);
      for (let y = 0; y < SNAP; y++) {
        const off = (s.by * SNAP + y) * TILE + s.bx * SNAP;
        cur.set(layer.subarray(off, off + SNAP), y * SNAP);
        layer.set(s.copy.subarray(y * SNAP, y * SNAP + SNAP), off);
      }
      inverse.set(id, { ...s, copy: cur });
      touchSave(s.t, s.k);
      growDirty(s.t, s.bx * SNAP, s.by * SNAP, (s.bx + 1) * SNAP, (s.by + 1) * SNAP);
    }
    return inverse;
  }

  const api = {
    tiles, SS, TILE, TILE_DEV, PAPER_RGB,
    get tool() { return tool; },
    get colour() { return colour; },
    get drawing() { return !!stroke; },

    /** name from TOOLS ('HB', '2H', '4B', 'eraser', 'kneaded', 'smudge') or a tool object, with overrides (size in sheet px) */
    setTool(t, over) {
      const base = typeof t === 'string' ? TOOLS[t] : t;
      if (!base) throw new Error('unknown tool ' + t);
      tool = over ? Object.freeze({ ...base, ...over }) : base;
      return tool;
    },
    setColour(hex) { colour = hex.toLowerCase(); },

    strokeBegin(x, y, p, alt, az) {
      if (stroke) api.strokeEnd(x, y, 0, alt, az);
      touched = new Map(); smudgeStates.clear();
      stroke = new Stroke(tool, write, { paper: sheetPaper });
      stroke.begin(x, y, p, alt, az);
    },
    strokeMove(x, y, p, alt, az) { if (!stroke) api.strokeBegin(x, y, p, alt, az); else stroke.move(x, y, p, alt, az); },
    strokeEnd(x, y, p = 0, alt, az) {
      if (!stroke) return;
      stroke.end(x, y, p, alt, az); stroke = null;
      if (touched.size) { pushUndo(touched); redoStack.length = 0; }
      touched = null;
    },
    get dabs() { return stroke ? stroke.dabs : 0; },

    undo() {
      if (stroke) api.strokeEnd(stroke.sx, stroke.sy, 0);
      const m = undoStack.pop(); if (!m) return false;
      undoBytes -= bytesOf(m); redoStack.push(restore(m)); return true;
    },
    redo() { const m = redoStack.pop(); if (!m) return false; pushUndo(restore(m)); return true; },

    /** composite every dirty tile region; calls draw(tile, deviceRect) for each so the page can repaint */
    flush(draw) {
      for (const t of dirtyTiles) {
        const r = t.dirty; t.dirty = null;
        const dev = blitTile(t, r);
        if (dev && draw) draw(t, dev);
      }
      dirtyTiles.clear();
    },

    clear() {                               // a stroke in progress ends with the old sheet, not in the new one
      stroke = null; touched = null; smudgeStates.clear();
      tiles.clear(); undoStack.length = 0; redoStack.length = 0; undoBytes = 0; dirtyTiles.clear();
    },

    /** bounding box of every non-zero pixel, in device px, or null */
    bounds() {
      let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
      for (const t of tiles.values()) {
        for (const layer of t.layers.values()) {
          for (let y = 0; y < TILE; y++) {
            const row = y * TILE;
            let first = -1, last = -1;
            for (let x = 0; x < TILE; x++) if (layer[row + x]) { if (first < 0) first = x; last = x; }
            if (first < 0) continue;
            const gy = t.ty * TILE + y;
            x0 = Math.min(x0, t.tx * TILE + first); x1 = Math.max(x1, t.tx * TILE + last + 1);
            y0 = Math.min(y0, gy); y1 = Math.max(y1, gy + 1);
          }
        }
      }
      return x0 === Infinity ? null : { x0: Math.floor(x0 / SS), y0: Math.floor(y0 / SS), x1: Math.ceil(x1 / SS), y1: Math.ceil(y1 / SS) };
    },

    /** PNG of the drawn region (+margin device px), paper white, at most maxPx pixels. null if empty.
     *  underlay {img, x, y, w, h} (device px): a picture under the drawing, included and multiplied over. */
    async exportPng({ margin = 32, maxPx = 16e6, underlay = null } = {}) {
      let b = api.bounds();
      if (underlay) {
        const u = { x0: Math.floor(underlay.x), y0: Math.floor(underlay.y), x1: Math.ceil(underlay.x + underlay.w), y1: Math.ceil(underlay.y + underlay.h) };
        b = b ? { x0: Math.min(b.x0, u.x0), y0: Math.min(b.y0, u.y0), x1: Math.max(b.x1, u.x1), y1: Math.max(b.y1, u.y1) } : u;
      }
      if (!b) return null;
      const w = b.x1 - b.x0 + 2 * margin, h = b.y1 - b.y0 + 2 * margin;
      const s = Math.min(1, Math.sqrt(maxPx / (w * h)));
      const out = document.createElement('canvas'); out.width = Math.round(w * s); out.height = Math.round(h * s);
      const octx = out.getContext('2d');
      octx.fillStyle = `rgb(${PAPER_RGB.join(',')})`; octx.fillRect(0, 0, out.width, out.height);
      if (underlay) octx.drawImage(underlay.img, (underlay.x - b.x0 + margin) * s, (underlay.y - b.y0 + margin) * s, underlay.w * s, underlay.h * s);
      octx.globalCompositeOperation = 'multiply';           // tiles are white where untouched
      for (const t of tiles.values()) {
        if (t.dirty) { blitTile(t, t.dirty); t.dirty = null; dirtyTiles.delete(t); }
        octx.drawImage(t.canvas, (t.tx * TILE_DEV - b.x0 + margin) * s, (t.ty * TILE_DEV - b.y0 + margin) * s, TILE_DEV * s, TILE_DEV * s);
      }
      return new Promise((res) => out.toBlob(res, 'image/png'));
    },

    /** [{t, k, gen}] layers that changed since their last save. Pass gen back to markSaved(): a layer
     *  touched again while its PNG was uploading stays unsaved. */
    unsaved() {
      const list = [];
      for (const t of tiles.values()) for (const k of t.saveDirty) list.push({ t, k, gen: t.saveGen.get(k) || 0 });
      return list;
    },
    async layerPng(t, k) {                   // density as the R channel of an opaque PNG
      const layer = t.layers.get(k); if (!layer) return null;
      const img = sctx.createImageData(TILE, TILE), d = img.data;
      for (let i = 0, o = 0; i < layer.length; i++, o += 4) { d[o] = layer[i]; d[o + 1] = layer[i]; d[o + 2] = layer[i]; d[o + 3] = 255; }
      sctx.putImageData(img, 0, 0);
      return new Promise((res) => scratch.toBlob(res, 'image/png'));
    },
    markSaved(t, k, gen) { if (gen === undefined || (t.saveGen.get(k) || 0) === gen) t.saveDirty.delete(k); },
    /** the inverse of layerPng; marks the tile dirty for the next flush. stillWanted() is asked after the decode
     *  (the sheet may have been switched meanwhile). Returns 'loaded', or 'merged' when the layer already had
     *  unsaved strokes (drawn before the tile arrived): those are kept, and the layer stays unsaved. */
    async loadLayer(tx, ty, k, blob, stillWanted) {
      const bmp = await createImageBitmap(blob);
      if (stillWanted && !stillWanted()) return false;
      sctx.clearRect(0, 0, TILE, TILE); sctx.drawImage(bmp, 0, 0);
      const d = sctx.getImageData(0, 0, TILE, TILE).data;
      const t = tileAt(tx, ty), merge = t.saveDirty.has(k), layer = layerOf(t, k, true);
      if (merge) for (let i = 0, o = 0; i < layer.length; i++, o += 4) { if (d[o] > layer[i]) layer[i] = d[o]; }
      else for (let i = 0, o = 0; i < layer.length; i++, o += 4) layer[i] = d[o];
      growDirty(t, 0, 0, TILE, TILE);
      return merge ? 'merged' : 'loaded';
    },
    get hasUnsaved() { for (const t of tiles.values()) if (t.saveDirty.size) return true; return false; },
    get canUndo() { return undoStack.length > 0; },
    get canRedo() { return redoStack.length > 0; },
  };
  return api;
}

export { TOOLS };
export { tiltToSpherical } from './graphite/engine/stroke.js';
