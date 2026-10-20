# 12 — 8bitpaint pencil: smudge and eraser tools, recovered from the wasm

Source: `reference/8bitpaint/8bitpaintpencil/` (v1.5.0.0). Study only. No code was copied; what follows is the algorithm and constants, rewritten as pseudo-code.

Method: `index.wat` was split per function. To get readable bodies, the Asyncify state global (`global 3`) was replaced with `0` in a scratch copy, cleaned with binaryen passes that keep function indexes (`precompute-propagate, dce, vacuum, simplify-locals, merge-blocks, remove-unused-brs, coalesce-locals`), and converted with `wasm2js`. In that JS output, function `$k` is wasm function `k+56` (56 imports). **All indexes in this report are wasm/wat indexes.** Data-section tables were read from the `wasm-objdump -x` hex dump.

Library helpers (identified from the musl bodies): 1798 = `powf`, 1799 = `sinf`, 1804 = `cosf`, 1811 = `cos`, 1822 = `sin`, 1812 = `atan2`, 1986/1987 = malloc/free, 1944/1945 = memcpy/memset.

---

## 1. Tool id table (app.pretty.js)

The UI has **two numbers per tool**:
- the **slot** (0–28), sent to `BrushSelectionEvent(slot)` (func 91) by `brush_clicked(slot)`;
- the **kind** (the `IDS_*` enum), sent to `KindOfPenChangeEvent(kind)` (func 99) at init, from `SETTING.brush[slot].kind_of_pen`.

At init, the JS loops over slots 0–28. For each slot it calls `BrushSelectionEvent(slot)`, then `KindOfPenChangeEvent(kind)`, `BrushSizeChangeEvent(size)` and `BrushHardnessChangeEvent(hardness)`. It finishes with `BrushSelectionEvent(current)`.

| Tool (i18n key) | slot → BrushSelectionEvent | kind → KindOfPenChangeEvent | default size | default hardness | in pencil UI? |
|---|---|---|---|---|---|
| Kneaded eraser | 1 | 8 (`IDS_KNEADED_ERASER`) | 100 | 40 (full app: 50) | yes (eraser group default) |
| Smudge1(all) | 2 | 23 (`IDS_SMUDGE`) | 200 | 50 | yes |
| Smudge2(all) | 3 | 26 (`IDS_SMUDGE2`) | 200 | 50 | **no** (full 8bitpaint web only) |
| Eraser | 6 | 7 (`IDS_ERASER`) | 100 | 50 | **no** (full app only) |
| Eraser(all) | 9 | 9 (`IDS_ERASER_ALL`) | 100 | 50 | yes |
| Erase and draw | 10 | 25 (`IDS_ERASE_AND_DRAW`) | 50 | 50 | **no** (full app only) |
| (Kneaded eraser all) | none | 10 (`IDS_KNEADED_ERASER_ALL`) | — | — | not exposed |
| Pencil(4B) / (HB) / (2H) | 26 / 27 / 28 | 27 / 28 / 29 (`IDS_PENCIL_4B/HB/2H`) | 16 | 40 / 40 / 50 | yes |
| Pencil (plain, slot 0, not in pencil UI) | 0 | 6 (`IDS_PENCIL`) | 16 | 40 | no |
| Lasso eraser(all) | 12 | 22 | 20 | 50 | yes |

Notes:
- **Brush correction** is not a tool. It is `SetBrushCorrection(n)` (func 158), the stabiliser, default 8. **Paper texture** is a material picker: `LoadMaterialEvent` (func 139) loads one of the nine 512×512 height maps in `img/`, default `paper_texture: 1`.
- Size slider: `size = 500^slider` (log scale), clamped 1..500 in func 100. Hardness: 0..100, func 101.
- Engine brush table: 29 records of 36 bytes at **72080** (`+0 kind, +4 size, +8 hardness, +12 palette …`). The current slot is at **73124**.
- **What "(all)" means.** The engine is 8bitpaint's, whose canvas byte holds **8 one-bit layer planes** (bit *i* = layer *i*; bit set = empty/white). Func 199 builds a mask of the layers that are visible (`+0≠0`) and not locked (`+4≠1`). The 8 layer records are 28 bytes each. "(all)" tools act on **every visible and unlocked layer at once**. The single-layer tools act only on the current layer's bit (current layer index at canvas+4188). It is also the gate: if the *current* layer is locked or hidden (func 178), the tool handlers bail out, except for kinds 9/10 (and the class-8 set 9, 10, 21, 22). Smudge1 and Smudge2 never touch a per-layer bit; they operate on the whole pixel byte, so they are inherently "all layers". See §7 for how this collides with the pencil's 0..255 tone model.

## 2. Dispatch: from TabletEvent to the tool kernel

```
TabletEvent(x, y, p, alt, az)                      func 163
  162: to canvas coords; alt -> int(deg*10), az -> (deg+90) mod 360 * 10
  keeps a 3-point history; quadratic (Bezier-like) interpolation;
  emits 4 sub-samples t = 0.75, 0.5, 0.25, 0, pressure linearly interpolated
  -> func 164(x', y', p', alt, az)  for each sub-sample
164: stroke bookkeeping, stabiliser (brush-correction queue, 73136), dirty rect
  -> call_indirect  table[ HEAP32[71392] ](canvasObj=63664, dirtyRect)
  -> DrawCanvasRectFromArray (import 8) for the clamped dirty rect, via 79 (row copy 67736 -> 67740)
```

`BrushSelectionEvent(slot)` (91) stores the slot at 73124. It reads `kind = brush[slot].kind` and computes `cls = table5120[kind]` (func 66: an i32 table at **5120** in the Data section, 30 entries). It stores `cls` at **71392**. The element segment starts at table index 1, so `cls` maps to a function:

| kind | cls | function | role |
|---|---|---|---|
| 0,4,5,7,9,14,19,25 | 8 | **177** | hard vector pen: Pen, Eraser, Eraser(all), Erase and draw |
| 1 | 9 | 200 | gray pen |
| 2,3 | 10 | 202 | gray pen 2 / marker |
| 6,27,28,29 | 11 | **189** | graphite pencil (4B/HB/2H) |
| 8,10 | 12 | **185** | Kneaded eraser |
| 23 | 19 | **190** | Smudge1 |
| 26 | 21 | **197** | Smudge2 |
| 24 | 20 | 222 | Lua brush script |
| 11 / 15,17 / 16,18 / 20–22 | 13 / 16 / 17 / 18 | 219 / 206 / 210 / 213 | bucket / selection / lasso / lasso paint & erase |

Gotcha: the class is latched only by `BrushSelectionEvent`. Changing the kind with `KindOfPenChangeEvent` changes behaviour only after the next selection.

All tool handlers have the signature `(param i32 canvasObj, i32 dirtyRectOut) (result i32)`.

The canvas object is at 63664. The fields used here:
- `+4064 w`, `+4068 h`, `+4072 → 8-bit indexed bitmap` (pixels at `[0]`, palette at `+44`). Globally, these are 67728/67732/67736.
- `+3684` the 8 layer records (28 bytes each).
- `+4188` current layer.
- `+7732 → brush table`, `+7736 → current slot`, `+7740 → paper texture` (512×512 u8).

Current and previous stylus samples are read by **248** (current) and **249** (previous), both wrappers of 247. Each returns `x, y, pressure, azimuth°, altitude` (altitude in tenths of a degree; its sign is kept and is used as the "eraser end" flag).

## 3. Smudge1(all) — func 190 → dab 191 → sample 192 + apply 193

**Verdict: neither a MyPaint pickup nor a drag.** Each dab is a local **weighted-mean flatten**. Under the dab footprint the engine:
1. computes the coverage- and texture-weighted mean density;
2. pulls every pixel toward that mean by its own weight.

Nothing is carried between dabs. The only persistent state is the spacing remainder at global 78488. It is a blur that is gated by paper contact.

```
SMUDGE1(stroke segment prev -> cur):                     // func 190
  h      = brush.hardness (0..100)
  gamma  = h >= 50 ? 1 + 3*(h-50)/50  :  1 / (1 + 3*(50-h)/50)   // 0.25 .. 1 .. 4
  p      = pressure ^ gamma          (both endpoints)
  if p_cur > 0 and p_prev == 0: spacingCarry = 0           // stroke start
  if size < 1 or the integer pixel did not change: return
  r      = max(size * 0.5, 2)                      // radius = size/2; pressure does NOT scale it
  tilt   = |altitude| in radians ; dir = (90 - azimuth) in radians
  a = b = r
  if tilt < 32°  (0.5585 rad):
      a = cos(tilt + 58°)^2 * max(600 - r, 0) + r // elongates as the pen lies flatter (58° = 45°+13°)
      b = max(r, a / 20)
  a = max(a, b)
  step   = max(1, int(2*b / 10))                   // spacing = 20 % of the minor radius
  walk the integer segment prev->cur in steps of `step`
      (carry the remainder in 78488):
      DAB_SMUDGE1(x+0.25, y+0.25, a, b, dir, tilt, paperTex, p)
      grow the dirty rect (the bbox is offset by a small texture-dependent tip jitter, ±10 px margin)

DAB_SMUDGE1(cx, cy, a, b, dir, tilt, tex, p):            // func 191
  e = sqrt(cos²(tilt)·a² + sin²(tilt)·b²)           // projected half-length
  centre shifted by (e - b)·cos(tilt) along dir     // stylus point = tip end of the ellipse
  poly = ellipse polygon (4·floor(b) vertices, min 4, rotated by dir)   // func 187
  mean = SAMPLE(poly, …, p)                         // func 192
  APPLY(poly, …, p, mean)                           // func 193

coverage(px)  (func 194, per scanline span):
  t   = normalised depth of px inside the tilted ellipse, measured along
        the tilt axis: 0 at the heel edge, 1 at the tip
  cov = 255 * max(0, t - (1 - p))                   // linear cone, offset by pressure
weight(px)  (func 195/196):
  w = (cov + texHeight(px mod 512) - 255) / 255     // only where > 0
SAMPLE: mean = Σ w·d / Σ w,  with d = 1 - v/255 (v = stored byte, 255 = white)
APPLY:  d' = (1 - w)·d + w·mean;  v' = 255 - 255·d'    (only where w > 0)
```

Constants: radius = size/2 (min 2). Tilt threshold 32°. Elongation `cos²(tilt+58°)·(600−r)`. Minor ≥ major/20. Spacing `max(1, ⌊0.2·b⌋)`. Hardness acts only as the pressure exponent γ ∈ [¼, 4], not as edge softness. Falloff is a linear ramp along the tilt axis, shifted by (1−p). There is no separate "rate" constant: the mix weight is the per-pixel contact weight w, at most 1.

**Paper texture.** The same 512×512 height map gates both sampling and writing (w = cov − (255 − tex)). High-tex pixels (peaks) are touched first. Low pixels (valleys) only join where cov > 255 − tex; at cov = 255 the weight is tex/255, so a fully deep valley (tex = 0) is never touched. **Smudge1 therefore does not fill paper valleys.** It averages graphite among the contacted peaks. Grain remains visible, softened. This holds as long as "tex high = peak", which the pencil darkening path implies (§8).

## 4. Smudge2(all) — func 197 → kernel 198

**Verdict: a displacement / drag (stamp-copy).** A hard disc of pixels is cut at the previous step and pasted at the current one.

```
SMUDGE2(prev -> cur):                                   // func 197
  gamma as Smudge1;  D = p(sample 248)^gamma * size     // pressure DOES scale this one
  if D < 0.7: return
  r = int(D * 0.5)
  walk prev->cur, step 3 px (remainder in 86688; last stamp position in 86692/86696):
      DRAG(fromPos = lastStamp, toPos = here, r);  lastStamp = here
  dirty rect = segment bbox ± (r+1)

DRAG(from, to, r):                                      // func 198
  n = 2r+1; mask = n×n 8-bit, cleared                   // func 69 alloc
  draw filled circle radius r into mask (func 179, mode 3 = all-layer bits)
  clear mask where palette[canvas byte at from].alpha == 255   (protected index)
  tmp = n×n copy of the canvas at (from - r)            // 168: copies only bits of editable layers
  apply mask to tmp                                     // 170
  …                                                     // 169: masked op with the layer records (+7748)
  composite tmp into the canvas at (to - r) through the mask   // func 159
  (the 8 layer "ignore" flags at +7772 are saved and restored around this)
```

The paste is a **straight copy** of the bits of editable layers: `dst = (src | lockedMask) & (~lockedMask | dst)`. There is no alpha mix and no falloff (hard circle edge), no tilt, and no paper texture. Spacing is 3 px, fixed. Because it ignores the texture and moves whole bytes, Smudge2 **can** carry graphite into paper valleys. It drags the grain pattern out of register with the paper under it.

**How it differs from Smudge1:**
- Smudge1 is a texture-gated averaging blur. It uses the tilted pencil-tip footprint, and its size does not depend on pressure.
- Smudge2 is a hard-edged pixel drag in a circular disc, whose diameter scales with pressure^γ.

## 5. Eraser / Eraser(all) / Erase and draw — func 177 (shared "hard pen" class)

```
HARDPEN(prev -> cur):                                   // func 177
  mode = 1                       if kind ∈ {7 Eraser, 21 Lasso eraser}
       = altitude >= 0 ? 2 : 3   otherwise (pen; flipped stylus = erase all)
  if kind == 25 (Erase and draw):            mode = 4
  elif kind ∈ {9 Eraser(all), 22}:            mode = 3
  gamma from hardness (same formula);  D0 = p_prev^gamma*size,  D1 = p_cur^gamma*size
  if D0 >= 2: filled circle at prev, radius D0/2                    (func 179)
  if both D < 0.7: skip;  thin (<1) ends -> 1-px lines (func 180)
  else: tangent quad ("capsule" between circles r0=D0/2, r1=D1/2)  (func 181, polygon fill)
  every span -> func 182 with mode:
     mode 0  pixel &= ~layerBit        (draw current layer)
     mode 1  pixel |=  layerBit        (ERASER: clear current layer)
     mode 2  pixel &= ~editableMask    (draw on all editable layers)
     mode 3  pixel |=  editableMask    (ERASER(all): clear all visible+unlocked layers)
     mode 4  pixel  = (pixel | editableMask) & ~layerBit   (ERASE AND DRAW)
```

- **Eraser** clears to 0 density, binary. It is a hard-edged capsule with no anti-aliasing and no hardness falloff. Pressure scales only the diameter (`p^γ·size`; hardness is the γ curve). It ignores the paper texture.
- **Eraser(all)** does the same on every visible and unlocked layer. In the pencil app with all 8 layers editable the mask is 0xFF, so the byte becomes 255, which is pure white.
- **Erase and draw** wipes the other editable layers inside the stroke and paints the current layer solid, in one pass. Think of a "replace colour" pen. It belongs to the 8-colour app and is not exposed in the pencil UI.

## 6. Kneaded eraser — func 185 → pencil dab 186 → 188 → kernel 215 (erase branch)

This is the graphite pencil's tip model run backwards. It uses the same tilted ellipse and the same texture gate, with these differences:

```
KNEADED(prev -> cur):                                   // func 185
  (no hardness exponent: raw pressure)
  r = max(size, 2) * 0.25                               // radius = size/4
  a = r;  if tilt < 45°: a = cos(tilt + 45°)^2 * max(600 - r, 0) + r ;  b = r
  dir = (90 - azimuth);  step = max(1, int(2r/10))       // spacing 20 % of r
  eraseFlag = (kind == 8) or (altitude < 0)
     // note: kind 10 (kneaded-all) therefore DARKENS unless the stylus is flipped
  per step: DAB(x+.25, y+.25, a, b, dir, tilt, paperTex, p(sample 249), eraseFlag)

DAB (186): same tip-offset as Smudge1, plus a texture-dependent jitter of the centre:
           j = min(1, sqrt(4ab)/100)/p * 6 * (1 - tex/255)
188: if kind == 8: cov = p*255 FLAT over the whole ellipse   (no cone)
     else (pencil): cov = cone from func 194
     k = clamp(sqrt(4·a·b) / 16, 0, 1) * 255            // texture strength; full once a·b ≥ 64
215 erase branch, per pixel:
     lift = max(0, cov - (255 - tex)·k/255)
     v'   = min(255, v + lift)                          // subtract density, additive, clamped at white
```

So the kneaded eraser **subtracts** a pressure-proportional amount of density, `Δd ≤ p`. It is **texture-aware**: paper peaks are lifted first, and valleys only at higher pressure or with small dabs (small `k`). It has a **soft overall effect** but a hard ellipse boundary: the edge comes from the polygon, with a uniform interior. It is a **tilt ellipse** below 45° altitude. The ghost cursor (func 109 → import 3) draws a simpler preview: `r = size/4`, `major = min(size, cos(tilt)·(size−r)+r)`. It does not exactly match the stroke formula.

For comparison, the pencil darkening branch of 215 is `v' = max(floor, v − (255−floor)/255·max(0, cov − (255−tex)·k/255))`, with `floor = 0` (4B), `30` (HB), `137` (2H). The handler also calls 199 (layer mask) and discards the result, so the 8-bit tone kernels do not implement "(all)" per layer.

## 7. Open contradiction: bit planes vs 8-bit tone

The same canvas byte is used two ways:
- **8bitpaint bit-plane code** treats it as 8 one-bit layers: 93 ClearLayer, 177/182 hard pen, 197/198/168/170 Smudge2, 199 mask.
- **Graphite code** treats it as 0..255 lightness (`d = 1 − v/255`): 189/185/186/188/215 pencil and kneaded, 190–196 Smudge1.

`GetCanvasBmpPixelPointerEvent` (154) returns a single plane of `stride·h` bytes. Its header (153) is 1068 bytes, a 256-entry palette. `GetCanvasLayerPointerEvent` (155) returns only the 9×28-byte layer *parameter* table at 71412. I found **no second per-layer pixel store**. In the pencil app the bit-plane tools therefore degrade to whole-byte operations: OR 0xFF = white; Smudge2 = byte copy. This could not be reconciled with the "one 8-bit density map per colour layer" model in the time available. Whoever studies layers/compositing should check the palette builder.

Extra check: the canvas bitmap pointer 67736 is written only by InitData/new canvas (61), LoadPNGEvent (60) and SetCanvasBmpEvent (156). Undo/redo (122/145) swap it only temporarily. Nothing reassigns it on a layer or palette switch. **So there is exactly one 8-bit plane per canvas.** That contradicts the brief's "one 8-bit density map per colour layer" for this engine. In the pencil app, layers are either 1-bit planes (8bitpaint semantics) or effectively a single tone plane; the graphite kernels' arithmetic only makes sense for the second.

Altitude sign: the pencil JS never sends a negative altitude (`TabletEvent(x, y, p, altitudeAngle, azimuthAngle)`). The barrel button (`buttons & 2`) is handled in JS by `tool_shift()` to the eraser group. So the engine's "altitude < 0 ⇒ erase" path is unreachable from this host.

## 8. Call graph

```
163 TabletEvent ─ 162 (coord/angle convert)
   └ 164 per-substep ─ 248/249 (cur/prev sample via 247)
        ├ call_indirect table[cls] :
        │   190 Smudge1 ─ 174/175 (rect), 184 (dist), 1798 powf, 1799/1804/1811/1822 trig
        │       └ 191 dab ─ 187 ellipse polygon
        │             ├ 192 sample ─ 194 cone coverage ─ 195 Σw·d, Σw (texture gate)
        │             └ 193 apply  ─ 194 ─ 196 d' = (1-w)d + w·mean
        │   197 Smudge2 ─ 174, 184, 1798
        │       └ 198 drag ─ 69 bitmap alloc, 179 circle mask, 168 copy-from, 170 mask,
        │                    169 masked op, 159 paste, 68/76 bitmap free
        │   185 Kneaded ─ 178 lock check, 174/175, 184
        │       └ 186 pencil dab ─ 187 polygon ─ 188 ─ 194 (pencil only) ─ 215 kernel (erase/draw)
        │   189 Pencil  ─ same 186/188/215 path, eraseFlag only from flipped stylus
        │   177 HardPen (Eraser 7, Eraser(all) 9, Erase&draw 25, Pen 0…)
        │       ─ 178, 179 circle, 180 thin line, 181 polygon ─ 182 span writer (modes 0-4), 199 layer mask
        ├ 79 dirty-rect row copy ─ import 8 DrawCanvasRectFromArray
109 ShowBrushGhostKneadedEraserEvent ─ 248 ─ import 3 DrawGhostBrushPencil
91 BrushSelectionEvent ─ 66 (kind→cls, table @5120) ; 99/100/101 write brush record @72080
```

Signatures (wat):
- 163 `(f64 x, f64 y, f64 p, f64 alt, f64 az) → i32`
- 164 `(f64×5)`
- 177/185/189/190/197 `(i32 canvas, i32 rect) → i32`
- 186 `(i32, f32 x, f32 y, f32 a, f32 b, f32 dir, f32 tilt, i32 tex, f32 p, i32 mode)`
- 191 `(i32, f32 x, f32 y, f32 a, f32 b, f32 dir, f32 tilt, i32 tex, f32 p)`
- 192 `(i32, i32 poly, i32 n, f32×6, i32 tex, f32 p) → f32 mean`
- 193 `(… , f32 p, f32 mean)`
- 194 `(f32×7, i32 x0, i32 x1, i32 y, i32 buf, i32 outL, i32 outR)`
- 195 `(i32 bmp, i32 x0, i32 x1, i32 y, i32 tex, i32 covBuf, i32 Σwd, i32 Σw)`
- 196 `(i32 bmp, i32 x0, i32 x1, i32 y, i32 tex, i32 covBuf, f32 mean)`
- 198 `(i32 canvas, i32 x0, i32 y0, i32 x1, i32 y1, i32 r)`
- 215 `(i32 bmp, i32 x0, i32 x1, i32 y, i32 tex, i32 covBuf, f32 4ab, i32 mode)`
- 182 `(i32 bmp, i32 x0, i32 x1, i32 y, i32 pattern, i32 mode)`

## 9. Confidence

**Certain** (read directly from the code):
- The slot/kind table and the defaults.
- The kind→class table at 5120 and the elem mapping to 177/185/189/190/197.
- The γ hardness curve.
- The Smudge1 structure: sample the weighted mean, then blend toward it, with no pickup buffer, the same footprint for both, and the texture gate `cov+tex−255`.
- Smudge1: r = size/2, the 32° tilt rule and constants 600/58°/÷20, spacing 0.2·b.
- Smudge2: drag-copy of a circular disc, 3 px spacing, D = p^γ·size, the 0.7 threshold.
- The bit operations in 182 for modes 0–4, and that kinds 7/9/25 select modes 1/3/4. Eraser and Eraser(all) are binary and hard-edged (OR into the byte), with no texture.
- Kneaded: r = size/4, 45° rule, flat p·255 coverage, `v' = min(255, v + max(0, cov − (255−tex)·k/255))`, k = clamp(√(4ab)/16)·255, no hardness.
- The kind 10 / negative-altitude erase-flag logic (engine side).
- sin/cos identities (from the musl bodies).

**Inferred:**
- What the hard-pen bits *mean* (bit i = layer i, bit set = empty). It follows from 8bitpaint web's model and from ClearLayer (93), but plain Pen (kind 0) also lands in mode 2 ("draw on all editable layers"), which is odd and points to §7.
- Texture polarity: tex high = paper peak. This rests on pencil darkening being gated the same way.
- The exact geometric meaning of the 194 "depth" (heel→tip linear ramp along the tilt axis) and of the 191/186 centre offset.
- That 248 is the current and 249 the previous sample.
- The role of 169 and of the palette-alpha protection in Smudge2.
- That "(all)" in the pencil app collapses to a whole-byte operation.

**Not found / unresolved:**
- How the pencil app stores more than one tone layer (§7).
- The palette builder.
- Whether 200/202 (gray pens) carry any smudge-like behaviour; not examined.
