// Sandboxed harness: runs the vendor glue in a vm context with stubbed host imports.
const vm = require('vm'), fs = require('fs');
const DIR = process.argv[2];
const glue = fs.readFileSync(DIR + '/index.pretty.js', 'utf8');
const wasm = fs.readFileSync(DIR + '/index.wasm');
const log = { ghost: [], blit: [], ellipse: [], missing: [] };
const el = () => ({ style: {}, classList: { add(){}, remove(){}, contains(){return false;} }, getContext: () => ctx2, width: 0, height: 0, clientHeight: 0, innerHTML: '' });
const ctx2 = { beginPath(){}, ellipse(...a){ log.ellipse.push(a); }, moveTo(){}, lineTo(){}, stroke(){}, rect(){}, fillRect(){}, setLineDash(){}, clearRect(){}, putImageData(img, dx, dy, sx, sy, w, h){ log.blit.push([img.width, img.height, dx, dy, sx, sy, w, h]); } };
const ctxObj = {
  console, Math, Date, JSON, Promise, Error, TypeError, Uint8Array, Uint8ClampedArray, Int8Array, Int16Array, Uint16Array, Int32Array, Uint32Array, Float32Array, Float64Array, BigInt64Array, BigUint64Array, ArrayBuffer, DataView, WebAssembly, TextDecoder, setTimeout, clearTimeout, performance,
  ImageData: function (d, w, h) { this.data = d; this.width = w; this.height = h; },
  window: { location: { href: '' }, addEventListener(){} }, location: { href: 'http://x/' },
  document: { getElementById: el, createElement: el, querySelector: el, currentScript: { src: 'http://x/index.js' } },
  ctx: ctx2, CANVAS: { width: 512, height: 512, style: { width: '512px' } },
  brush_ghost_view: { style: {} }, brush_ghost_ctx: ctx2, current_offsetX: 100, current_offsetY: 100,
  SETTING: { paper_texture: 1 }, cache_cleared: true,
};
ctxObj.self = ctxObj.window;
ctxObj.paper_texture_clicked = function () { log.material = (log.material||0)+1; };
ctxObj.Module = { wasmBinary: wasm, print: s => (ctxObj.__sink ? ctxObj.__sink(s) : console.log('[wasm]', s)), printErr: s => console.log('[wasm-err]', s), locateFile: p => p,
  onRuntimeInitialized: () => { ctxObj.__ready = true; } };
vm.createContext(ctxObj);
// Override import stubs that are "missing" so they log instead of aborting.
const patched = glue + `
_DrawCanvasWideLine = function(a,b){ __missing('DrawCanvasWideLine',[a,b]); return 0; };
_DrawCanvasRectangle = function(a,b){ __missing('DrawCanvasRectangle',[a,b]); return 0; };
_SaveCanvasToIndexedDB = function(){ __missing('SaveCanvasToIndexedDB',[]); };
`;
ctxObj.__missing = (n, a) => log.missing.push([n, a]);
// Wrap ghost to log the raw args before the JS draws.
vm.runInContext(patched.replace('var _DrawGhostBrushPencil = function (shift_x, shift_y, a, b, angle) {', 'var _DrawGhostBrushPencil = function (shift_x, shift_y, a, b, angle) { __ghost([shift_x, shift_y, a, b, angle]);'), ctxObj, { filename: 'glue.js' });
ctxObj.__ghost = a => log.ghost.push(a);
module.exports = { ctxObj, log };
