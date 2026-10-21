// app.js — the rascunho app: the graphite sheet (sheet.js) under the interface (ui.js),
// gestures, view, autosave, gallery, and the send → seen → reply loop (client.js).
//
// Gestures: Pencil draws with the active tool · one finger smudges · two fingers pan
// and zoom · two-finger tap undo · three-finger tap redo. Mouse draws; shift+mouse
// acts as a finger (desktop testing). Keys (desktop): arrows pan, +/- zoom, z/y undo/redo.

import { createSheet, SS, TILE_DEV, PAPER_RGB, TOOLS, tiltToSpherical } from './sheet.js';
import { api, subscribe } from './client.js';

const ui = window.rascunhoUI;
const dpr = Math.min(window.devicePixelRatio || 1, 3);
const TOOL_IDS = { '2h': '2H', hb: 'HB', '4b': '4B', eraser: 'eraser' };   // ui id → engine tool
const SIZE_STEPS = [0.6, 1, 1.6, 2.4];                                    // S M L XL
const ZOOM_MIN = 0.25, ZOOM_MAX = 6;
const TAP_MS = 350, TAP_MOVE_CSS = 12;
const SMUDGE_START_CSS = 5;        // one finger must travel this far before it smudges (two-finger gestures start clean)
const AUTOSAVE_MS = 3000;
const THUMB_PX = 160000;
const SESSIONS_REFRESH_MS = 20000;

const store = {
  get(k, fallback) { try { const v = localStorage.getItem('rascunho.' + k); return v === null ? fallback : JSON.parse(v); } catch { return fallback; } },
  set(k, v) { try { localStorage.setItem('rascunho.' + k, JSON.stringify(v)); } catch { /* private mode */ } },
};
const debug = new URLSearchParams(location.search).has('debug');

// ---------------------------------------------------------------- canvas + view
const host = document.getElementById('sheet');
const canvas = document.createElement('canvas'); canvas.id = 'paper';
host.appendChild(canvas);
const ctx = canvas.getContext('2d', { alpha: false });
let rect = canvas.getBoundingClientRect();
const state = {
  view: { x: 0, y: 0 },            // device-px sheet coordinate at the screen's top-left
  zoom: 1,
  tool: 'hb', colour: '#2a2a2a', sizes: { '2h': 1, hb: 1, '4b': 1, eraser: 1 },
  sheetId: store.get('sheet', null),
};
const sheet = createSheet({ paper: 'noise' });

function resize() {
  canvas.width = Math.round(innerWidth * dpr); canvas.height = Math.round(innerHeight * dpr);
  canvas.style.width = innerWidth + 'px'; canvas.style.height = innerHeight + 'px';
  rect = canvas.getBoundingClientRect();
  redrawAll();
}
const toDev = (cx, cy) => ({     // client → device-px sheet space
  x: (cx - rect.left) * (canvas.width / rect.width) / state.zoom + state.view.x,
  y: (cy - rect.top) * (canvas.height / rect.height) / state.zoom + state.view.y,
});
const paperCss = `rgb(${PAPER_RGB.join(',')})`;

// ---------------------------------------------------------------- underlay: a picture under the sheet, drawn over
// A session puts a PNG/JPEG under a sheet (POST /underlay, tools/place.py). It sits at the sheet origin,
// fitted into UNDERLAY_FIT device px (the same on every device, so the drawing stays registered), and the
// graphite multiplies over it like pencil on a print. Sends and thumbnails include it.
const UNDERLAY_FIT = { w: 2180, h: 1640 };
let underlay = null;             // {img, url, x, y, w, h} device px in sheet space
function drawUnderlay(clip) {    // the part of the underlay inside a sheet-space rect (device px)
  if (!underlay) return;
  const u = underlay, z = state.zoom;
  const x0 = Math.max(u.x, clip.x0), y0 = Math.max(u.y, clip.y0), x1 = Math.min(u.x + u.w, clip.x1), y1 = Math.min(u.y + u.h, clip.y1);
  if (x0 >= x1 || y0 >= y1) return;
  const k = u.img.naturalWidth / u.w;                    // image px per device px
  ctx.drawImage(u.img, (x0 - u.x) * k, (y0 - u.y) * k, (x1 - x0) * k, (y1 - y0) * k,
    (x0 - state.view.x) * z, (y0 - state.view.y) * z, (x1 - x0) * z, (y1 - y0) * z);
}
const loadImage = (url) => new Promise((res, rej) => { const img = new Image(); img.onload = () => res(img); img.onerror = rej; img.src = url; });
async function setUnderlay(url) {
  underlay = null;
  if (url) {
    try {
      const img = await loadImage(`${url}?t=${Date.now()}`);
      const s = Math.min(UNDERLAY_FIT.w / img.naturalWidth, UNDERLAY_FIT.h / img.naturalHeight);
      underlay = { img, url, x: 0, y: 0, w: img.naturalWidth * s, h: img.naturalHeight * s };
    } catch { ui.toast('could not load the picture'); }
  }
  queueRedraw();
}
function showWhole(u) {           // zoom out if needed and centre a sheet rect on the screen
  state.zoom = Math.min(1, canvas.width * 0.92 / u.w, canvas.height * 0.86 / u.h);
  state.view.x = u.x + (u.w - canvas.width / state.zoom) / 2;
  state.view.y = u.y + (u.h - canvas.height / state.zoom) / 2;
  settleView();
}

function drawTileRect(t, r) {    // r: device px within the tile
  const z = state.zoom, w = r.x1 - r.x0, h = r.y1 - r.y0;
  const sx = t.tx * TILE_DEV + r.x0, sy = t.ty * TILE_DEV + r.y0;      // sheet device px
  const dx = (sx - state.view.x) * z, dy = (sy - state.view.y) * z;
  ctx.fillStyle = paperCss; ctx.fillRect(dx, dy, w * z, h * z);        // paper, the picture if any, then the tile multiplied over both
  drawUnderlay({ x0: sx, y0: sy, x1: sx + w, y1: sy + h });
  ctx.globalCompositeOperation = 'multiply';
  ctx.drawImage(t.canvas, r.x0, r.y0, w, h, dx, dy, w * z, h * z);
  ctx.globalCompositeOperation = 'source-over';
}
function redrawAll() {
  ctx.fillStyle = paperCss; ctx.fillRect(0, 0, canvas.width, canvas.height);
  sheet.flush();                                           // composite anything pending first
  const z = state.zoom, v = state.view;
  drawUnderlay({ x0: v.x, y0: v.y, x1: v.x + canvas.width / z, y1: v.y + canvas.height / z });
  ctx.globalCompositeOperation = 'multiply';               // tiles are white where untouched
  const x0 = Math.floor(v.x / TILE_DEV), y0 = Math.floor(v.y / TILE_DEV);
  const x1 = Math.ceil((v.x + canvas.width / z) / TILE_DEV), y1 = Math.ceil((v.y + canvas.height / z) / TILE_DEV);
  for (const t of sheet.tiles.values()) {
    if (t.tx < x0 || t.tx >= x1 || t.ty < y0 || t.ty >= y1) continue;
    ctx.drawImage(t.canvas, (t.tx * TILE_DEV - v.x) * z, (t.ty * TILE_DEV - v.y) * z, TILE_DEV * z, TILE_DEV * z);
  }
  ctx.globalCompositeOperation = 'source-over';
}
const flush = () => sheet.flush(drawTileRect);
let redrawQueued = false;
function queueRedraw() { if (redrawQueued) return; redrawQueued = true; requestAnimationFrame(() => { redrawQueued = false; redrawAll(); }); }
function settleView() {           // snap near-1 zoom to exactly 1 and integer offsets: crisp tiles
  if (Math.abs(state.zoom - 1) < 0.04) { state.zoom = 1; state.view.x = Math.round(state.view.x); state.view.y = Math.round(state.view.y); }
  queueRedraw();
}

// ---------------------------------------------------------------- tools
function applyTool() {
  const name = TOOL_IDS[state.tool] || 'HB';
  sheet.setTool(name, { size: TOOLS[name].size * SIZE_STEPS[state.sizes[state.tool] ?? 1] * SS / 4 });
  sheet.setColour(state.colour);
}
function useSmudge() { sheet.setTool('smudge', { size: TOOLS.smudge.size * SS / 4 }); }

// ---------------------------------------------------------------- pencil (and mouse)
let penId = null, penLast = null, timing = { ms: 0, n: 0 };
function sample(ev, pointerType) {
  const d = toDev(ev.clientX, ev.clientY);
  let altitude, azimuth;
  if (typeof ev.altitudeAngle === 'number') { altitude = ev.altitudeAngle; azimuth = ev.azimuthAngle; }
  else ({ altitude, azimuth } = tiltToSpherical(ev.tiltX || 0, ev.tiltY || 0));
  const pressure = pointerType === 'pen' ? ev.pressure : 0.5;
  return [d.x * SS, d.y * SS, pressure, altitude, azimuth];
}
function capture(e) { try { canvas.setPointerCapture(e.pointerId); } catch { /* synthetic pointer */ } }
function penDown(e) {
  if (penId !== null) return;
  if (touches.size) { endSmudge(); touches.clear(); touchSession = null; gesture = null; }   // the Pencil wins over a resting finger
  penId = e.pointerId; capture(e);
  applyTool();
  penLast = sample(e, e.pointerType);
  sheet.strokeBegin(...penLast);
  flush();
}
function penMove(e) {
  if (e.pointerId !== penId) return;
  const t0 = performance.now();
  const list = (e.getCoalescedEvents && e.getCoalescedEvents()) || [];
  for (const ev of list.length ? list : [e]) { penLast = sample(ev, e.pointerType); sheet.strokeMove(...penLast); }
  flush();
  tick(performance.now() - t0);
}
function penUp(e) {
  if (e.pointerId !== penId) return;
  const s = e.type === 'pointercancel' ? penLast : sample(e, e.pointerType);   // a cancel may carry no position
  sheet.strokeEnd(s[0], s[1], 0, s[3], s[4]);
  flush(); penId = null; penLast = null;
  scheduleAutosave();
}

// ---------------------------------------------------------------- fingers: smudge, pan/zoom, taps
const touches = new Map();         // pointerId → {x, y} device px
let touchSession = null, smudge = null, gesture = null;
function touchDown(e) {
  if (penId !== null) return;                                 // Pencil is down: fingers are the palm
  capture(e);
  const p = { x: e.clientX * dpr, y: e.clientY * dpr };
  touches.set(e.pointerId, p);
  touchSession ??= { max: 0, moved: 0, start: performance.now() };
  touchSession.max = Math.max(touchSession.max, touches.size);
  if (touches.size === 1) smudge = { pending: true, id: e.pointerId, x: p.x, y: p.y, cx: e.clientX, cy: e.clientY };
  else { endSmudge(); startGesture(); }                        // two fingers pan/zoom; a third re-anchors, no jump
}
function touchMove(e) {
  const p = touches.get(e.pointerId); if (!p) return;
  const nx = e.clientX * dpr, ny = e.clientY * dpr;
  touchSession.moved += Math.hypot(nx - p.x, ny - p.y);
  p.x = nx; p.y = ny;
  if (gesture) { if (touches.size >= 2) updateGesture(); return; }
  if (!smudge || smudge.id !== e.pointerId) return;
  if (smudge.pending) {
    if (Math.hypot(nx - smudge.x, ny - smudge.y) < SMUDGE_START_CSS * dpr) return;
    useSmudge();
    const s = sample({ clientX: smudge.cx, clientY: smudge.cy }, 'touch');
    sheet.strokeBegin(s[0], s[1], 0.5, Math.PI / 2, 0);
    smudge = { id: e.pointerId, active: true, last: s };
  }
  const t0 = performance.now();
  const list = (e.getCoalescedEvents && e.getCoalescedEvents()) || [];
  for (const ev of list.length ? list : [e]) { const s = sample(ev, 'touch'); smudge.last = s; sheet.strokeMove(s[0], s[1], 0.5, Math.PI / 2, 0); }
  flush();
  tick(performance.now() - t0);
}
function touchUp(e) {
  if (!touches.has(e.pointerId)) return;
  touches.delete(e.pointerId);
  if (smudge && smudge.id === e.pointerId) endSmudge();
  if (gesture) { if (touches.size < 2) { gesture = null; settleView(); } else startGesture(); }   // a finger left: re-anchor on the pair that stays
  if (touches.size > 0) return;
  const s = touchSession; touchSession = null; smudge = null;
  const tap = performance.now() - s.start < TAP_MS && s.moved < TAP_MOVE_CSS * dpr;
  if (!tap) return;
  if (s.max === 2) undo(); else if (s.max === 3) redo();
}
function endSmudge() {
  if (smudge && smudge.active) {
    const l = smudge.last;                                   // lift where the finger is (ending at 0,0 streaked toward the corner)
    sheet.strokeEnd(l[0], l[1], 0, Math.PI / 2, 0); flush(); applyTool(); scheduleAutosave();
  }
  smudge = null;
}
function twoTouches() { const it = touches.values(); return [it.next().value, it.next().value]; }
function startGesture() {
  const [a, b] = twoTouches();
  const mid = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
  gesture = { zoom0: state.zoom, d0: Math.max(1, Math.hypot(a.x - b.x, a.y - b.y)), anchor: toDev(mid.x / dpr, mid.y / dpr) };
}
function updateGesture() {        // the sheet point under the first midpoint stays under the current midpoint
  const [a, b] = twoTouches();
  const mid = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }, d = Math.hypot(a.x - b.x, a.y - b.y);
  state.zoom = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, gesture.zoom0 * d / gesture.d0));
  state.view.x = gesture.anchor.x - mid.x / state.zoom;
  state.view.y = gesture.anchor.y - mid.y / state.zoom;
  queueRedraw();
}

function undo() { if (sheet.undo()) { flush(); scheduleAutosave(); } else ui.toast('nothing to undo'); }
function redo() { if (sheet.redo()) { flush(); scheduleAutosave(); } }

// ---------------------------------------------------------------- pointer routing
const isFinger = (e) => e.pointerType === 'touch' || (e.pointerType === 'mouse' && e.shiftKey);
canvas.addEventListener('pointerdown', (e) => { e.preventDefault(); if (isFinger(e)) touchDown(e); else penDown(e); });
canvas.addEventListener('pointermove', (e) => { if (touches.has(e.pointerId)) touchMove(e); else penMove(e); });
canvas.addEventListener('pointerup', (e) => { if (touches.has(e.pointerId)) touchUp(e); else penUp(e); });
canvas.addEventListener('pointercancel', (e) => { if (touches.has(e.pointerId)) touchUp(e); else penUp(e); });
for (const type of ['touchstart', 'touchmove', 'touchend', 'gesturestart', 'gesturechange', 'gestureend']) {
  document.addEventListener(type, (e) => { if (!e.target.closest || !e.target.closest('#grid')) e.preventDefault(); }, { passive: false });
}
document.addEventListener('contextmenu', (e) => e.preventDefault());
document.addEventListener('visibilitychange', () => {       // app switch / lock within 3 s of a stroke: save now
  if (document.hidden) { clearTimeout(autosaveTimer); autosaveTimer = 0; autosave(); saveThumb(); }
});
window.addEventListener('resize', resize);
window.visualViewport?.addEventListener('resize', resize);
window.addEventListener('keydown', (e) => {               // desktop testing
  const step = 120 / state.zoom;
  if (e.key === 'ArrowLeft') state.view.x -= step; else if (e.key === 'ArrowRight') state.view.x += step;
  else if (e.key === 'ArrowUp') state.view.y -= step; else if (e.key === 'ArrowDown') state.view.y += step;
  else if (e.key === '+' || e.key === '=') zoomAbout(1.25); else if (e.key === '-') zoomAbout(0.8);
  else if (e.key === 'z') return undo(); else if (e.key === 'y') return redo();
  else return;
  settleView();
});
function zoomAbout(f) {
  const cx = canvas.width / 2, cy = canvas.height / 2, a = toDev(cx / dpr, cy / dpr);
  state.zoom = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, state.zoom * f));
  state.view.x = a.x - cx / state.zoom; state.view.y = a.y - cy / state.zoom;
}

// ---------------------------------------------------------------- debug readout (?debug)
let debugEl = null;
function tick(ms) {
  timing.ms = timing.ms * 0.9 + ms * 0.1; timing.n++;
  if (!debug) return;
  if (!debugEl) { debugEl = document.createElement('div'); debugEl.style.cssText = 'position:fixed;left:8px;top:8px;font:11px ui-monospace,monospace;color:#777;pointer-events:none;z-index:60'; document.body.appendChild(debugEl); }
  if ((timing.n & 7) === 0) debugEl.textContent = `${sheet.tool.name} ${ms.toFixed(2)} ms/event (avg ${timing.ms.toFixed(2)}) tiles ${sheet.tiles.size} zoom ${state.zoom.toFixed(2)}`;
}

// ---------------------------------------------------------------- sheets: autosave, load, new, gallery
let autosaveTimer = 0, savePromise = null;
function scheduleAutosave() { if (!autosaveTimer) autosaveTimer = setTimeout(autosave, AUTOSAVE_MS); }
function autosave() {               // one upload pass at a time; returns a promise that resolves true when the pass succeeded
  autosaveTimer = 0;
  if (!savePromise) savePromise = savePass().finally(() => { savePromise = null; });
  return savePromise;
}
async function savePass() {
  const id = state.sheetId, work = sheet.unsaved();
  if (!work.length) return true;
  try {
    for (const { t, k, gen } of work) {
      const blob = await sheet.layerPng(t, k);
      if (!blob) continue;
      await api.putTile(id, t.tx, t.ty, blob, k.slice(1));
      if (id === state.sheetId) sheet.markSaved(t, k, gen);    // a stroke that landed meanwhile keeps the layer unsaved
    }
    if (id === state.sheetId && sheet.hasUnsaved) scheduleAutosave();
    return true;
  } catch (err) { ui.toast('autosave failed: ' + err.message); scheduleAutosave(); return false; }
}
async function loadSheet(id) {
  try {
    const info = await api.sheet(id);
    if (id !== state.sheetId) return;
    await setUnderlay(info.underlay || null);
    if (underlay && id === state.sheetId) showWhole(underlay);
    const stillWanted = () => id === state.sheetId;
    await Promise.all((info.tiles || []).map(async ([tx, ty, layer]) => {    // all tiles in parallel, paint as they land
      const r = await fetch(api.tileUrl(id, tx, ty, layer));
      if (!r.ok) return;
      const blob = await r.blob();
      if (!stillWanted()) return;
      const how = await sheet.loadLayer(tx, ty, '#' + layer, blob, stillWanted);
      if (how === 'loaded') { const t = sheet.tiles.get(`${tx},${ty}`); if (t) sheet.markSaved(t, '#' + layer); }   // what we loaded is what is saved
      flush();
    }));
    if (stillWanted()) redrawAll();
  } catch (err) { ui.toast('could not load the sheet'); console.error(err); }
}
const newId = () => { const d = new Date(), p = (n) => String(n).padStart(2, '0'); return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}_${p(d.getHours())}-${p(d.getMinutes())}-${p(d.getSeconds())}`; };
async function saveThumb() {
  try { const png = await sheet.exportPng({ maxPx: THUMB_PX, underlay }); if (png) await api.putThumb(state.sheetId, png); } catch { /* gallery only */ }
}
async function leaveSheet() {     // flush everything of the current sheet to the server before switching
  clearTimeout(autosaveTimer); autosaveTimer = 0;
  for (let pass = 0; pass < 3 && sheet.hasUnsaved; pass++) {   // a pass already in flight may miss the newest strokes
    if (!(await autosave())) break;
  }
  await saveThumb();
}
async function newSheet() {
  await leaveSheet();
  sheet.clear(); underlay = null; state.sheetId = newId(); store.set('sheet', state.sheetId);
  state.view = { x: 0, y: 0 }; state.zoom = 1;
  redrawAll(); refreshGallery();
}
async function openSheet(id) {
  if (id === state.sheetId) return;
  await leaveSheet();
  sheet.clear(); underlay = null; state.sheetId = id; store.set('sheet', id);
  state.view = { x: 0, y: 0 }; state.zoom = 1;
  redrawAll(); await loadSheet(id);
}
async function refreshGallery() {
  try {
    const list = await api.sheets();
    ui.setSheets(list.map((s) => ({
      id: s.id,
      date: new Date(s.updated * 1000).toISOString().slice(0, 10),
      src: s.thumb ? `${api.thumbUrl(s.id)}?t=${Math.round(s.updated)}` : (s.underlay || undefined),   // a placed picture not yet drawn on shows itself
    })));
  } catch { /* offline: the gallery keeps what it has */ }
}

// ---------------------------------------------------------------- send → seen → reply
const pendingSends = new Map();
async function refreshSessions() {
  try {
    const names = (await api.sessions()).map((s) => s.name), last = store.get('lastSession', null);
    ui.setSessions(names, names.includes(last) ? last : null);     // a remembered session that is gone must not stay selected
  } catch { /* server down: keep the old list */ }
}
async function send(name) {
  try {
    const png = await sheet.exportPng({ underlay });
    if (!png) { ui.setSent(false, 'nothing drawn yet'); return; }
    const r = await api.send(png, name, { sheet: state.sheetId });
    ui.setSent(!!(r.ok && r.delivered), r.detail);
    if (r.delivered) { store.set('lastSession', name); pendingSends.set(r.id, name); }
    saveThumb();
  } catch (err) { ui.setSent(false, err.message); }
}
function showReply(reply) {       // a quiet card top-right: the session's words, and its picture if it sent one
  let box = document.getElementById('reply');
  if (!box) {
    box = document.createElement('div'); box.id = 'reply';
    box.addEventListener('pointerdown', (e) => { e.stopPropagation(); if (e.target.tagName !== 'IMG') box.remove(); });
    document.body.appendChild(box);
  }
  box.textContent = '';
  const who = document.createElement('div'); who.className = 'who'; who.textContent = `${reply.from} · ${reply.time.slice(11, 16)}`;
  box.appendChild(who);
  if (reply.text) { const p = document.createElement('div'); p.textContent = reply.text; box.appendChild(p); }
  if (reply.image) { const img = document.createElement('img'); img.src = reply.image; img.alt = ''; box.appendChild(img); }
  store.set('lastReply', reply.id);
}
async function onUnderlay(e) {    // a session placed a picture: on this sheet, refresh; elsewhere, open it unless a hand is on the glass
  const who = e.from || 'claude';
  if (e.sheet === state.sheetId) { await setUnderlay(e.url); if (underlay) showWhole(underlay); ui.toast(`${who} put a picture under this sheet`); return; }
  if (penId !== null || touches.size) { ui.toast(`${who} sent a picture to draw on: it is in ::`); refreshGallery(); return; }
  await openSheet(e.sheet);
  ui.toast(`${who} sent a picture to draw on` + (e.note ? `: ${e.note}` : ''));
  refreshGallery();
}
subscribe((e) => {
  if (e.type === 'seen' && pendingSends.has(e.id)) { pendingSends.delete(e.id); ui.toast(`${e.session} saw your drawing`); }
  if (e.type === 'reply') showReply(e);
  if (e.type === 'underlay') onUnderlay(e);
});

// ---------------------------------------------------------------- bind the interface
ui.onTool((id) => { state.tool = id; store.set('tool', id); applyTool(); });
ui.onSize((id, step) => { state.sizes[id] = step; applyTool(); });
ui.onColour((hex) => { state.colour = hex; store.set('colour', hex); applyTool(); });
ui.onUndo(undo);
ui.onNew(newSheet);
ui.onOpenSheet(openSheet);
ui.onGrid((mode) => store.set('grid', mode));
ui.onSession((name) => store.set('lastSession', name));
ui.onSend(send);
document.getElementById('gridbtn')?.addEventListener('pointerup', () => { leaveSheet().then(refreshGallery); });   // fresh thumbnails when the gallery opens
document.getElementById('session')?.addEventListener('pointerup', refreshSessions);                                  // fresh names when the list opens

async function start() {
  resize();
  await new Promise((r) => setTimeout(r, 0));          // let ui.js restore its localStorage state first
  const s = ui.state;
  state.tool = store.get('tool', s.tool || 'hb');
  state.colour = store.get('colour', s.colour || '#2a2a2a');
  state.sizes = { ...state.sizes, ...ui.sizes };
  ui.setTool(state.tool); ui.setColour(state.colour);
  const grid = store.get('grid', null); if (grid) ui.setGrid(grid);
  applyTool();
  if (!state.sheetId) { state.sheetId = newId(); store.set('sheet', state.sheetId); }
  await loadSheet(state.sheetId);
  refreshSessions(); refreshGallery();
  setInterval(refreshSessions, SESSIONS_REFRESH_MS);
  api.replies(1).then((list) => { if (list[0] && list[0].id !== store.get('lastReply', null)) showReply(list[0]); }).catch(() => {});
}
start();
window.rascunho = { sheet, state, api, redrawAll, undo, redo, send, get underlay() { return underlay; } };   // for tests
