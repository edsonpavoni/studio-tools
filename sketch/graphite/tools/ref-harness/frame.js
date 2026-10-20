const H = require('./common.js');
const { ctxObj, log } = H;
let FW = 512, FH = 512, frame = new Uint8ClampedArray(FW * FH * 4);
ctxObj.ctx.putImageData = function (img, dx, dy, sx, sy, w, h) {
  log.blit.push([img.width, img.height, dx, dy, sx, sy, w, h]);
  for (let y = sy; y < sy + h; y++) for (let x = sx; x < sx + w; x++) {
    const X = dx + x, Y = dy + y; if (X < 0 || Y < 0 || X >= FW || Y >= FH) continue;
    const s = (y * img.width + x) * 4, d = (Y * FW + X) * 4;
    frame[d] = img.data[s]; frame[d+1] = img.data[s+1]; frame[d+2] = img.data[s+2]; frame[d+3] = img.data[s+3];
  }
};
const lum = (x, y) => frame[(y * FW + x) * 4];
module.exports = { ...H, lum, frameRef: () => frame, W: () => FW };
