// sketch — UI layer (design prototype, final). Spec: design/UI-SPEC.md (read that, not this file, to implement it on an engine).
// Pure DOM, no engine, no libraries. Loads palette.json; keeps all visual state itself; reports through hooks.
// Public API: window.sketchUI = {
//   onTool, onColour, onSize, onUndo, onNew, onSend, onSession, onOpenSheet, onGrid, onQuickChange,   // callbacks, each returns an unsubscribe
//   setSessions, setSheets, setSending, setSent, setQuick, setSize, setGrid, setTool, setColour, setMode,
//   openColours, closeColours, toast,
//   state, quick, sizes, colours                                                                     // getters
// }
// #sheet is the engine's: an empty full-screen div it replaces with its canvases. #aid (paper grid) and #ui (controls) sit above it.
// localStorage keys: sketch.quick, sketch.sizes, sketch.hint.undo.

// sketch — UI prototype. Pure DOM, no engine.
// All fake data lives in FAKE. The engine binds through window.sketchUI (bottom of file).

const FAKE = {
  sessions: ['book', 'today', 'oracle', 'sunrise'],
  connected: 'book',
  tool: 'hb',
  grid: 'off',          // paper grid: 'off' | 'dots' | 'lines'
  params: {            // 0..1, shown on long-press of the active pencil
    '2h':     { size: .18, hardness: .9,  grain: .25, smoothing: .5 },
    'hb':     { size: .35, hardness: .5,  grain: .45, smoothing: .5 },
    '4b':     { size: .7,  hardness: .15, grain: .7,  smoothing: .4 },
    'eraser': { size: .5,  hardness: .3,  grain: .1,  smoothing: .6 },
  },
  paramNames: ['hardness', 'grain', 'smoothing'],   // size is set by sliding on the tool word
  doubleTapMs: 320,                                 // two taps within this reset a tool's size to M
  sizeStepPx: 24,                                   // vertical travel per size step
  sizes: { '2h': 1, 'hb': 1, '4b': 1, 'eraser': 1 },   // default step 1 of 0..3 (S, M, L, XL)
  sheets: (() => {                 // newest first, {id, date, src?}
    const out = [], d = new Date('2026-10-20');
    const gaps = [0, 0, 1, 1, 2, 3, 1, 4, 2, 6, 1, 5, 3];
    gaps.forEach((g, i) => { d.setDate(d.getDate() - g); out.push({ id: 'sheet-' + (13 - i), date: d.toISOString().slice(0, 10) }); });
    return out;
  })(),
  longPressMs: 420,
  toastMs: 1800,
};

// ---------- hooks ----------
const hooks = { tool: [], colour: [], undo: [], new: [], send: [], session: [], openSheet: [], grid: [], quickChange: [], size: [] };
const on = name => fn => { hooks[name].push(fn); return () => { hooks[name] = hooks[name].filter(f => f !== fn); }; };
const emit = (name, ...args) => hooks[name].forEach(fn => { try { fn(...args); } catch (e) { console.error(e); } });

// ---------- state ----------
const state = {
  mode: 'draw',
  tool: FAKE.tool,
  colour: null, quick: [], chosen: null, colourMap: {}, palettes: [],
  grid: FAKE.grid,
  session: FAKE.connected,
  sessions: FAKE.sessions.slice(),
  sheets: FAKE.sheets.slice(),
  params: JSON.parse(JSON.stringify(FAKE.params)),
  sizes: (() => { try { const s = JSON.parse(localStorage.getItem('sketch.sizes')); if (s && typeof s === 'object') return { ...FAKE.sizes, ...s }; } catch (e) {} return { ...FAKE.sizes }; })(),
  sending: false,
};

const $ = id => document.getElementById(id);
const body = document.body;
const els = {
  sheet: $('sheet'), wash: $('wash'), new: $('new'), undo: $('undo'), undoHint: $('undo-hint'), back: $('back'),
  colours: $('colours'), colourswrap: $('colourswrap'), palette: $('palette'), tools: $('tools'), params: $('params'),
  gridbtn: $('gridbtn'), aidbtn: $('aidbtn'), session: $('session'), sessions: $('sessions'), send: $('send'), sendto: $('sendto'), sendgroup: $('sendgroup'),
  toast: $('toast'), grid: $('grid'), sheets: document.querySelector('#grid .sheets'),
};

// a light press feedback for line glyphs
function pressable(el) {
  el.addEventListener('pointerdown', () => el.classList.add('pressed'));
  const up = () => el.classList.remove('pressed');
  el.addEventListener('pointerup', up); el.addEventListener('pointercancel', up); el.addEventListener('pointerleave', up);
}
document.addEventListener('contextmenu', e => e.preventDefault());

// ---------- colours ----------
// palette.json is the single source. the row shows five quick colours (editable, persisted),
// a live sixth "chosen" slot, and a hollow dot that opens the full list.
const QUICK_KEY = 'sketch.quick';
const norm = hex => String(hex || '').trim().toLowerCase();
function fallbackPalette() {
  const cs = getComputedStyle(document.documentElement);
  return { _fallback: true, black: { name: 'black', hex: cs.getPropertyValue('--c-quick-1').trim() },
           quick: [1, 2, 3, 4, 5].map(i => cs.getPropertyValue('--c-quick-' + i).trim()), palettes: [] };
}
async function loadPalette() {
  let pal;
  try { const r = await fetch('palette.json', { cache: 'no-store' }); if (!r.ok) throw new Error(r.status); pal = await r.json(); }
  catch (e) { console.warn('palette.json not loaded, using CSS fallbacks', e); pal = fallbackPalette(); }
  const byId = { black: pal.black.hex };
  (pal.palettes || []).forEach(p => p.colours.forEach(c => { byId[c.id] = c.hex; }));
  state.colourMap = byId; state.palettes = pal.palettes || [];
  const fromFile = pal._fallback ? pal.quick : pal.quick.map(id => byId[id] || id);
  let saved = null; try { saved = JSON.parse(localStorage.getItem(QUICK_KEY)); } catch (e) {}
  state.quick = (Array.isArray(saved) && saved.length === 5) ? saved.map(norm) : fromFile.map(norm);
  state.chosen = null;
  renderPalette(); renderColours();
  setColour(state.colour || state.quick[0]);   // app.js may have restored the colour before palette.json arrived
}
const dotEl = (cls, hex) => { const el = document.createElement('div'); el.className = 'colour ' + cls; el.style.color = hex || ''; el.innerHTML = '<i></i>'; return el; };
function renderColours() {
  els.colours.innerHTML = '';
  state.quick.forEach((hex, i) => {
    const el = dotEl('quick', hex); el.dataset.i = i; el.setAttribute('role', 'radio'); el.setAttribute('aria-label', 'quick colour ' + (i + 1));
    longPressable(el,
      () => setColour(state.quick[i], true),                                    // tap: pick
      () => { if (els.palette.classList.contains('on')) assignQuick(i); else openColours(); });  // hold: assign (list open) or open the list
    els.colours.appendChild(el);
  });
  const chosen = dotEl('chosen', state.chosen); chosen.id = 'chosen'; chosen.setAttribute('role', 'radio'); chosen.setAttribute('aria-label', 'chosen colour');
  chosen.addEventListener('pointerup', () => { if (state.chosen) setColour(state.chosen, true); });
  els.colours.appendChild(chosen);
  const more = dotEl('', ''); more.id = 'more'; more.setAttribute('role', 'button'); more.setAttribute('aria-label', 'all colours');
  more.innerHTML = '<svg viewBox="0 0 18 18" aria-hidden="true"><circle cx="9" cy="9" r="7"/></svg>';   // a dotted ring: the full list
  more.addEventListener('pointerup', () => els.palette.classList.contains('on') ? closeColours() : openColours());
  els.colours.appendChild(more);
  paintColours();
}
function paintColours() {
  const cur = norm(state.colour), inQuick = state.quick.includes(cur);
  [...els.colours.querySelectorAll('.quick')].forEach((el, i) => el.classList.toggle('on', state.quick[i] === cur));
  const ch = $('chosen');
  if (ch) { ch.style.color = state.chosen || ''; ch.classList.toggle('has', !!state.chosen); ch.classList.toggle('on', !inQuick && !!state.chosen && state.chosen === cur); }
  [...els.palette.querySelectorAll('.pdot')].forEach(el => el.classList.toggle('on', norm(el.dataset.hex) === cur));
}
function setColour(hexOrId, fromUser) {
  let hex = state.colourMap[hexOrId] || hexOrId; hex = norm(hex);
  if (!hex) return;
  state.colour = hex;
  if (!state.quick.includes(hex)) state.chosen = hex;     // a colour from the full list lives in the sixth slot
  paintColours();
  if (fromUser) emit('colour', hex);
}
function renderPalette() {
  els.palette.innerHTML = '';
  state.palettes.forEach(p => {
    const col = document.createElement('div'); col.className = 'pcol';
    p.colours.forEach(cdef => {
      const dot = document.createElement('div'); dot.className = 'pdot'; dot.dataset.hex = cdef.hex; dot.style.color = cdef.hex;
      dot.setAttribute('role', 'option'); dot.setAttribute('aria-label', cdef.name); dot.innerHTML = '<i></i>';
      dot.addEventListener('pointerup', e => { e.stopPropagation(); setColour(cdef.hex, true); closeColours(); });
      col.appendChild(dot);
    });
    const name = document.createElement('div'); name.className = 'pname'; name.textContent = p.name; col.appendChild(name);
    els.palette.appendChild(col);
  });
}
function openColours() { if (!state.palettes.length) return; paintColours(); els.palette.classList.add('on'); els.palette.setAttribute('aria-hidden', 'false'); $('more')?.classList.add('open'); }
function closeColours() { els.palette.classList.remove('on'); els.palette.setAttribute('aria-hidden', 'true'); $('more')?.classList.remove('open'); }
function assignQuick(i) {
  const hex = norm(state.colour); if (!hex || state.quick[i] === hex) return;
  state.quick[i] = hex;
  if (state.chosen === hex) state.chosen = null;            // it now lives in the row
  try { localStorage.setItem(QUICK_KEY, JSON.stringify(state.quick)); } catch (e) {}
  renderColours(); toast('saved to the row'); emit('quickChange', state.quick.slice());
}
function setQuick(list) {
  if (!Array.isArray(list) || list.length !== 5) return;
  state.quick = list.map(h => norm(state.colourMap[h] || h));
  try { localStorage.setItem(QUICK_KEY, JSON.stringify(state.quick)); } catch (e) {}
  if (state.quick.includes(norm(state.chosen))) state.chosen = null;
  renderColours();
}
// tap vs hold, shared by the colour dots
function longPressable(el, onTap, onHold) {
  let t = null, start = null, moved = false, held = false;
  el.addEventListener('pointerdown', e => {
    start = { x: e.clientX, y: e.clientY }; moved = false; held = false; el.classList.add('held');
    clearTimeout(t); t = setTimeout(() => { if (!moved) { held = true; el.classList.remove('held'); onHold(); } }, FAKE.longPressMs);
  });
  el.addEventListener('pointermove', e => { if (start && Math.hypot(e.clientX - start.x, e.clientY - start.y) > 10) moved = true; });
  const end = e => { clearTimeout(t); el.classList.remove('held'); if (e.type === 'pointerup' && !moved && !held) onTap(); start = null; };
  el.addEventListener('pointerup', end); el.addEventListener('pointercancel', end); el.addEventListener('pointerleave', end);
}

// ---------- tools ----------
// tap a word: select. slide up / down on a word: its size, in four steps (S M L XL), the hairline shows it.
// the pointer is captured by the word, so the gesture never reaches the sheet.
const SIZE_LINE = [1, 2, 3.5, 5];      // px, the hairline under the word per step
let pressTimer = null;
function setTool(id, fromUser) {
  state.tool = id;
  [...els.tools.children].forEach(el => el.classList.toggle('on', el.dataset.tool === id));
  if (fromUser) emit('tool', id);
}
function paintSize(id) {
  const el = els.tools.querySelector(`.tool[data-tool="${id}"]`);
  if (el) el.style.setProperty('--line', SIZE_LINE[state.sizes[id]] + 'px');
}
function setSize(id, step, fromUser) {
  step = Math.max(0, Math.min(3, Math.round(step)));
  if (!(id in state.sizes) || state.sizes[id] === step) return false;
  state.sizes[id] = step; paintSize(id);
  try { localStorage.setItem('sketch.sizes', JSON.stringify(state.sizes)); } catch (e) {}
  if (fromUser) emit('size', id, step);
  return true;
}
[...els.tools.children].forEach(el => {
  const id = el.dataset.tool;
  let start = null, startStep = 0, lastStep = 0, sliding = false, cancelled = false, lastTapAt = 0;
  el.addEventListener('pointerdown', e => {
    start = { x: e.clientX, y: e.clientY }; startStep = lastStep = state.sizes[id]; sliding = false; cancelled = false;
    try { el.setPointerCapture(e.pointerId); } catch (err) {}   /* synthetic events have no active pointer */
    el.classList.add('held');
    clearTimeout(pressTimer);
    if (id === state.tool) pressTimer = setTimeout(() => { if (!sliding && !cancelled) showParams(); }, FAKE.longPressMs);
  });
  el.addEventListener('pointermove', e => {
    if (!start || cancelled) return;
    const dx = e.clientX - start.x, dy = start.y - e.clientY;          // up = positive
    if (!sliding) {
      if (Math.abs(dy) > 8 && Math.abs(dy) >= Math.abs(dx)) { sliding = true; clearTimeout(pressTimer); hideParams(); el.classList.add('sliding'); if (id !== state.tool) setTool(id, true); }
      else if (Math.abs(dx) > 14) { cancelled = true; clearTimeout(pressTimer); }
      else return;
    }
    const step = Math.max(0, Math.min(3, startStep + Math.round(dy / FAKE.sizeStepPx)));
    if (step !== lastStep) {                                          // live tick
      lastStep = step; state.sizes[id] = step; paintSize(id);
      el.classList.remove('tick'); void el.offsetWidth; el.classList.add('tick');
    }
  });
  const end = e => {
    clearTimeout(pressTimer); el.classList.remove('held', 'sliding');
    if (!start) return;
    if (sliding) {                                                     // release commits
      const final = lastStep; state.sizes[id] = startStep; setSize(id, final, true);
      if (final === startStep) paintSize(id);
    } else if (e.type === 'pointerup' && !cancelled && !els.params.classList.contains('on')) {
      const now = performance.now();
      if (now - lastTapAt < FAKE.doubleTapMs) {                        // double-tap: back to the default size
        lastTapAt = 0;
        if (setSize(id, FAKE.sizes[id], true)) { el.classList.remove('tick'); void el.offsetWidth; el.classList.add('tick'); }
      } else lastTapAt = now;
      if (id !== state.tool) setTool(id, true);                        // plain tap selects
    } else if (e.type === 'pointerup' && !cancelled && els.params.classList.contains('on') && id !== state.tool) { hideParams(); setTool(id, true); }
    start = null;
  };
  el.addEventListener('pointerup', end); el.addEventListener('pointercancel', end);
});
Object.keys(state.sizes).forEach(paintSize);

// ---------- params (long-press) ----------
function renderParams() {
  els.params.innerHTML = '';
  FAKE.paramNames.forEach(name => {
    const row = document.createElement('div'); row.className = 'param'; row.dataset.param = name;
    row.innerHTML = `<span class="label">${name}</span><div class="line"><i class="knob"></i></div>`;
    const line = row.querySelector('.line'), knob = row.querySelector('.knob');
    const setFromEvent = e => {
      const r = line.getBoundingClientRect();
      const v = Math.min(1, Math.max(0, (e.clientX - r.left) / r.width));
      state.params[state.tool][name] = v; knob.style.left = (v * 100) + '%';
    };
    let dragging = false;
    row.addEventListener('pointerdown', e => { dragging = true; row.setPointerCapture(e.pointerId); setFromEvent(e); e.stopPropagation(); });
    row.addEventListener('pointermove', e => { if (dragging) setFromEvent(e); });
    const stop = () => { dragging = false; };
    row.addEventListener('pointerup', stop); row.addEventListener('pointercancel', stop);
    els.params.appendChild(row);
  });
}
function showParams() {
  const p = state.params[state.tool];
  [...els.params.children].forEach(row => { row.querySelector('.knob').style.left = (p[row.dataset.param] * 100) + '%'; });
  els.params.classList.add('on'); els.params.setAttribute('aria-hidden', 'false');
}
function hideParams() { els.params.classList.remove('on'); els.params.setAttribute('aria-hidden', 'true'); }
// released elsewhere: any pointerdown outside the params or the held tool hides them
document.addEventListener('pointerdown', e => {
  if (els.params.classList.contains('on') && !els.params.contains(e.target) && !els.tools.contains(e.target)) hideParams();
  if (els.sessions.classList.contains('on') && !$('sessionwrap').contains(e.target)) closeSessions();
  if (els.palette.classList.contains('on') && !els.colourswrap.contains(e.target)) closeColours();
}, true);

// ---------- new sheet ----------
pressable(els.new);
els.new.addEventListener('pointerup', () => {
  if (state.mode === 'grid') setMode('draw');
  els.wash.classList.add('on');
  setTimeout(() => { emit('new'); els.wash.classList.remove('on'); }, 220);
});

// ---------- undo ----------
pressable(els.undo);
function doUndo() {
  els.undo.classList.remove('flash'); void els.undo.offsetWidth; els.undo.classList.add('flash');
  emit('undo');
}
els.undo.addEventListener('pointerup', doUndo);
// (two-finger tap undo is the engine's: app.js)
// the hint, once
(function undoHintOnce() {
  let seen = false; try { seen = localStorage.getItem('sketch.hint.undo') === '1'; } catch (e) {}
  if (seen && !location.hash.includes('hint')) return;
  setTimeout(() => els.undoHint.classList.add('on'), 1200);
  setTimeout(() => { els.undoHint.classList.remove('on'); try { localStorage.setItem('sketch.hint.undo', '1'); } catch (e) {} }, 5200);
})();

// ---------- paper grid (drawing aid) ----------
const GRID_MODES = ['off', 'dots', 'lines'];
function setGrid(mode, fromUser) {
  if (!GRID_MODES.includes(mode)) mode = 'off';
  state.grid = mode; body.dataset.grid = mode; els.aidbtn.dataset.grid = mode;
  if (fromUser) emit('grid', mode);
}
pressable(els.aidbtn);
els.aidbtn.addEventListener('pointerup', () => setGrid(GRID_MODES[(GRID_MODES.indexOf(state.grid) + 1) % GRID_MODES.length], true));

// ---------- gallery ----------
pressable(els.gridbtn); pressable(els.back);
els.gridbtn.addEventListener('pointerup', () => setMode('grid'));
els.back.addEventListener('pointerup', () => setMode('draw'));
function setMode(m) {
  state.mode = m; body.dataset.mode = m;
  els.grid.setAttribute('aria-hidden', m === 'grid' ? 'false' : 'true');
  if (m === 'grid') { hideParams(); closeSessions(); closeColours(); els.grid.scrollTop = 0; }
}
const MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];
function fmtDate(iso) { const d = new Date(iso + 'T12:00:00'); return `${d.getDate()} ${MONTHS[d.getMonth()]}`; }
function seeded(s) { let h = 2166136261; for (const c of s) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); } return () => { h += 0x6D2B79F5; let t = Math.imul(h ^ (h >>> 15), 1 | h); t ^= t + Math.imul(t ^ (t >>> 7), 61 | t); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
function doodle(id) {
  const r = seeded(id), n = 1 + Math.floor(r() * 2); let d = '';
  for (let i = 0; i < n; i++) {
    let x = 20 + r() * 120, y = 15 + r() * 90; d += `M${x.toFixed(1)} ${y.toFixed(1)}`;
    const k = 2 + Math.floor(r() * 2);
    for (let j = 0; j < k; j++) {
      const c1x = x + (r() - .5) * 70, c1y = y + (r() - .5) * 60, nx = 15 + r() * 130, ny = 12 + r() * 96;
      d += `C${c1x.toFixed(1)} ${c1y.toFixed(1)} ${(nx + (r() - .5) * 60).toFixed(1)} ${(ny + (r() - .5) * 50).toFixed(1)} ${nx.toFixed(1)} ${ny.toFixed(1)}`; x = nx; y = ny;
    }
  }
  return `<svg class="doodle" viewBox="0 0 160 120" preserveAspectRatio="none" aria-hidden="true"><path d="${d}"/></svg>`;
}
function renderSheets() {
  els.sheets.innerHTML = '';
  state.sheets.forEach(s => {
    const f = document.createElement('figure'); f.dataset.id = s.id;
    f.innerHTML = `<div class="page"><img alt="">${doodle(s.id)}</div><figcaption>${fmtDate(s.date)}</figcaption>`;
    if (s.src) f.querySelector('img').src = s.src;
    let start = null;
    f.addEventListener('pointerdown', e => { start = { x: e.clientX, y: e.clientY }; f.classList.add('pressed'); });
    f.addEventListener('pointerup', e => {
      f.classList.remove('pressed');
      if (start && Math.hypot(e.clientX - start.x, e.clientY - start.y) < 10) { setMode('draw'); emit('openSheet', s.id); }
      start = null;
    });
    f.addEventListener('pointercancel', () => { f.classList.remove('pressed'); start = null; });
    f.addEventListener('pointerleave', () => f.classList.remove('pressed'));
    els.sheets.appendChild(f);
  });
}

// ---------- session + send ----------
function renderSessions() {
  els.sessions.innerHTML = '';
  state.sessions.filter(n => n !== state.session).forEach(n => {
    const it = document.createElement('div'); it.className = 'item'; it.textContent = n; it.setAttribute('role', 'option');
    it.addEventListener('pointerup', e => { e.stopPropagation(); connect(n, true); closeSessions(); });
    els.sessions.appendChild(it);
  });
  els.session.textContent = state.session;
}
function connect(name, fromUser) { state.session = name; renderSessions(); if (fromUser) emit('session', name); }
function openSessions() { els.sessions.classList.add('on'); els.session.classList.add('open'); $('sendgroup').classList.add('open'); }
function closeSessions() { els.sessions.classList.remove('on'); els.session.classList.remove('open'); $('sendgroup').classList.remove('open'); }
els.session.addEventListener('pointerup', () => els.sessions.classList.contains('on') ? closeSessions() : openSessions());

// send: tap → sending (arrow dims) → setSent(true): the hamsa for 2 s, caption "sent to <session>" → the arrow again.
// setSent(false, reason): the arrow stays, the caption shows the reason.
// the prototype fakes success after 400 ms when no onSend handler is bound; the engine calls setSent itself.
let sentTimer = null;
function doSend() {
  if (state.sending) return;
  setSending(true);
  emit('send', state.session);
  if (!hooks.send.length) setTimeout(() => setSent(true), 400);
}
function setSending(flag) {
  state.sending = !!flag;
  els.sendgroup.classList.toggle('sending', state.sending); els.session.classList.toggle('sending', state.sending);
}
function setSent(ok, detail) {
  setSending(false); clearTimeout(sentTimer);
  if (ok) {
    els.sendgroup.classList.add('sent'); toast(`sent to ${state.session}`);
    sentTimer = setTimeout(() => els.sendgroup.classList.remove('sent'), 2000);
  } else {
    els.sendgroup.classList.remove('sent'); toast(detail || `not sent to ${state.session}`);
  }
}
pressable(els.send); pressable(els.sendto);
els.send.addEventListener('pointerup', doSend);
els.sendto.addEventListener('pointerup', doSend);

let toastTimer = null;
function toast(text) {
  els.toast.textContent = text; els.toast.classList.add('on');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => els.toast.classList.remove('on'), FAKE.toastMs);
}

// ---------- init ----------
renderParams(); renderSheets(); renderSessions();
setTool(state.tool); setGrid(state.grid);
loadPalette().then(() => {
  if (location.hash.includes('colours')) openColours();
  requestAnimationFrame(() => requestAnimationFrame(() => body.classList.add('ready')));   // transitions start after first paint
});
if (location.hash.includes('grid')) setMode('grid');
if (location.hash.includes('params')) showParams();
if (location.hash.includes('dots')) setGrid('dots');
if (location.hash.includes('lines')) setGrid('lines');
if (location.hash.includes('sent')) { els.sendgroup.classList.add('sent'); toast(`sent to ${state.session}`); }   // freeze the sent state for a screenshot
if (location.hash.includes('sessions')) openSessions();

// ---------- hook layer for the engine ----------
window.sketchUI = {
  onTool: on('tool'), onColour: on('colour'), onUndo: on('undo'), onNew: on('new'),
  onSend: on('send'), onSession: on('session'), onOpenSheet: on('openSheet'), onGrid: on('grid'), onQuickChange: on('quickChange'), onSize: on('size'),
  setSize: (id, step) => setSize(id, step, false),
  setQuick, openColours, closeColours,
  setGrid: mode => setGrid(mode, false),
  setSessions(list, connected) { state.sessions = list.slice(); if (connected) state.session = connected; else if (!list.includes(state.session)) state.session = list[0] || ''; renderSessions(); },
  setSheets(list) { state.sheets = list.slice(); renderSheets(); },
  setSending, setSent,
  toast,
  // extras, not in the brief but cheap for the merge
  setTool: id => setTool(id, false), setColour: hexOrId => setColour(hexOrId, false), setMode,
  get state() { return { ...state, params: state.params[state.tool] }; },
  get quick() { return state.quick.slice(); },
  get sizes() { return { ...state.sizes }; },
  get colours() { return { ...state.colourMap }; },   // id → hex, black + the twenty, resolved from palette.json
};
