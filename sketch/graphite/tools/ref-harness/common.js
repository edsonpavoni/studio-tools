const { ctxObj, log } = require('./run.js');
const wait = () => new Promise(r => { const t = setInterval(() => { if (ctxObj.__ready) { clearInterval(t); r(); } }, 20); });
const BR = [[16,40,6],[100,40,8],[200,50,23],[200,50,26],[50,50,0],[150,50,3],[100,50,7],[50,50,15],[50,50,17],[100,50,9],[50,50,25],[20,50,20],[20,50,22],[20,50,11],[50,50,16],[50,50,18],[50,50,24],[50,50,24],[50,50,24],[50,50,24],[50,50,24],[50,50,24],[50,50,24],[50,50,24],[150,50,1],[150,50,2],[16,40,27],[16,40,28],[16,50,29]];
async function setup(gray = 200, view = 512, doc = 1024, rgba = null) {
  await wait();
  const M = ctxObj.Module, c = (n, args) => M.ccall(n, 'number', args.map(() => 'number'), args);
  c('InitData', [view, view, doc, doc, 2, 0, 0]);
  const n = 512 * 512 * 4, p = M._malloc(n);
  if (rgba) M.HEAPU8.set(rgba.subarray(0, n), p);
  else for (let i = 0; i < n; i += 4) { M.HEAPU8[p+i] = M.HEAPU8[p+i+1] = M.HEAPU8[p+i+2] = gray; M.HEAPU8[p+i+3] = 255; }
  c('LoadMaterialEvent', [p, n]);
  BR.forEach((b, i) => { c('BrushSelectionEvent', [i]); c('KindOfPenChangeEvent', [b[2]]); c('BrushSizeChangeEvent', [b[0]]); c('BrushHardnessChangeEvent', [b[1]]); });
  c('SetBrushCorrection', [8]);
  return { M, c };
}
module.exports = { ctxObj, log, setup, BR };
