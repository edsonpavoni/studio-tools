// sketch.js — the page: pointer input, unbounded tiled sheet, viewport, undo, UI,
// autosave and send. Brush maths live in brush.js.
import { makePaper, tiltAngles, PencilStroke, SmudgeStroke, PAPER_RGB, PRESETS, DEFAULT_SETTINGS } from './brush.js';
import { api, subscribe } from './client.js';

const TILE = 256;                 // sheet tile, physical px
const UNDO_DEPTH = 30;
const AUTOSAVE_MS = 3000;
const EXPORT_MARGIN = 64;
const MAX_EXPORT_PX = 16e6;       // Safari canvas area cap
const THUMB_PX = 160000;          // gallery thumbnail, ~400×400
const ZOOM_MIN = 0.2, ZOOM_MAX = 8;
const TAP_MS = 350, TAP_MOVE_CSS = 12, LONG_PRESS_MS = 450;
const SMUDGE_START_CSS = 5;       // one finger must move this far before it smudges (lets two-finger gestures start clean)
const CORNER_CSS = 90;            // triple-tap area for the debug overlay
const GRID_SPACING = 52;          // sheet px per grid cell: 5 mm at 264 ppi (the sheet is at device pixels)
const GRID_MAJOR = 5;             // every 5th mark (25 mm) is bolder
const GRID_MINOR_MIN_ZOOM = 0.5;  // below this zoom only the major marks are drawn
const GRID_MODES = ['off', 'dots', 'lines'];
const GRID_INK = '42,42,46';      // rgb of the grid marks
const GRID_ALPHA = { dots: 0.12, lines: 0.04, majorDots: 0.18, majorLines: 0.08 };   // Edson 16:43: lines softer, dots stronger
const COLOURS = [                 // [r,g,b] 0..1 — graphite, warm grey, red, blue, green
  [0.16, 0.16, 0.18], [0.54, 0.49, 0.44], [0.80, 0.21, 0.17], [0.18, 0.37, 0.72], [0.22, 0.56, 0.33],
];
const SLIDERS = [                 // key, label, min, max
  ['size', 'size', 0.4, 3], ['hardness', 'hardness', 0.05, 0.95], ['grain', 'grain', 0, 1], ['smoothing', 'smoothing', 0, 0.9],
];

const dpr = Math.max(1, window.devicePixelRatio || 1);
const $ = (sel) => document.querySelector(sel);
const canvas = $('#sheet'), ctx = canvas.getContext('2d', { alpha: false, desynchronized: true });
const ghost = $('#ghost'), gctx = ghost.getContext('2d');
const grid = $('#grid'), gridCtx = grid.getContext('2d');
const paper = makePaper();
const paperCss = `rgb(${PAPER_RGB.join(',')})`;

// ---------------------------------------------------------------- state
const store = {
  get(key, fallback) { try { const v = localStorage.getItem('sketch.' + key); return v === null ? fallback : JSON.parse(v); } catch { return fallback; } },
  set(key, value) { try { localStorage.setItem('sketch.' + key, JSON.stringify(value)); } catch { /* private mode */ } },
};
const state = {
  preset: store.get('preset', 'HB'),
  eraser: false,
  colour: store.get('colour', 0),
  settings: Object.assign({ '2H': { ...DEFAULT_SETTINGS }, 'HB': { ...DEFAULT_SETTINGS }, '4B': { ...DEFAULT_SETTINGS } }, store.get('settings', {})),
  sheetId: store.get('sheet', 'current'),
  view: { x: 0, y: 0 }, zoom: 1,
  grid: GRID_MODES.includes(store.get('grid', 'off')) ? store.get('grid', 'off') : 'off',
  debug: false,
};
const stats = { evMs: 0, evAvg: 0, dabs: 0, dabsPerS: 0, samples: 0, samplesPerS: 0, lastTick: performance.now() };

// ---------------------------------------------------------------- sheet: tiles + undo recording
const sheet = {
  TILE, tiles: new Map(), rec: null, pendingDirty: null,
  deleted: new Set(),               // tile keys undone back to blank paper, to DELETE on the server
  key: (tx, ty) => tx + ',' + ty,
  tile(tx, ty) {
    const key = this.key(tx, ty);
    let t = this.tiles.get(key);
    if (!t) {
      const data = new Uint8ClampedArray(TILE * TILE * 4);
      fillPaper(data);
      t = { tx, ty, data, image: new ImageData(data, TILE, TILE), canvas: null, cctx: null, canvasDirty: null, saveDirty: false };
      this.tiles.set(key, t);
      this.deleted.delete(key);
      if (this.rec && !this.rec.has(key)) this.rec.set(key, null);   // null = was blank paper
    } else if (this.rec && !this.rec.has(key)) {
      this.rec.set(key, t.data.slice());                              // copy on first write this stroke
    }
    return t.data;
  },
  markDirty(x0, y0, x1, y1) {
    const r = this.pendingDirty;
    this.pendingDirty = r ? [Math.min(r[0], x0), Math.min(r[1], y0), Math.max(r[2], x1), Math.max(r[3], y1)] : [x0, y0, x1, y1];
    for (let ty = Math.floor(y0 / TILE); ty <= Math.floor(y1 / TILE); ty++) {
      for (let tx = Math.floor(x0 / TILE); tx <= Math.floor(x1 / TILE); tx++) {
        const t = this.tiles.get(this.key(tx, ty));
        if (!t) continue;
        const d = [Math.max(0, x0 - tx * TILE), Math.max(0, y0 - ty * TILE), Math.min(TILE - 1, x1 - tx * TILE), Math.min(TILE - 1, y1 - ty * TILE)];
        const c = t.canvasDirty;
        t.canvasDirty = c ? [Math.min(c[0], d[0]), Math.min(c[1], d[1]), Math.max(c[2], d[2]), Math.max(c[3], d[3])] : d;
        t.saveDirty = true;
      }
    }
  },
  beginRecord() { this.rec = new Map(); },
  endRecord() {
    const rec = this.rec; this.rec = null;
    if (!rec || rec.size === 0) return;
    undoStack.push(rec); if (undoStack.length > UNDO_DEPTH) undoStack.shift();
    redoStack.length = 0;
  },
  clear() { this.tiles.clear(); this.deleted.clear(); this.rec = null; this.pendingDirty = null; undoStack.length = 0; redoStack.length = 0; },
};
const undoStack = [], redoStack = [];

function fillPaper(data) {
  for (let i = 0; i < data.length; i += 4) { data[i] = PAPER_RGB[0]; data[i + 1] = PAPER_RGB[1]; data[i + 2] = PAPER_RGB[2]; data[i + 3] = 255; }
}

function swapStates(from, to) {   // apply every snapshot in `from`, pushing the inverse on `to`
  const rec = from.pop();
  if (!rec) return false;
  const inverse = new Map();
  for (const [key, before] of rec) {
    const [tx, ty] = key.split(',').map(Number);
    const existed = sheet.tiles.has(key);
    sheet.tile(tx, ty);
    const t = sheet.tiles.get(key);
    inverse.set(key, existed ? t.data.slice() : null);
    if (before) { t.data.set(before); t.canvasDirty = [0, 0, TILE - 1, TILE - 1]; t.saveDirty = true; }
    else { sheet.tiles.delete(key); sheet.deleted.add(key); }   // back to blank paper: drop the tile
  }
  to.push(inverse);
  redrawAll();
  return true;
}
const undo = () => { if (!swapStates(undoStack, redoStack)) toast('nothing to undo'); };
const redo = () => { if (!swapStates(redoStack, undoStack)) toast('nothing to redo'); };

// ---------------------------------------------------------------- viewport + rendering
const toSheet = (cx, cy) => ({ x: cx * dpr / state.zoom + state.view.x, y: cy * dpr / state.zoom + state.view.y });

function resize() {
  const r = canvas.getBoundingClientRect();
  for (const c of [canvas, grid, ghost]) { c.width = Math.round(r.width * dpr); c.height = Math.round(r.height * dpr); }
  redrawAll();
}

// ---------------------------------------------------------------- grid overlay (never in the tiles or the export)
let gridDrawn = '';
function drawGrid() {   // in sheet coordinates, so it pans and zooms with the paper; repaints only when the view changed
  const mode = state.grid, z = state.zoom, v = state.view, W = grid.width, H = grid.height;
  const sig = `${mode}|${z}|${v.x}|${v.y}|${W}|${H}`;
  if (sig === gridDrawn) return;
  gridDrawn = sig;
  gridCtx.clearRect(0, 0, W, H);
  if (mode === 'off') return;
  const S = GRID_SPACING, minor = z >= GRID_MINOR_MIN_ZOOM, stepIdx = minor ? 1 : GRID_MAJOR;
  const i0 = Math.floor(v.x / S / stepIdx) * stepIdx, i1 = Math.ceil((v.x + W / z) / S);
  const j0 = Math.floor(v.y / S / stepIdx) * stepIdx, j1 = Math.ceil((v.y + H / z) / S);
  const sx = (i) => (i * S - v.x) * z, sy = (j) => (j * S - v.y) * z, isMajor = (k) => k % GRID_MAJOR === 0;
  if (mode === 'lines') {
    gridCtx.lineWidth = 1;
    for (const bold of [false, true]) {
      gridCtx.strokeStyle = `rgba(${GRID_INK},${bold ? GRID_ALPHA.majorLines : GRID_ALPHA.lines})`;
      gridCtx.beginPath();
      for (let i = i0; i <= i1; i += stepIdx) if (isMajor(i) === bold) { const x = Math.round(sx(i)) + 0.5; gridCtx.moveTo(x, 0); gridCtx.lineTo(x, H); }
      for (let j = j0; j <= j1; j += stepIdx) if (isMajor(j) === bold) { const y = Math.round(sy(j)) + 0.5; gridCtx.moveTo(0, y); gridCtx.lineTo(W, y); }
      gridCtx.stroke();
    }
  } else {
    for (const bold of [false, true]) {
      gridCtx.fillStyle = `rgba(${GRID_INK},${bold ? GRID_ALPHA.majorDots : GRID_ALPHA.dots})`;
      const r = bold ? 1.1 : 0.75;   // 1.5 px dots, a touch larger on the 25 mm marks
      gridCtx.beginPath();
      for (let i = i0; i <= i1; i += stepIdx) for (let j = j0; j <= j1; j += stepIdx) {
        if ((isMajor(i) && isMajor(j)) !== bold) continue;
        gridCtx.moveTo(sx(i) + r, sy(j)); gridCtx.arc(sx(i), sy(j), r, 0, Math.PI * 2);
      }
      gridCtx.fill();
    }
  }
}
function setGrid(mode) {
  state.grid = GRID_MODES.includes(mode) ? mode : 'off';
  store.set('grid', state.grid); syncBar(); drawGrid();
}
const cycleGrid = () => setGrid(GRID_MODES[(GRID_MODES.indexOf(state.grid) + 1) % GRID_MODES.length]);

function uploadTile(t) {   // keep the per-tile canvas (used at zoom != 1 and for export) in sync
  if (!t.canvas) {
    t.canvas = document.createElement('canvas'); t.canvas.width = t.canvas.height = TILE;
    t.cctx = t.canvas.getContext('2d'); t.canvasDirty = [0, 0, TILE - 1, TILE - 1];
  }
  const d = t.canvasDirty;
  if (d) { t.cctx.putImageData(t.image, 0, 0, d[0], d[1], d[2] - d[0] + 1, d[3] - d[1] + 1); t.canvasDirty = null; }
}

const fastPath = () => state.zoom === 1 && Number.isInteger(state.view.x) && Number.isInteger(state.view.y);

function drawTile(t, clip) {
  const sx = t.tx * TILE - state.view.x, sy = t.ty * TILE - state.view.y;
  if (fastPath()) {
    const c = clip || [0, 0, TILE - 1, TILE - 1];
    ctx.putImageData(t.image, sx, sy, c[0], c[1], c[2] - c[0] + 1, c[3] - c[1] + 1);
  } else {
    uploadTile(t);
    const z = state.zoom;
    ctx.drawImage(t.canvas, sx * z, sy * z, TILE * z + 0.5, TILE * z + 0.5);
  }
}

function flush() {   // paint the pixels touched since the last flush, synchronously
  const r = sheet.pendingDirty;
  if (!r) return;
  sheet.pendingDirty = null;
  for (let ty = Math.floor(r[1] / TILE); ty <= Math.floor(r[3] / TILE); ty++) {
    for (let tx = Math.floor(r[0] / TILE); tx <= Math.floor(r[2] / TILE); tx++) {
      const t = sheet.tiles.get(sheet.key(tx, ty));
      if (t) drawTile(t, [Math.max(0, r[0] - tx * TILE), Math.max(0, r[1] - ty * TILE), Math.min(TILE - 1, r[2] - tx * TILE), Math.min(TILE - 1, r[3] - ty * TILE)]);
    }
  }
}

function redrawAll() {
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.fillStyle = paperCss; ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.imageSmoothingEnabled = state.zoom < 1;
  const z = state.zoom, v = state.view;
  const tx0 = Math.floor(v.x / TILE), ty0 = Math.floor(v.y / TILE);
  const tx1 = Math.floor((v.x + canvas.width / z) / TILE), ty1 = Math.floor((v.y + canvas.height / z) / TILE);
  for (const t of sheet.tiles.values()) if (t.tx >= tx0 && t.tx <= tx1 && t.ty >= ty0 && t.ty <= ty1) drawTile(t);
  sheet.pendingDirty = null;
  gctx.clearRect(0, 0, ghost.width, ghost.height);
  drawGrid();
}

let redrawQueued = false;
function queueRedraw() {
  if (redrawQueued) return;
  redrawQueued = true;
  requestAnimationFrame(() => { redrawQueued = false; redrawAll(); });
}

function settleView() {   // snap near-1 zooms to the exact putImageData path
  if (Math.abs(state.zoom - 1) < 0.04) state.zoom = 1;
  if (state.zoom === 1) { state.view.x = Math.round(state.view.x); state.view.y = Math.round(state.view.y); }
  redrawAll();
}

// ---------------------------------------------------------------- pen strokes
let stroke = null, penId = null, ghostBox = null;
function capture(e) { try { canvas.setPointerCapture(e.pointerId); } catch { /* synthetic or stale pointer */ } }

function penDown(e) {
  if (stroke) return;
  penId = e.pointerId;
  capture(e);
  sheet.beginRecord();
  stroke = new PencilStroke(sheet, paper, {
    preset: state.preset, settings: currentSettings(), colour: COLOURS[state.colour], erase: state.eraser,
  });
  penMove(e);
}

function penMove(e) {
  if (!stroke || e.pointerId !== penId) return;
  const t0 = performance.now();
  const events = (e.getCoalescedEvents && e.getCoalescedEvents()) || [];
  const dabs0 = stroke.dabs;
  for (const ev of events.length ? events : [e]) feedSample(ev, e.pointerType);
  flush();
  drawGhost(e);
  recordTiming(performance.now() - t0, stroke.dabs - dabs0, events.length || 1);
}

function feedSample(ev, pointerType) {
  const { x, y } = toSheet(ev.clientX, ev.clientY);
  const pressure = pointerType === 'pen' ? ev.pressure : (ev.pressure || 0.5);
  const { altitude, azimuth } = tiltAngles(ev);
  stroke.addSample(x, y, pressure, altitude, azimuth);
}

function penUp(e) {
  if (!stroke || e.pointerId !== penId) return;
  if (e.type !== 'pointercancel') penMove(e);
  stroke = null; penId = null;
  sheet.endRecord();
  clearGhost();
}

// predicted events as a faint tail on the overlay, never into the tiles
function drawGhost(e) {
  clearGhost();
  const pred = e.getPredictedEvents && e.getPredictedEvents();
  if (!pred || !pred.length || !stroke.last) return;
  const z = state.zoom, v = state.view, c = COLOURS[state.colour];
  gctx.beginPath();
  gctx.moveTo((stroke.last.x - v.x) * z, (stroke.last.y - v.y) * z);
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const p of pred) {
    const x = p.clientX * dpr, y = p.clientY * dpr;
    gctx.lineTo(x, y);
    minX = Math.min(minX, x); minY = Math.min(minY, y); maxX = Math.max(maxX, x); maxY = Math.max(maxY, y);
  }
  const w = stroke.radius(stroke.last.p) * 2 * z;
  gctx.lineWidth = w; gctx.lineCap = 'round'; gctx.lineJoin = 'round';
  gctx.strokeStyle = `rgba(${c.map((k) => Math.round(k * 255)).join(',')},${state.eraser ? 0 : 0.18})`;
  gctx.stroke();
  const lx = (stroke.last.x - v.x) * z, ly = (stroke.last.y - v.y) * z;
  ghostBox = [Math.min(minX, lx) - w, Math.min(minY, ly) - w, Math.max(maxX, lx) + w, Math.max(maxY, ly) + w];
}
function clearGhost() {
  if (!ghostBox) return;
  gctx.clearRect(ghostBox[0], ghostBox[1], ghostBox[2] - ghostBox[0], ghostBox[3] - ghostBox[1]);
  ghostBox = null;
}

// ---------------------------------------------------------------- touch: smudge, pan/zoom, taps
const touches = new Map();          // pointerId -> {x, y} physical px
let touchSession = null, smudge = null, gesture = null;

function touchDown(e) {
  if (stroke) return;                                   // pen is down: ignore fingers
  capture(e);
  const p = { x: e.clientX * dpr, y: e.clientY * dpr };
  touches.set(e.pointerId, p);
  touchSession ??= { max: 0, moved: 0, start: performance.now(), x: p.x, y: p.y };
  touchSession.max = Math.max(touchSession.max, touches.size);
  if (touches.size === 1) smudge = { pending: true, id: e.pointerId, x: p.x, y: p.y };
  else if (touches.size === 2) { endSmudge(); startGesture(); }
}

function touchMove(e) {
  const p = touches.get(e.pointerId);
  if (!p) return;
  const nx = e.clientX * dpr, ny = e.clientY * dpr;
  touchSession.moved += Math.hypot(nx - p.x, ny - p.y);
  p.x = nx; p.y = ny;
  if (gesture) { if (touches.size >= 2) updateGesture(); return; }
  if (!smudge || smudge.id !== e.pointerId) return;
  if (smudge.pending) {
    if (Math.hypot(nx - smudge.x, ny - smudge.y) < SMUDGE_START_CSS * dpr) return;
    sheet.beginRecord();
    const s = new SmudgeStroke(sheet);
    const o = toSheet(smudge.x / dpr, smudge.y / dpr);
    s.addSample(o.x, o.y);
    smudge = { id: e.pointerId, stroke: s };
  }
  const t0 = performance.now();
  const events = (e.getCoalescedEvents && e.getCoalescedEvents()) || [];
  const d0 = smudge.stroke.dabs;
  for (const ev of events.length ? events : [e]) { const q = toSheet(ev.clientX, ev.clientY); smudge.stroke.addSample(q.x, q.y); }
  flush();
  recordTiming(performance.now() - t0, smudge.stroke.dabs - d0, events.length || 1);
}

function touchUp(e) {
  if (!touches.has(e.pointerId)) return;
  touches.delete(e.pointerId);
  if (smudge && smudge.id === e.pointerId) endSmudge();
  if (gesture && touches.size < 2) { gesture = null; settleView(); }
  if (touches.size > 0) return;
  const s = touchSession; touchSession = null; smudge = null;
  const tap = performance.now() - s.start < TAP_MS && s.moved < TAP_MOVE_CSS * dpr;
  if (!tap) return;
  if (s.max === 2) undo();
  else if (s.max === 3) redo();
  else if (s.max === 1) cornerTap(s.x / dpr, s.y / dpr);
}

function endSmudge() {
  if (smudge && smudge.stroke) sheet.endRecord();
  smudge = null;
}

function twoTouches() { const it = touches.values(); return [it.next().value, it.next().value]; }

function startGesture() {
  const [a, b] = twoTouches();
  const mid = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
  gesture = { zoom0: state.zoom, d0: Math.max(1, Math.hypot(a.x - b.x, a.y - b.y)), anchor: toSheet(mid.x / dpr, mid.y / dpr) };
}

function updateGesture() {   // the sheet point under the first midpoint stays under the current midpoint
  const [a, b] = twoTouches();
  const mid = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }, d = Math.hypot(a.x - b.x, a.y - b.y);
  state.zoom = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, gesture.zoom0 * d / gesture.d0));
  state.view.x = gesture.anchor.x - mid.x / state.zoom;
  state.view.y = gesture.anchor.y - mid.y / state.zoom;
  queueRedraw();
}

// ---------------------------------------------------------------- pointer routing
function onPointerDown(e) {
  if (e.pointerType === 'touch' || (e.pointerType === 'mouse' && e.shiftKey)) touchDown(e);
  else penDown(e);
}
function onPointerMove(e) { if (touches.has(e.pointerId)) touchMove(e); else penMove(e); }
function onPointerUp(e) { if (touches.has(e.pointerId)) touchUp(e); else penUp(e); }

canvas.addEventListener('pointerdown', onPointerDown);
canvas.addEventListener('pointermove', onPointerMove);
canvas.addEventListener('pointerup', onPointerUp);
canvas.addEventListener('pointercancel', onPointerUp);
for (const type of ['touchstart', 'touchmove', 'touchend', 'gesturestart', 'gesturechange', 'gestureend']) {
  document.addEventListener(type, (e) => { if (!e.target.closest || !e.target.closest('.panel')) e.preventDefault(); }, { passive: false });
}
document.addEventListener('contextmenu', (e) => e.preventDefault());
window.addEventListener('resize', resize);

// desktop testing only: arrows pan, +/- zoom, z/y undo/redo, e eraser
window.addEventListener('keydown', (e) => {
  const step = 120 / state.zoom;
  if (e.key === 'ArrowLeft') state.view.x -= step; else if (e.key === 'ArrowRight') state.view.x += step;
  else if (e.key === 'ArrowUp') state.view.y -= step; else if (e.key === 'ArrowDown') state.view.y += step;
  else if (e.key === '+' || e.key === '=') zoomAbout(1.25); else if (e.key === '-') zoomAbout(0.8);
  else if (e.key === 'z') return undo(); else if (e.key === 'y') return redo();
  else if (e.key === 'e') return setEraser(!state.eraser);
  else if (e.key === 'd') return setDebug(!state.debug);
  else if (e.key === 'g') return cycleGrid();
  else return;
  settleView();
});
function zoomAbout(f) {
  const cx = canvas.width / 2, cy = canvas.height / 2, a = toSheet(cx / dpr, cy / dpr);
  state.zoom = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, state.zoom * f));
  state.view.x = a.x - cx / state.zoom; state.view.y = a.y - cy / state.zoom;
}

// ---------------------------------------------------------------- debug overlay
let cornerTaps = 0, cornerTimer = 0;
function cornerTap(cssX, cssY) {
  if (cssX > CORNER_CSS || cssY > CORNER_CSS) return;
  cornerTaps++; clearTimeout(cornerTimer); cornerTimer = setTimeout(() => (cornerTaps = 0), 600);
  if (cornerTaps >= 3) { cornerTaps = 0; setDebug(!state.debug); }
}
function setDebug(on) { state.debug = on; $('#debug').hidden = !on; if (on) $('#debug').textContent = 'debug on: draw to measure'; }
function recordTiming(ms, dabs, samples) {
  stats.evMs = ms; stats.evAvg += (ms - stats.evAvg) * 0.1; stats.dabs += dabs; stats.samples += samples;
  const now = performance.now();
  if (now - stats.lastTick > 1000) {
    const s = (now - stats.lastTick) / 1000;
    stats.dabsPerS = Math.round(stats.dabs / s); stats.samplesPerS = Math.round(stats.samples / s);
    stats.dabs = stats.samples = 0; stats.lastTick = now;
  }
  if (state.debug) {
    $('#debug').textContent = `${ms.toFixed(2)} ms/event (avg ${stats.evAvg.toFixed(2)})  ${stats.dabsPerS} dabs/s  ${stats.samplesPerS} samples/s  ` +
      `tiles ${sheet.tiles.size}  zoom ${state.zoom.toFixed(2)}  dpr ${dpr}  ${fastPath() ? 'putImageData' : 'drawImage'}`;
  }
}

// ---------------------------------------------------------------- UI
const bar = $('#bar');
function currentSettings() { return state.settings[state.preset]; }

function syncBar() {
  for (const b of bar.querySelectorAll('[data-preset]')) b.classList.toggle('active', !state.eraser && b.dataset.preset === state.preset);
  $('#eraser').classList.toggle('active', state.eraser);
  for (const b of bar.querySelectorAll('[data-colour]')) b.classList.toggle('active', Number(b.dataset.colour) === state.colour);
  $('#grid-btn').classList.toggle('active', state.grid !== 'off');
  $('#grid-btn').textContent = state.grid === 'dots' ? '⁙' : '#';
}
function setPreset(name) { state.preset = name; state.eraser = false; store.set('preset', name); syncBar(); }
function setEraser(on) { state.eraser = on; syncBar(); }
function setColour(i) { state.colour = i; state.eraser = false; store.set('colour', i); syncBar(); }

let pressTimer = 0;
for (const b of bar.querySelectorAll('[data-preset]')) {
  b.addEventListener('pointerdown', (e) => {
    e.stopPropagation();
    const active = !state.eraser && b.dataset.preset === state.preset;
    setPreset(b.dataset.preset);
    clearTimeout(pressTimer);
    if (active) pressTimer = setTimeout(openPanel, LONG_PRESS_MS);
  });
  for (const t of ['pointerup', 'pointercancel', 'pointerleave']) b.addEventListener(t, () => clearTimeout(pressTimer));
}
for (const b of bar.querySelectorAll('[data-colour]')) {
  b.style.setProperty('--dot', `rgb(${COLOURS[b.dataset.colour].map((k) => Math.round(k * 255)).join(',')})`);
  b.addEventListener('pointerdown', (e) => { e.stopPropagation(); setColour(Number(b.dataset.colour)); });
}
$('#eraser').addEventListener('pointerdown', (e) => { e.stopPropagation(); setEraser(!state.eraser); });
$('#grid-btn').addEventListener('pointerdown', (e) => { e.stopPropagation(); cycleGrid(); });
$('#undo').addEventListener('pointerdown', (e) => { e.stopPropagation(); undo(); });
$('#new').addEventListener('pointerdown', (e) => { e.stopPropagation(); newSheet(); });
$('#send').addEventListener('pointerdown', (e) => { e.stopPropagation(); openSend(); });
for (const el of document.querySelectorAll('.panel')) el.addEventListener('pointerdown', (e) => e.stopPropagation());
for (const b of document.querySelectorAll('[data-close]')) b.addEventListener('pointerdown', (e) => { e.stopPropagation(); b.closest('.panel').hidden = true; });

// settings panel: div sliders, dragged with pencil or finger
const panel = $('#panel');
function openPanel() {
  panel.hidden = false;
  $('#panel-title').textContent = state.preset;
  const host = $('#sliders'); host.textContent = '';
  for (const [key, label, min, max] of SLIDERS) host.appendChild(makeSlider(key, label, min, max));
}
function sliderValue(key) {
  const v = currentSettings()[key];
  return v ?? PRESETS[state.preset][key];
}
function makeSlider(key, label, min, max) {
  const row = document.createElement('div'); row.className = 'slider';
  const name = document.createElement('div'); name.className = 'slider-label';
  const track = document.createElement('div'); track.className = 'track';
  const fill = document.createElement('div'); fill.className = 'fill';
  track.appendChild(fill); row.append(name, track);
  const show = (v) => { name.textContent = `${label}  ${v.toFixed(2)}`; fill.style.width = `${((v - min) / (max - min)) * 100}%`; };
  show(sliderValue(key));
  const set = (e) => {
    const r = track.getBoundingClientRect();
    const v = min + Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)) * (max - min);
    currentSettings()[key] = v; store.set('settings', state.settings); show(v);
  };
  track.addEventListener('pointerdown', (e) => { try { track.setPointerCapture(e.pointerId); } catch { /* stale id */ } set(e); });
  track.addEventListener('pointermove', (e) => { if (e.buttons || e.pressure > 0) set(e); });
  return row;
}
$('#reset').addEventListener('pointerdown', () => { state.settings[state.preset] = { ...DEFAULT_SETTINGS }; store.set('settings', state.settings); openPanel(); });

let toastTimer = 0;
function toast(msg, ms = 2600) {
  const el = $('#toast'); el.textContent = msg; el.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => (el.hidden = true), ms);
}

// ---------------------------------------------------------------- sheets: autosave, load, new
let saving = false;
async function autosave() {
  if (saving) return;
  const dirty = [...sheet.tiles.values()].filter((t) => t.saveDirty);
  const gone = [...sheet.deleted];
  if (!dirty.length && !gone.length) return;
  saving = true;
  const id = state.sheetId, url = (tx, ty) => `/tile?sheet=${encodeURIComponent(id)}&tx=${tx}&ty=${ty}`;
  try {
    for (const key of gone) {
      const [tx, ty] = key.split(',').map(Number);
      const r = await fetch(url(tx, ty), { method: 'DELETE' });
      if (!r.ok && r.status !== 404) throw new Error(`delete ${key}: ${r.status}`);
      if (id === state.sheetId) sheet.deleted.delete(key);
    }
    for (const t of dirty) {
      t.saveDirty = false;
      uploadTile(t);
      const blob = await new Promise((res) => t.canvas.toBlob(res, 'image/png'));
      const r = await fetch(url(t.tx, t.ty), { method: 'POST', headers: { 'Content-Type': 'image/png' }, body: blob });
      if (!r.ok) throw new Error(`tile ${t.tx},${t.ty}: ${r.status}`);
    }
  } catch (err) {
    if (id === state.sheetId) for (const t of dirty) t.saveDirty = true;
    toast('autosave failed: ' + err.message);
  } finally { saving = false; }
}

async function loadSheet() {
  try {
    const info = await (await fetch(`/sheet?sheet=${encodeURIComponent(state.sheetId)}`)).json();
    const scratch = document.createElement('canvas'); scratch.width = scratch.height = TILE;
    const sctx = scratch.getContext('2d', { willReadFrequently: true });
    for (const [tx, ty] of info.tiles || []) {
      const r = await fetch(`/tile?sheet=${encodeURIComponent(state.sheetId)}&tx=${tx}&ty=${ty}`);
      if (!r.ok) continue;
      const bmp = await createImageBitmap(await r.blob());
      sctx.clearRect(0, 0, TILE, TILE); sctx.drawImage(bmp, 0, 0);
      sheet.tile(tx, ty).set(sctx.getImageData(0, 0, TILE, TILE).data);
      const t = sheet.tiles.get(sheet.key(tx, ty));
      t.canvasDirty = [0, 0, TILE - 1, TILE - 1]; t.saveDirty = false;
    }
    redrawAll();
    if (info.tiles && info.tiles.length) toast(`sheet ${state.sheetId}: ${info.tiles.length} tiles`);
  } catch (err) { toast('could not load sheet: ' + err.message); }
}

async function newSheet() {
  await autosave();                                   // the old sheet keeps its last strokes
  await saveThumb();
  const d = new Date(), pad = (n) => String(n).padStart(2, '0');
  state.sheetId = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}_${pad(d.getHours())}-${pad(d.getMinutes())}-${pad(d.getSeconds())}`;
  store.set('sheet', state.sheetId);
  sheet.clear(); state.view = { x: 0, y: 0 }; state.zoom = 1;
  redrawAll(); toast('new sheet');
}

// ---------------------------------------------------------------- send
function drawnBounds() {   // per-pixel bounding box of everything that is not paper
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  const [pr, pg, pb] = PAPER_RGB;
  for (const t of sheet.tiles.values()) {
    const d = t.data;
    for (let y = 0; y < TILE; y++) for (let x = 0; x < TILE; x++) {
      const i = (y * TILE + x) * 4;
      if (Math.abs(d[i] - pr) > 2 || Math.abs(d[i + 1] - pg) > 2 || Math.abs(d[i + 2] - pb) > 2) {
        const sx = t.tx * TILE + x, sy = t.ty * TILE + y;
        if (sx < x0) x0 = sx; if (sx > x1) x1 = sx; if (sy < y0) y0 = sy; if (sy > y1) y1 = sy;
      }
    }
  }
  return x0 === Infinity ? null : [x0 - EXPORT_MARGIN, y0 - EXPORT_MARGIN, x1 + EXPORT_MARGIN, y1 + EXPORT_MARGIN];
}

async function exportPng(maxPx = MAX_EXPORT_PX) {
  const b = drawnBounds();
  if (!b) return null;
  let w = b[2] - b[0] + 1, h = b[3] - b[1] + 1;
  const s = Math.min(1, Math.sqrt(maxPx / (w * h)));
  const out = document.createElement('canvas'); out.width = Math.round(w * s); out.height = Math.round(h * s);
  const octx = out.getContext('2d');
  octx.fillStyle = paperCss; octx.fillRect(0, 0, out.width, out.height);
  for (const t of sheet.tiles.values()) {
    uploadTile(t);
    octx.drawImage(t.canvas, (t.tx * TILE - b[0]) * s, (t.ty * TILE - b[1]) * s, TILE * s, TILE * s);
  }
  return new Promise((res) => out.toBlob(res, 'image/png'));
}

async function openSend() {
  const list = $('#sessions'); list.textContent = 'looking…';
  $('#send-panel').hidden = false;
  try {
    const sessions = await api.sessions();
    const last = store.get('lastSession', null);
    sessions.sort((a, b) => (b.name === last) - (a.name === last) || a.name.localeCompare(b.name));
    list.textContent = '';
    if (!sessions.length) list.textContent = 'no named sessions running';
    for (const s of sessions) {
      const b = document.createElement('button'); b.className = 'session';
      b.textContent = s.name + (s.status && s.status !== 'idle' ? ` · ${s.status}` : '');
      b.addEventListener('pointerdown', (e) => { e.stopPropagation(); $('#send-panel').hidden = true; sendTo(s.name); });
      list.appendChild(b);
    }
  } catch (err) { list.textContent = 'server unreachable: ' + err.message; }
}

async function sendTo(name) {
  try {
    const png = await exportPng();
    if (!png) return toast('nothing drawn yet');
    toast(`sending to ${name}…`);
    const j = await api.send(png, name, { sheet: state.sheetId });
    if (j.delivered) { store.set('lastSession', name); pendingSends.set(j.id, name); }
    toast(j.delivered ? `sent to ${name}` : `saved, not delivered: ${j.detail}`, 4000);
    saveThumb();
  } catch (err) { toast('send failed: ' + err.message, 4000); }
}

// ---------------------------------------------------------------- the session talks back: seen + replies
const pendingSends = new Map();          // send id -> session name, until the session reads the PNG

async function saveThumb() {             // small picture of the sheet for the gallery; never blocks drawing
  try {
    const png = await exportPng(THUMB_PX);
    if (png) await api.putThumb(state.sheetId, png);
  } catch { /* gallery only */ }
}

function showReply(reply) {
  let box = $('#reply');
  if (!box) {
    box = document.createElement('div'); box.id = 'reply';
    Object.assign(box.style, {
      position: 'fixed', right: '16px', top: 'calc(16px + env(safe-area-inset-top))', maxWidth: 'min(46vw, 520px)',
      maxHeight: '70vh', overflow: 'auto', background: 'rgba(255,255,255,0.96)', color: '#222', borderRadius: '12px',
      padding: '14px 16px', font: '15px/1.45 -apple-system, Helvetica, sans-serif', boxShadow: '0 4px 24px rgba(0,0,0,0.18)',
      zIndex: 50, touchAction: 'pan-y', whiteSpace: 'pre-wrap', wordBreak: 'break-word',
    });
    box.addEventListener('pointerdown', (e) => { e.stopPropagation(); if (e.target === box || e.target.tagName !== 'IMG') box.remove(); });
    document.body.appendChild(box);
  }
  box.textContent = '';
  const who = document.createElement('div'); who.textContent = `${reply.from} · ${reply.time.slice(11, 16)}`;
  Object.assign(who.style, { fontSize: '12px', opacity: 0.6, marginBottom: '6px' });
  box.appendChild(who);
  if (reply.text) { const p = document.createElement('div'); p.textContent = reply.text; box.appendChild(p); }
  if (reply.image) {
    const img = document.createElement('img'); img.src = reply.image; img.alt = 'reply image';
    Object.assign(img.style, { display: 'block', maxWidth: '100%', marginTop: reply.text ? '10px' : 0, borderRadius: '6px' });
    box.appendChild(img);
  }
  store.set('lastReply', reply.id);
}

subscribe((e) => {
  if (e.type === 'seen' && pendingSends.has(e.id)) { pendingSends.delete(e.id); toast(`${e.session} saw your sketch`, 3500); }
  if (e.type === 'reply') showReply(e);
});
api.replies(1).then((list) => {                          // a reply that arrived while the page was closed
  if (list[0] && list[0].id !== store.get('lastReply', null)) showReply(list[0]);
}).catch(() => {});

// ---------------------------------------------------------------- go
resize();
syncBar();
loadSheet();
setInterval(autosave, AUTOSAVE_MS);
window.sketch = { state, stats, sheet, undo, redo, drawnBounds, exportPng, autosave, loadSheet, newSheet, setPreset, setEraser, setDebug,
  setGrid, settleView, zoomAbout, redrawAll, sendTo, toast, toSheet, dpr };   // for scripted tests
