# 10 — 8bitpaint pencil: stroke input pipeline (from the wasm)

Source: `reference/8bitpaint/8bitpaintpencil/index.wasm` (v1.5.0.0), read as `index.wat` + `wasm-objdump`.
Study only. No code copied; this is the algorithm and its constants, rewritten as pseudo-code.
The binary is Emscripten + **Asyncify** (`global 3` = asyncify state, `global 4` = asyncify stack). Every
`if (global3 == 2) …` / `global3 == 1` branch is unwind/rewind boilerplate and has been dropped below.

**Main finding.** The pencil runs as straight C++. TabletEvent never reaches Lua. Per pointer event it does
this: the host sends the point in view pixels, the engine makes **4 quadratic sub-samples** from the last 3 events,
puts each one into a **box filter (moving average) of 2·correction+1 sub-samples**, then the pencil function
(func 189) walks the smoothed segment from the previous filter output to the current one. It places dabs at
`max(1, trunc(minorDiameter/10))` pixels apart, carries the leftover distance into the next segment, and gives
**all dabs in the segment the end-point attributes**. The dabs go to func 186, the ellipse rasteriser.

---

## 0. Host side (app.pretty.js), what TabletEvent receives

```
x, y      = pointer pageX/Y relative to the <canvas> element × (canvas.width / css width)   // VIEW pixels, not canvas
altitude  = e.altitudeAngle (rad); if missing → tilt2spherical(tiltX, tiltY); default π/2
azimuth   = e.azimuthAngle  (rad); default 0
pressure  = e.pressure (pen/mouse); touch-drawing → e.pressure or 0.5
iOS only  : x += sin(-tiltX°)·tilt_correction ; y -= sin(tiltY°)·tilt_correction
iOS only  : first 9 events of a stroke: pressure *= n/10   (n = 1..9)  ← host-side start ramp

pointerdown : TabletEvent(x,y, 0, alt,az)   // reset the interpolator at the touch point
              TabletEvent(x,y, p, alt,az)   // (AddLayerToHistoryEvent first if LAYER_MODIFIED)
pointermove : if p > 0 → TabletEvent(x,y,p,alt,az)
pointerup   : 4 × TabletEvent(PREV_X, PREV_Y, 0, PREV_alt, PREV_az)   // pen-up flush
SetBrushCorrection(v)      v = slider 0..99, default SETTING.brush_correction = 8
BrushSizeChangeEvent(s)    s = round(500^slider)          (slider 0..1)
BrushHardnessChangeEvent(h) h = round(100·slider)         (slider 0..1)
```

Pencil brushes are `kind_of_pen` **6** (brush 0, size 16, hardness 40) and **27, 28, 29** (brushes 26–28,
size 16, hardness 40/40/50). All four go to the same C++ function (189). The kneaded eraser is kind 8/10 (func 185).
Kind 24 = Lua script brushes (func 222, the only path into the Lua VM).

---

## 1. Memory map (named fields)

Brush-engine object `O` = **63664** (one static C++ object). Offsets are from O.

| addr | O+ | name | notes |
|---|---|---|---|
| 63664 | 0 | `raw_cur` | Point (20 B) |
| 63684 | 20 | `raw_prev` | Point |
| 63704 | 40 | `hist[0..199]` | Point ring, newest at hist[0] |
| 67684 | 4020 | `sm_cur` | smoothed Point (box-filter output) |
| 67704 | 4040 | `sm_prev` | previous smoothed Point |
| 67724 | 4060 | `&correction` | pointer → 73136 |
| 67728/67732 | 4064/4068 | canvas W, H | (also the start of the canvas/layer object passed to 186) |
| 67736 / 67740 | | current layer bmp / pre-stroke backup bmp | used by undo |
| 67772 | | `stroke_active` (i32) | |
| 67776 | | `stroke_rect` {x0,y0,x1,y1} | dirty rect for the whole stroke (undo) |
| 71392 | | `brush_fn` | function-table index for the current kind |
| 71924/71928 | 8260/8264 | view W, H (px) | |
| 71948/71952 | 8284/8288 | view offset X, Y | |
| 71964 | 8300 | `view_scale` | canvas px per view px (GetViewCanvasScaleEvent) |
| 71968 | 8304 | `hflip` | |
| 71972 | 8308 | `view_angle` (deg) | |
| 72080 | 8416 | `brush[29]` | 36-byte records: +0 kind, +4 size(int), +8 hardness(int 0..100), +20/+24 rand offsets |
| 73124 | 9460 | `brush_index` | |
| 73136 | 9472 | `correction` | clamp 0..99 |
| 73264/73284/73304 | | `q0, q1, q2` | TabletEvent's last-3-points buffer (q0 newest) |
| 73324 | | `q_valid` (u8) | |
| 73328 | | `refresh_rect` | dirty rect pushed to screen |
| 73344 | | `refresh_counter` | |
| 78484 | | `dab_carry` (f32) | distance since last dab |
| O+7740 | | `paper` → u8[512×512] | height map (img/*.png), indexed `(x%512) + (y%512)·512` |

`Point` (func 162, `MakePoint`):
```
struct Point { f32 x; f32 y; f32 p;
               i32 alt10 = trunc(alt_rad·180/π·10);               // tenths of a degree
               i32 az10  = posmod(trunc(az_rad·180/π + 90), 360)·10; }  // +90° rotation, whole degrees ×10
```
func 81 = positive modulo `((a % b) + b) % b`. func 63 = rect clear. func 166 = rect union (ignores empty rects).
func 174 = rect from 2 points (min/max). func 175 = normalise rect. func 184 = int Euclidean distance (sqrt of int dx²+dy²).
func 1811/1822 = cos/sin (f64), 1804/1799 = cosf/sinf, 1798 = powf.

---

## 2. TabletEvent (func 163): reset + quadratic 4× upsampling

```
TabletEvent(x, y, p, alt, az):
    n = MakePoint(x, y, p, alt, az)
    if p == 0 or !q_valid:
        q0 = q1 = q2 = n ; q_valid = 1               // pressure 0 ALWAYS resets the 3-point buffer
    else:
        q2 = q1 ; q1 = q0 ; q0 = n                    // q0 newest

    // Quadratic (Lagrange) through q0 (s=0), q1 (s=1), q2 (s=2), per axis:
    c = 0.5·(q0 − 2·q1 + q2)
    b = (q1 − q0) − c
    P(s) = q0 + b·s + c·s²                            // P(0)=q0, P(1)=q1, P(2)=q2
    for i in 3, 2, 1, 0:                              // 4 sub-samples per event, oldest first
        s  = i·0.25                                   // 0.75, 0.5, 0.25, 0.0
        xs, ys = P(s)
        ps = q1.p·(i/4) + q0.p·((4−i)/4)              // pressure: LINEAR between q1 and q0
        StrokeSample(xs, ys, ps, alt, az)             // func 164 — alt/az = RAW args of this event (not interpolated)
    return 0
```
So the curve covers the segment q1→q0, with its curvature taken from q2. s=1 is skipped because the previous
event already emitted it as s=0. At pointer-down the host sends p=0 then p=c, so the first 4 sub-samples ramp
pressure 0.25c, 0.5c, 0.75c, c at the same position.

---

## 3. StrokeSample (func 164): stroke state machine + box-filter smoothing

```
StrokeSample(x, y, p, alt, az):
    if !material_loaded(71404): LoadMaterialJS()      // import 0
    raw_prev = raw_cur ; raw_cur = MakePoint(x,y,p,alt,az)
    p_now  = Get(raw, cur).p ; p_before = Get(raw, prev).p   // funcs 250/251 → 247

    if p_before == 0 and p_now > 0:                   // ---- STROKE START ----
        stroke_rect = ∅ ; stroke_active = 1
        HistoryFill()                                 // func 243: hist[0..2c] = raw_cur, sm_prev = raw_cur, sm_cur = BoxFilter()
        if brush.kind == 3: brush.+20 = rand()%256 ; brush.+24 = rand()%256   // not pencil

    if stroke_active:
        HistoryPush()                                 // func 245: hist[k+1]=hist[k] for k=198..0 ; hist[0]=raw_cur ; sm_prev = sm_cur
        sm_prev = sm_cur ; sm_cur = BoxFilter()       // func 244
        tmp = ∅
        if p_now == 0:                                // ---- PEN-UP FLUSH ----
            if !StrokeEnded():
                stroke_rect ∪= refresh_rect ; Refresh(refresh_rect) ; refresh_rect = ∅
                for i in 0 .. 2c   while !StrokeEnded():   // drain the filter window
                    brush_fn(O, &tmp)                 // dab the segment sm_prev → sm_cur
                    stroke_rect ∪= tmp ; refresh_rect ∪= tmp
                    HistoryPush() ; sm_prev = sm_cur ; sm_cur = BoxFilter()   // pushes p=0 samples
                Refresh(refresh_rect) ; refresh_rect = ∅
        else:                                         // ---- NORMAL SAMPLE ----
            if brush_fn(O, &tmp) != 0:
                stroke_rect ∪= tmp ; refresh_rect ∪= tmp
                Refresh(refresh_rect) ; refresh_rect = ∅          // (throttle counter 73344, effectively every call)

    if StrokeEnded():                                 // ---- STROKE END ----
        if stroke_active:
            if brush.kind == 24: brush_fn(...) ; Refresh      // Lua brush gets one last call
            clamp stroke_rect to [0,W]×[0,H]
            if non-empty and UndoPush(1):             // func 78
                Blit(dst=backup(67740), stroke_rect, src=layer(67736))   // func 79: resync the pre-stroke backup
            stroke_rect = ∅ ; stroke_active = 0
```

**BoxFilter (func 244)**: the "brush correction":
```
N = min(2·correction + 1, 199)
sm_cur.x, .y, .p = mean(hist[0..N−1].x/.y/.p)         // plain unweighted average, f32
sm_cur.alt10, .az10 = hist[correction].alt10/.az10     // the CENTRE sample (matches the filter delay)
```
- correction 0 → N=1 (no smoothing). Default 8 → **N=17 sub-samples ≈ 4.25 pointer events**, lag = 8 sub-samples = 2 events.
- It is not exponential smoothing and not Catmull-Rom. It is a centred FIR box filter over the 4×-upsampled stream.
- Pressure goes through the same box filter, so a step in pressure becomes a linear ramp N sub-samples long.
- **Stroke-end taper comes from this**: on pen-up the raw point is held with p=0 and the filter is drained (up to N pushes),
  so position converges to the last point while pressure ramps down linearly to 0. The stroke **start** is not tapered the same way.
  HistoryFill fills the whole window with the first sample (p≈0.25·c), so the start ramp is only the 4-sample one from §2,
  plus the iOS host ramp.

**StrokeEnded (func 165)**:
```
kind ∈ {11..18, 20, 21, 22}  (bitmask 0x77F800):  return raw_prev.p > 0 and raw_cur.p == 0
otherwise (pencil 6/27/28/29):                    return sm_prev.p  > 0 and sm_cur.p  == 0
```
For the pencil the stroke ends only when the smoothed pressure reaches exactly 0, which is after the whole window is zeros.
The last segment (sm_cur.p == 0) is never dabbed, because the check runs before brush_fn.

**Undo (func 78 mode 1)**: runs at **stroke end**. It does not run at the start. It allocates `h × ((w+3)/4·4)` bytes
for the clamped stroke bbox, copies those pixels from the **pre-stroke backup** buffer (67740) into the record (func 69 + 79),
stores the rect, then subtracts the size from the memory budget (67792). After that, 164 copies the new pixels into the backup.
The host also calls `AddLayerToHistoryEvent` before the first TabletEvent if `LAYER_MODIFIED`.

---

## 4. View → canvas transform (func 247, called through 248/249/250/251)

`Get(O, which, prev?, &x,&y,&p,&az,&alt10)` selects raw_cur / raw_prev / sm_cur / sm_prev and maps it to canvas pixels.
```
θ = view_angle·π/180 ; if hflip: θ = 2π − θ ; c = cos θ ; s = sin θ
S = view_scale ; W,H = canvas size ; Vw,Vh = view size ; ox = hflip ? −offX : offX
bw = ceil((|c·W| + |s·H|)/S) ; bh = ceil((|s·W| + |c·H|)/S)       // rotated canvas bbox in view px
cw = ceil(W/S) ; ch = ceil(H/S)
u = (x − (ox  + (Vw − bw)/2)) − 0.5·(|c·cw| + |s·ch|)              // integer /2 on the (V−b) term
v = (y − (offY + (Vh − bh)/2)) − 0.5·(|s·cw| + |c·ch|)
X = W/2 + S·(c·u − s·v)
Y = H/2 + S·(s·u + c·v)
if hflip: X = (W − 1) − X
az_deg = posmod(az10/10, 360) ; if hflip: az_deg = 360 − az_deg
alt10  = as stored (float)
```
The transform runs **after** smoothing. The box filter and the interpolator both work in view pixels.
**Azimuth is not corrected for view rotation.** The dab angle is used in canvas space as received.
The ghost (func 108) adds `view_angle` for drawing on screen.

---

## 5. Pencil dab emitter (func 189): `brush_fn` for kinds 6, 27, 28, 29

```
PencilSegment(O, out_rect):
    if layer_locked_or_hidden (func 178) and kind ∉ {9,10}: return 0
    (x1,y1,p1,az1,alt1) = Get(sm_cur)  ; (x0,y0,p0,_,_) = Get(sm_prev)
    alt1 = |alt1|  (sign kept: alt1_signed < 0 → mode 3)
    h = brush.hardness (0..100) ; size = brush.size (1..500)

    // Hardness = pressure-curve exponent  ← the real "pressure curve"
    g = (h >= 50) ? 1 + 3·(h − 50)/50              // 1 … 4
                  : 1 / (1 + 3·(50 − h)/50)        // 0.25 … 1
    P1 = p1^g ; P0 = p0^g                          // default pencil h=40 → g = 1/1.6 = 0.625
    if P1 > 0 and P0 == 0: dab_carry = 0

    out_rect = rect(int x0,int y0, int x1,int y1)
    if floor(x1)==floor(x0) and floor(y1)==floor(y0): return 1      // < 1 px move → no dab (a still tap leaves no mark)

    D1 = size·0.5 + size·0.5·P1                    // diameter: 50% of size at P=0 … 100% at P=1
    D0 = size·0.5 + size·0.5·P0
    if D1 < 0.7 and D0 < 0.7: return 1
    r  = D1/2
    mode = (alt1_signed < 0) ? 3 : 2 ; if kind == 8: mode = 3        // 2 = draw, 3 = erase (inferred)

    // Tilt → ellipse axes (constant over the segment)
    altR = alt1/10 · π/180
    if altR < 0.558505 (32°):
        k     = cos(altR + 0.785398 + 0.226893)    // cos(alt + 45° + 13°) = cos(alt + 58°)
        major = r + k²·max(600 − r, 0)             // 600 = cap on how far the side of the lead reaches
        minor = max(r, major/20)
    else:
        major = minor = r
    a = max(major, minor) ; b = minor              // semi-axes passed to the rasteriser
    θ = (90 − az1)·π/180                           // ≡ −(pointer azimuth), see Point.az10 (+90)

    // Dab spacing along the INTEGER segment (x0,y0)→(x1,y1)
    step = max(1, trunc(2·b/10))                   // 10% of minor diameter, whole pixels, min 1
    dist = sqrt((ix1−ix0)² + (iy1−iy0)²)           // func 184, int endpoints
    t = −dab_carry ; drew = false
    while t < dist:
        if step <= t + dab_carry:                  // skips k=0, so dabs land at −carry + k·step, k ≥ 1
            px = trunc(ix0 + t·dx/dist) ; py = trunc(iy0 + t·dy/dist)
            DrawPencilDab(canvas=O+4064, px+0.25, py+0.25, a, b, θ, altR, paper, P1, mode)   // func 186
            dab_carry = 0 ; drew = true
            out_rect ∪= DabBBox(...)               // see §6
        t += step
    dab_carry = drew ? dist − (t − step) : dab_carry + dist          // distance since last dab
    return 1
```
- **Per segment, size, pressure, altitude and azimuth are NOT interpolated.** Every dab in the segment uses the
  end-point (sm_cur) values. Only position is interpolated, and it is truncated to whole pixels plus 0.25.
  Segments are short (4 sub-samples per event plus the box filter), so the steps rarely show.
- Pressure works in two places. **Size** goes from 50% to 100% of the brush size, linear in P = p^g. **Density** is P itself,
  passed to 186. P also sets the paper "shift" below (÷P).
- No velocity term anywhere in the pipeline.
- `dab_carry` is a global and is only reset when P0 == 0 and P1 > 0, which rarely happens at a pencil stroke start
  (HistoryFill makes sm_prev = sm_cur with p>0), so a little carry can leak from one stroke into the next.

## 6. Dab centre offset and dirty bbox (func 189 after each dab; func 186 head computes the same shift)

```
sA,cA = sin/cos(altR) ; sθ,cθ = sin/cos(θ)
texel = paper[(px%512) + (py%512)·512]                      // u8 height 0..255
q     = min(1, sqrt(4·a·b)/100)                              // 186 uses a,b; 189's bbox uses R1,R2 below
shift = q / P1 · 6 · (1 − texel/255)                         // paper-grain shift, larger at low pressure / in valleys
centre' = (px + 0.25, py + 0.25) + cA·((a − b) − shift)·(cθ, −sθ)
R1 = sqrt(cA²b² + sA²a²) ; R2 = sqrt(sA²b² + cA²a²)
halfW = sqrt(cθ²R2² + sθ²R1²) ; halfH = sqrt(cθ²R1² + sθ²R2²)
bbox = [centre'.x ± (halfW+10), centre'.y ± (halfH+10)]     // +10 px margin
```
The tilted ellipse is moved by (a−b) along the azimuth direction, so the contact patch spreads from the tip
toward the pen body, minus the paper shift.

**Ghost (func 108 → import 3 `DrawGhostBrushPencil(shift_x, shift_y, a, b, angle)`)**: same axis formula with
**r = size/2** (no pressure, no paper), `a = max(major,minor)`, `b = minor`, `d = a − b`,
`θg = (90 − az + view_angle)·π/180`.
No flip: `shift_x = d·cos θg, shift_y = −d·sin θg, angle = −θg`. Flip: `θg' = 2π − θg`,
`shift_x = −d·cos θg', shift_y = d·sin θg', angle = −θg'`.

---

## 7. Hand-off to the rasteriser (for the sibling agent)

| func | signature | role |
|---|---|---|
| **186** | `(i32 canvas, f32 cx, f32 cy, f32 a, f32 b, f32 θ, f32 altRad, i32 paper, f32 P, i32 mode)` | dab setup: centre texel, shift, offset, calls 187 then 188, frees the mask |
| **187** | `(f32,f32,f32,f32,f32, i32 *out, i32 *out)` | builds the ellipse span/mask table (mallocs, uses sinf/cosf) |
| **188** | `(i32,i32,i32,i32, f32×7, i32)` | **per-scanline loop** over the mask with paper and pressure; calls 215 per span, 194 |
| **215** | `(i32 canvas, i32 x0, i32 x1, i32 y, i32, i32, f32 v, i32 mode)` | **span writer**: v → `clamp(sqrt(v)·0.0625,0,1)·255`; layer rows are packed 4 px per i32 (stride `(w+3)>>2` words), written with i32 stores (no store8) |
| 194 | `(f32×7, i32×6)` | helper called from 188 (sin/cos) |
| 199 | `(i32) → i32` | builds an 8-layer bitmask byte used by 215 |
| 185 / 190 | `(i32,i32)→i32` | kneaded eraser (kind 8/10) / kind 23 emitters, same structure as 189 |

## 8. Call graph

```
JS pointer events
 └─ TabletEvent 163 ── MakePoint 162
     └─ StrokeSample 164 (×4 per event)
         ├─ LoadMaterialJS import 0 (once)
         ├─ 250/251 → 247 Get(raw cur/prev)        ├─ 81 posmod, 1811 cos, 1822 sin
         ├─ 243 HistoryFill → 244 BoxFilter
         ├─ 245 HistoryPush ; 244 BoxFilter
         ├─ 165 StrokeEnded ; 63 rect clear ; 166 rect union ; 217 rand
         ├─ 167 Refresh(rect) → call_indirect *(71980)  (screen blit)
         ├─ 78 UndoPush(1) → 69, 79 Blit(→2000 memcpy), 80, 65, 58 ; 79 resync backup
         └─ call_indirect brush_fn = table[ kindTable@5120[kind] ]   (set by 91 BrushSelectionEvent via 66)
              kind 6,27,28,29 → 189 PencilSegment
                 ├─ 178 layer check ; 248/249 → 247 Get(smoothed cur/prev)
                 ├─ 1798 powf ; 1799 sinf ; 1804 cosf ; 1811/1822
                 ├─ 174/175 rect ; 184 dist ; 166 union
                 └─ 186 DrawPencilDab → 187 mask, 188 scan → 215 span (→199), 194
              kind 8,10 → 185 ; 23 → 190 ; 24 → 222 (Lua VM) ; others 177/200/202/206/210/213/219/197
```
Kind → func table (data @5120, then elem table): 0→177 1→200 2,3→202 4,5,7,9,14,19,25→177 6,27,28,29→189
8,10→185 11→219 12→import 9 13→import 10 15,17→206 16,18→210 20,21,22→213 23→190 24→222 26→197.

**Lua:** the paths from 163 reach 38 functions and none of them is Lua, except through kind 24 (func 222, 372 reachable functions, the Lua VM).
The pencil is plain C++.

## 9. Setters

- `SetBrushCorrection` (158): `correction = clamp(v, 0, 99)` → 73136.
- `BrushSizeChangeEvent` (100): `brush.size = trunc(min(v < 1 ? 0 : v, 500))`.
- `BrushHardnessChangeEvent` (101): `brush.hardness = trunc(clamp(v, 0, 100))`.

---

## Confidence

**Certain (read straight from the instructions):**
- 4 sub-samples per event, quadratic through the last 3 points (s = 0.75, 0.5, 0.25, 0), linear pressure, raw alt/az.
- p == 0 resets the TabletEvent buffer. The host sends 4 zero-pressure events on pointer-up and one before pointer-down.
- Box filter of N = 2c+1 (max 199) over x, y, p, with alt/az taken from the centre sample. Correction is clamped 0..99.
- The stroke-start, end and flush logic and the StrokeEnded rule, with its kind bitmask 0x77F800.
- Hardness → exponent g formula. Diameter = size·(0.5 + 0.5·p^g). The 0.7 cutoff.
- Tilt constants: 32° threshold (0.558505), cos(alt + 58°), 600, /20. Spacing max(1, trunc(D_minor/10)) with carry.
  Positions truncated to int plus 0.25. Attributes held constant over a segment.
- Shift formula constants (100, 6, 1 − texel/255) and the 512×512 paper indexing. The ghost formula.
- The view transform formula. Which function is cos and which is sin was checked from the musl code (1804 returns 1 for tiny x, so it is cosf).

**Inferred:**
- Field names (view offset/size, backup vs current layer buffers in the undo path). Mode 2/3 = draw/erase.
- That azimuth is not corrected for view rotation. The code says so; whether it is intended is not known.
- The `refresh_counter` throttle seems to refresh every dab in practice.
- The 4-px-per-word layout in 215 comes from the `(w+3)>>2` stride and the absence of byte stores. The sibling should confirm it.
- 167 → `*(71980)` is the screen-blit callback; it leads toward DrawCanvasRectFromArray, not traced.
