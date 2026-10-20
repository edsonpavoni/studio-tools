# 11 — 8bitpaint pencil: the dab rasteriser, paper texture and pencil grades (WASM study)

Source: `studio/graphite/reference/8bitpaint/8bitpaintpencil/index.wasm` (v1.5.0.0), static reading only (nothing executed).
Study notes. No code copied; the algorithm and constants below were rebuilt from the bytecode.

Function numbers are **original wasm indexes** (as in `index.wat` `(func (;N;)`).
Method: the binary is Asyncify-instrumented (every function is wrapped in `global 3` unwind/rewind state). I replaced `global.get 3` with `i32.const 0` in the .wat, re-assembled, and ran binaryen constant-folding passes (no inlining, no function removal, so the indexes stay the same). That gave readable s-expressions (`wasm-dis`, cleaned index = original − 56). The scratch copies are in the session scratchpad, not in the repo.

---

## 0. Headline: three premises corrected

1. **The layer byte is lightness, not density.** A new canvas is filled with **255 = white paper** (F61 memset 255). Drawing *subtracts* toward a per-pencil floor. Erasing adds back toward 255.
2. **"Hardness" is not a radial falloff.** The 0–100 slider becomes a **pressure exponent**: `p' = p^k`. The dab profile itself has no hardness parameter.
3. **The pencil app has no colour multiply.** It is one 8-bit canvas shown through a 256-entry **gamma-1/2.2 grey palette**. I did not find any per-layer colour/multiply in the pencil binary's draw path (the full 8bitpaint app may do this, but this binary doesn't).

---

## 1. Call graph (pencil path)

```
JS pointer event ──► TabletEvent F163 (x, y, pressure, altitude, azimuth : f64)
   F162  pack point {x f32, y f32, p f32, alt_i = int(alt_deg*10), az_i = ((int(az_deg+90)) mod 360)*10}
   keeps the last 3 raw points (73264 / 73284 / 73304, 20-byte records)
   emits 4 sub-points per event: quadratic curve through the 3 points at t = 0.75, 0.5, 0.25, 0
       pressure linearly blended between the current and previous raw point
   └► F164 (per sub-point)
        F162 pack again; shift point history (63664…)
        F243/F244/F245  moving average of the last (2·corr+1) points for x, y, pressure
                        (corr = SetBrushCorrection F158, 0–99, default 8 → 17 points);
                        alt/az are taken from the newest point
        F247 (via F248 cur / F249 prev)  screen→canvas transform (view rotation 8308,
                        h-flip 8304, scale 8300); returns x, y, p, az_deg, alt*10
        call_indirect [71392]  ← brush function, selected by BrushSelectionEvent F91:
                        fn = table[ mem32[5120 + 4*kind] ]   (F66)
            kind 6 Pencil, 27 4B, 28 HB, 29 2H  → slot 11 → **F189 (pencil stroke segment)**
            kind 0 Pen → F177; 1 Gray scale pen → F200; 2 Gray pen 2 / 3 Marker → F202;
            8/10 kneaded eraser → F185; 23 smudge → F190; 11 bucket → F219
        F166 union dirty rect; F78/F79 undo snapshot + backup copy; display via F135
   F189  ── per segment prev→cur: computes radii, spacing, loops dabs
     └► F186 (one dab)   tilt offset + texture "tooth" displacement
          ├► F187  build the ellipse polygon (malloc, freed after)
          └► F188  scanline-fill the convex polygon, per scanline:
                ├► F194  per-pixel dab value (0..255) into an int span buffer   ← hot loop 1
                └► F215  composite span into the 8-bit layer with texture       ← hot loop 2
   display: F135 → F123/F124/F125/F126 (zoom-dependent resamplers; palette lookup)
            → import 8 DrawCanvasRectFromArray(dirty rect)
```

Signatures (wasm types):
- `F186(canvas i32, x f32, y f32, a f32, b f32, rot f32, alt f32, tex i32, p f32, mode i32)`
- `F187(cx f32, cy f32, A f32, B f32, rot f32, out_ptr i32*, out_n i32*)`
- `F188(canvas, poly, n, tex, cx f32, cy f32, a f32, b f32, rot f32, alt f32, p f32, mode i32)`
- `F194(cx f32, cy f32, a f32, b f32, rot f32, alt f32, p f32, x0 i32, x1 i32, y i32, buf i32, *first, *last)`
- `F215(canvas, x0 i32, x1 i32, y i32, tex i32, buf i32, area f32, mode i32)`

Tool record (36 bytes, table at 72080, index in 73124): +0 kind, +4 size (1–500, F100), +8 hardness (0–100, F101), +12 palette (F110), +20/+24 random 0–255 (only re-rolled for the marker, kind 3, at stroke start).

Trig helpers (checked against the musl small-argument branches): F1799 = sinf, F1804 = cosf, F1811 = cos, F1822 = sin, F1798 = powf.

---

## 2. Stroke segment → dabs (F189)

```
h  = tool.hardness                       # 0..100
k  = h >= 50 ? 1 + 3*(h-50)/50           # 1 .. 4
             : 1 / (1 + 3*(50-h)/50)     # 0.25 .. 1
p' = pow(p_smoothed, k)                  # done for the cur AND the prev point
     # h=40 (4B/HB default) → k=0.625 (boosts light pressure); h=50 (2H) → k=1; h=100 → k=4; h=0 → k=0.25

s  = tool.size
if s/2 + p'*s/2 < 0.7 (for both cur and prev) : no dab
r  = s*(1 + p')/4                        # radius: s/4 at zero pressure, s/2 at full

alt = altitude in radians (pi/2 = vertical; mouse = pi/2)
if alt < 0.5585053606 (32°):             # lying pencil → long ellipse
    a = r + cos(alt + pi/4 + 0.2268928028 [13°])^2 * max(600 - r, 0)
    b = max(r, a/20)
    # at alt=0: a ≈ 0.28*600 + 0.72*r ≈ 170 px; continuous with a=r at 32°
else:
    a = b = r                            # upright pencil → circle

rot  = (90 - az_internal) deg → rad  =  −azimuth   (az_internal = azimuth_deg + 90)
mode = (kind == 8 or raw altitude < 0) ? 3 (lighten/erase) : 2 (draw)

step = max(1, int(2*b/10))               # dab spacing = 10% of the minor diameter, integer px
dist = |cur_int − prev_int|              # integer endpoints; skip if both coords floor-equal
for t from −carry by step while t < dist:     # carry kept in global 78484
    (dx,dy) = prev + (cur−prev)*t/dist  → truncated to int
    F186(canvas, dx+0.25, dy+0.25, a, b, rot, alt, texture, p'_cur, mode)
    union the dab bbox into the dirty rect
carry = dist − (last t)                  # spacing continues across segments
```

Notes: the dab pressure and radius are the **current** point's (not interpolated per dab). Positions snap to integer + 0.25, so there is no sub-pixel placement.

---

## 3. One dab: tilt offset and texture "tooth" displacement (F186)

```
T0   = tex[(int cx mod 512) + 512*(int cy mod 512)]        # paper height at the dab centre
g    = min(sqrt(4ab)/100, 1)                               # = min(sqrt(ab)/50, 1)
m    = 6 * g / p' * (1 − T0/255)                           # tooth push-back; big at low pressure / in valleys
A    = sqrt(cos²(alt)*a² + sin²(alt)*b²)                   # projected half-length of the tip
e    = A − b
dir  = (cos rot, −sin rot)                                 # = (cos az, sin az) in y-down screen coords
c'   = (cx, cy) + cos(alt) * (e − m) * dir                 # push the ellipse forward along the azimuth,
                                                           # pulled back by the tooth term
poly = F187(c', A, b, rot)                                 # ellipse, semi-axes A (along dir) and b
F188(poly, c', a, b, rot, alt, p', mode)
```

For an upright pencil, cos(alt) = 0, so there is no offset and no tooth displacement. The displacement only acts on tilted strokes.

**F187 polygon:** N = 4 if A ≤ 2, else 4·floor(b) vertices. Quarter-ellipse samples at x = −A … 0 in N/4 steps, `y = max(sqrt(b² − b²x²/A²), 3)`. A minimum half-width of 3 px keeps the ends from collapsing. The samples are mirrored and then rotated (x' = x cos − y sin + cx, y' = −x sin − y cos + cy).

**F188 scanline fill:** it finds the top and bottom vertex. For each pixel-centre row it intersects the left and right edges, rounds to integer x0..x1, and clips to the canvas. It allocates an int32 span buffer (from a static 1024-int pool, or malloc when larger) that is 4-aligned (x0 & ~3), because F215 writes 4 pixels per u32.
- Kneaded eraser (kind 8): the span is filled with the constant `int(p'·255)`.
- Otherwise F194 fills it, and F215 composites it.

---

## 4. Per-pixel dab value: the tilted-tip depth profile (F194)

This is the code's own arithmetic. The geometric reading follows it.

```
s = sin(alt), c = cos(alt)
D  = a²c² + b²s²
H  = c*b + sqrt(b²c² + a²s²)          # full height of the tip
for x in x0..x1:
    dx = x − cx ; dy = y − cy
    u  = cos(rot)*dx − sin(rot)*dy        # along the major axis
    v  = sin(rot)*dx + cos(rot)*dy        # across
    disc = a²b²c² + b⁴s² − (b²s² + a²c²)*v² − b²*u²
    R    = a * sqrt(max(disc, 0))
    z    = (s*c*(a² − b²)*u − R) / D      # lower surface height under this pixel (if |D|>1e-5)
    depth = max(0, c*b − z)
    val  = max(0, depth/H − (1 − p'))
    buf[x] = int(255 * val)
first/last = the first and last x with buf > 0 (trims the span)
```

**Geometric reading (inferred, but it fits every constant).** The lead tip is a half-ellipsoid: radius b, length a along the pencil's axis, tilted to altitude `alt` toward the azimuth. `c·b` is the top of its tilted equator rim and `−sqrt(b²c²+a²s²)` is its lowest point, so H is its full vertical extent. The tip is pressed into the paper to a fraction **p'** of H. A pixel's value is how far the tip surface at that pixel lies below the cutting plane, normalised to H.

**Upright pencil (alt = 90°, a = b = r):** `val = sqrt(1 − (ρ/r)²) − (1 − p')`, with ρ the distance from the centre. This is a **spherical cap**: not linear, not smoothstep, not a power law.
- Peak (centre) = 255·p'.
- Visible radius = `r·sqrt(p'(2 − p'))`. Light pressure gives both a smaller footprint and a fainter peak, and the cap has a steep rim.

**Flat pencil (alt → 0):** `val = (1 + sqrt(1 − u²/a² − v²/b²))/2 − (1 − p')`. At p' > 0.5 the whole ellipse marks. At low p' only the core marks.

**Anti-aliasing:** there is none at the rim besides the profile itself. The value goes to 0 continuously at the contact circle, so the rim is soft through the cap shape, not through coverage sampling. The polygon only bounds the work.

---

## 5. Texture and compositing into the 8-bit layer (F215)

The layer is u8, row stride `4·ceil(w/4)`, and is processed 4 pixels per u32 word.

```
floor F = (kind == 29 /*2H*/) ? 137 : (kind == 28 /*HB*/) ? 30 : 0     # 4B and plain Pencil: 0
G       = int(255 * clamp(sqrt(area)/16, 0, 1)),  area = 4ab   → full strength once sqrt(ab) ≥ 8 px
T       = tex[(x & 511) + 512*(y & 511)]                            # 1:1 canvas pixels, 512-tiled
tooth   = (G * (255 − T)) / 255                                     # integer
d       = max(0, buf[x] − tooth)                                    # texture = subtractive threshold

mode 2 (draw):
    if L > F:
        L' = L − trunc((255 − F) * d / 255)
        L  = clamp(L', F, 255)
    else: unchanged                       # already darker than this grade can reach
mode 3 (lighten / erase):
    L = min(255, L + d)
```

- **Texture formula:** `mark = max(0, dab − G·(255 − T)/255)`. Paper peaks (T high, bright) take graphite first. Valleys (T low) need dab values above `255 − T`. The same formula applies at rim and core, but because the rim values are small, the rim (and light pressure overall) breaks up first. That rim effect emerges from the formula; there is no separate rim branch.
- **Small dabs get less texture:** G drops linearly below sqrt(ab) = 8 px.
- **No texture loaded:** the texture reads 255 everywhere and has no effect. `none.png` is all 255.
- **Build-up:** this is **additive darkening with a floor cap**: not max, not alpha-over. There is no separate per-dab opacity constant; the per-dab amount is the profile value times `(255 − F)/255`. With 10% spacing a pixel near the stroke centre gets about 10 overlapping dabs per stroke pass, so at firm pressure the stroke saturates to the floor quickly, while at light pressure the cap and the texture threshold leave grain.
- **Quantisation:** the increment is truncated per dab. For 2H, where (255 − F) = 118, any `d ≤ 2` adds nothing, so 2H light pressure stays very faint.

**Paper texture load (LoadMaterialEvent F139):** RGBA → `T = trunc(0.299R + 0.587G + 0.114B + 0.5)`. Alpha is ignored. Stored 512×512 u8 at [71404]; there is no scaling and no offset for the pencil.

Measured luma of the shipped papers (mean / p5 / p50):

| file | mean | p5 | p50 |
|---|---|---|---|
| none | 255 | 255 | 255 |
| noise (default, index 1) | 219 | 108 | 252 |
| paper | 181 | 121 | 189 |
| cotman | 207 | 132 | 217 |
| langton | 219 | 102 | 242 |
| monval_tradition | 233 | 180 | 242 |
| muse_touch | 197 | 94 | 211 |
| mermaid2 | 211 | 110 | 228 |
| wargman | 180 | 113 | 183 |

---

## 6. Per-pencil parameters

All four pencils run the same code (F189 → F186 → F194/F215). The only per-grade branch in the dab path is the floor in F215. A search for kind constants 6/27/28/29 across F164–F215 found nothing else. The other difference is the JS default hardness.

| grade | kind | floor F (darkest linear L) | per-dab gain (255−F)/255 | darkest displayed grey | default size / hardness → k |
|---|---|---|---|---|---|
| Pencil | 6 | 0 | 1.00 | 0 (black) | 16 / 40 → 0.625 |
| 4B | 27 | 0 | 1.00 | 0 (black) | 16 / 40 → 0.625 |
| HB | 28 | 30 | 0.882 | ≈ 96 | 16 / 40 → 0.625 |
| 2H | 29 | 137 | 0.463 | ≈ 192 | 16 / 50 → 1.0 |

So "4B soft/dark versus 2H hard/light" comes from (a) the darkness cap, (b) a slower per-dab gain, and (c) for 2H a linear rather than boosted pressure curve. Neither size nor texture strength changes per grade. Darkest displayed grey = `255·(F/255)^(1/2.2)`.

I found no static per-pencil float table in the Data section. The tool table at 72080 is BSS, filled from JS settings.

---

## 7. Display / gamma

- The canvas is a single 8-bit indexed bitmap (F69 bpp=8, palette at bitmap+44).
- F68 palette: for v = 0..254, `grey = trunc(255·(v/255)^0.4545454 + 0.5)` into R=G=B. Entry 255 is `0xFFFFFF` (white).
- So **the layer stores linear lightness and the display applies a 1/2.2 encode**. Darkening math happens in linear space, which makes light strokes look lighter on screen than a straight subtraction in display space would.
- F123–F126 resample by zoom (nearest / filtered variants) and do only a palette lookup. Alpha comes from palette byte 3: 255 marks transparent, and 0 stays opaque.
- The blit is import 8 `DrawCanvasRectFromArray` (F135) over the dirty rect.

---

## 8. Pseudo-code summary for our engine

```
on input point: smooth (17-pt moving average, plus 4 quadratic sub-steps per event)
p' = p^k(hardness)
r  = size*(1+p')/4 ; (a,b) = circle, or a long ellipse below 32° altitude
for each dab every max(1, int(b/5)) px along the segment:
    centre += cos(alt)*(A − b − 6*min(√(ab)/50,1)/p'*(1 − T(centre)/255)) * dir(az)
    for each pixel in the ellipse (A, b):
        v = 255*max(0, tipDepth(u,v; a,b,alt)/H − (1 − p'))      # spherical cap when upright
        d = max(0, v − min(√(ab)/8,1)*(255 − T(x,y)))             # T tiled 512, 1:1
        L = max(F_grade, L − (255 − F_grade)*d/255)              # L: 255 = white, linear
display: grey = 255*(L/255)^(1/2.2)
```

---

## 9. Confidence

**Certain** (read directly from the de-asyncified code; constants exact):
- The call chain 163 → 164 → [71392] = 189 → 186 → 187/188 → 194/215, and the kind → function table at 5120.
- The hardness → exponent formula and powf. Radius `size(1+p')/4`; the 0.7 skip; the 32° threshold with the `600`, `π/4 + 0.2269`, `/20` constants; spacing `int(2b/10)`.
- The F186 offset and tooth formula (constants 6, /100, /255) and the F194 arithmetic as written.
- F215: the floors 137/30/0 keyed on kinds 29/28/other, the `(255−F)` gain, the clamp, `G = clamp(√(4ab)/16)`, the `255 − T` threshold, 512 tiling, and the additive erase.
- Texture luma weights; the canvas initialised to 255; the gamma 1/2.2 palette.

**Inferred:**
- The physical reading of F194 (a half-ellipsoid tip pressed to depth p'·H). The algebra is certain; the interpretation fits the vertical and flat limits exactly.
- The role of `m` as a deliberate "tooth catch" displacement.
- Which raw altitude < 0 inputs reach mode 3 (probably a flipped or eraser stylus; standard pointer events never give negative altitude).
- The ~10-overlap build-up estimate.

**Not found / not checked:**
- Any per-layer colour multiply or layer opacity in the pencil binary. The pencil canvas is one indexed bitmap; the 9-entry structures at 71412/71664 look like layer metadata, but they were not traced into the draw or display path.
- Static per-pencil float tables (none exist; the grade lives in the F215 floor constants).
- Marker / Gray scale pen / Pen internals (F202 / F200 / F177): not analysed.
- Nothing was run. Every number here comes from static reading. A runtime check (instrumenting F215 inputs in the browser) would confirm the build-up rate.
