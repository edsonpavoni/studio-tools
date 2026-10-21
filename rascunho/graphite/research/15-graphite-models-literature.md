# 15 — Graphite pencil models: the maths (literature + open-source code)

Research date: 2026-10-20. Scope: formulas and constants for a plain-JS, per-pixel, 8-bit density engine on iPad + Apple Pencil. The library survey is in `studio/rascunho/research/05-graphite-brushes.md` and `06-graphite-demos.md` and is not repeated here.

Notation used throughout: `D` = graphite density at a pixel, 0..1 (×255 in the buffer). `h` = paper height 0..1, **1 = top of the tooth** (same as `engine/paper.js`). `p` = pressure 0..1. `m` = dab mask value 0..1 at the pixel. `alt` = altitude (π/2 = upright), `az` = azimuth.

Source status (read before trusting any number):

| Source | Status |
|---|---|
| Sousa & Buchanan, CGF 19(1) 2000 "Observational Models of Graphite Pencil Materials" | **Full text read** ([PDF, U Calgary mirror](https://ires.cpsc.ucalgary.ca/publ/papers/2000/refs/Costa%20Sousa%20&%20Buchanan%20'00.pdf)) |
| Sousa & Buchanan, GI 1999 "Observational Model of Blenders and Erasers…" | **Full text read** ([PDF](https://graphicsinterface.org/wp-content/uploads/gi1999-21.pdf)) |
| Sousa & Buchanan, CGF 18(3) 1999 "Computer-Generated Graphite Pencil Rendering of 3D Polygonal Models" | Downloaded ([mirror](https://ires.cpsc.ucalgary.ca/publ/papers/1999/refs/Costa%20Sousa%20&%20Buchanan%20'99a.pdf)); its pencil/paper model is the same one restated in CGF 2000, so CGF 2000 is cited |
| Sousa PhD thesis, U Alberta | Full text read ([PDF, LAC](https://nlc-bnc.ca/obj/s4/f2/dsk1/tape7/PQDD_0035/NQ46821.pdf)); adds no numbers for `ba()`/`da()` |
| Takagi, Nakajima, Fujishiro, PG 1999 "Volumetric modeling of colored pencil drawing" | **Abstract only** (paywalled, [DOI 10.1109/PCCGA.1999.803369](https://doi.org/10.1109/PCCGA.1999.803369)); one observation from their SIGGRAPH 97 sketch, quoted second-hand |
| Lee, Kwon, Lee, NPAR 2006 "Real-Time Pencil Rendering" | **Full text read** ([PDF](https://faculty.digipen.edu/~gherron/references/References/NPR/npar.pdf)) |
| AlMeraj et al. "Mimicking Hand-Drawn Pencil Lines", CAe 2008 | **Full text read** ([PDF](https://rmarcus.info/blog/assets/humanLines/Meraj08.pdf)). The 2009 C&G journal version was not retrieved |
| Rudolf, Mould, Neufeld, "A Bidirectional Deposition Model of Wax Crayons", CGF 2005 | **Full text read** ([PDF](https://people.scs.carleton.ca/~mould/papers/crayon-cgf.pdf)); a different medium, but the closest contact/friction model with published constants |
| libmypaint `master` (`mypaint-brush.c`, `mypaint-tiled-surface.c`, `brushmodes.c`, `mypaint-mapping.c`, `brushsettings.json`) | **Code read** ([repo](https://github.com/mypaint/libmypaint)) |
| mypaint-brushes `.myb` files | **Downloaded and evaluated** ([repo](https://github.com/mypaint/mypaint-brushes/tree/master/brushes)) |
| Krita `kis_texture_option.cpp`, `KisTextureMaskInfo.cpp`, `KisMaskingBrushCompositeOp.h`, `KisColorSmudgeStrategyBase.cpp` | **Code read** (KDE/krita mirror on GitHub, `master`) |
| Krita pencil presets (`.kpp`) | **Not retrieved** (not in `krita/data/paintoppresets/`; they live in a resource bundle) |
| Procreate Brush Studio handbook, Sketchbook help, Apple UIKit docs, Kodeco Apple Pencil tutorial | Read; quoted below |
| Paper (FiftyThree), Concepts, Linea Rascunho, Freeform/Notes tilt internals | **Nothing concrete found.** Paper's public facts are already in `05-graphite-brushes.md` §4 |
| "Pencil+" (PSOFT) | A 3D line renderer for 3ds Max/Maya, not a deposition model. Nothing to extract |

---

## 1. Physical / empirical pencil models

### 1.1 Sousa & Buchanan 2000: lead + paper + blender + kneaded eraser

The only published model built from SEM photographs of real graphite on real paper. It runs per pixel, and the authors report about 2E-5 s per pixel on a 1999 SGI Octane. Everything below is from CGF 2000 §3–7 unless marked.

**Lead composition (Table 2).** Mass fractions graphite / clay / wax. Wax is 0.05 for every grade.

| grade | 9H | 6H | 4H | 2H | H | F | HB | B | 2B | 4B | 6B | 8B |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| graphite `Gp` | 0.41 | 0.50 | 0.55 | 0.60 | 0.63 | 0.66 | 0.68 | 0.71 | 0.74 | 0.79 | 0.84 | 0.90 |
| clay `Cp` | 0.53 | 0.45 | 0.39 | 0.34 | 0.31 | 0.28 | 0.26 | 0.23 | 0.20 | 0.15 | 0.10 | 0.04 |

(The printed table gives 7B clay = 0.73, an obvious typo: the column runs 0.10 → ? → 0.04, so read about 0.07.) Lead thickness is linear from 2 mm (9H) to 4 mm (8B), about 0.111 mm per grade step.

**Tip.** A polygon (typical / broad / chisel point) with *pressure distribution coefficients*: `c` at a main point (default the centre) and `ci` at each vertex, each in 0..1 (the fraction of that part of the tip that touches). Values in between are linearly interpolated across the polygon's triangles. In Fig. 3 every `ci` is 0.2, 0.5 or 0.9 with `c` = 1. **Tilt is qualitative only:** "the canonical polygonal tip shape … is scaled according to the angle α defined by slanting the pencil … The more the pencil is slanted, the larger the tip is" (§5.1). The shape is then rotated by β, the wrist/arm angle. No formula for the scale is given.

**Paper.** A height field `0 ≤ h ≤ 1`, either procedural (Curtis et al. 1997) or a scanned grey sample with black = 0 and white = 1. A *grain* is the unit square of four heights `h1..h4` at (x,y), (x,y+1), (x+1,y+1), (x+1,y). One paper pixel is one grain corner. Paper weight `w` is in 0..1, 0 = thick.

**Per tip position, per grain** (§5.2–5.7):

```
pressure at coefficients:     p'c = p·c,   p'ci = p·ci                            (1)
Pa = mean of the 4 interpolated tip pressures at the grain corners

grain threshold volume Tv:
  if all hk equal:  Tv = Fs = 500 lpu                       (thin layer on a flat spot)
  else:  h'k = hmax − hk                                                         (2)
         Vg  = ¼(h'1 + h'2 + h'3 + h'4)                                          (3)
         Tv  = Vg × Fv,   Fv ∈ [1000, 3000] lpu                                  (4)
distribute to corners, higher corners get more:
  Dk = hk / Σh   (all 0.25 if Σh = 0)                                           (6)
  Lk += Dk × Tv                                                                  (5)

depth of the lead into the grain:   Dl = hmax − hmax·Pa = hmax(1 − Pa)           (7)
  clamp Dl ≥ hmin
volume bitten:
  if all hk ≥ Dl:  Bv = Tv                                                       (8)
  else:            Bv = Tv × hm,  hm = (h'max − Dl)/(h'max − h'min)              (9,10)
hardness:          Bv ← Bv × ba(Pd),   ba ∈ [0,1], soft → 1, hard → 0           (11)
per corner:        Bk = Bv × Dk                                                  (12)
grain full (Tk ≥ Lk):   Bk ← Bk × M^p,   0.97 ≤ M ≤ 0.99                        (13)
deposit:   Gk += Gp·Bk,  Ck += Cp·Bk,  Wk += Wp·Bk,   Tk = Gk + Ck + Wk         (14,15)
paper damage:  Ek = Dl × da(Pd) × w,   hk ← hk − Ek,  da: hard → 1, soft → 0    (16,17)
shade:  Ak = Gk / Ft,  Ft = Fs + Fv;   Ik = 1 − Ak                              (18,19)
```

What to take from this:

- **Contact = "skim the peaks".** The tip sits at height `1 − Pa`. Only paper above that plane bites (eq. 7, 9). Light pressure gives grainy tone; heavy pressure reaches the valleys.
- **Hardness acts twice.** `ba` (how much lead is bitten off) makes hard leads light. `da` (how much the tooth is flattened) makes hard leads burnish the paper. Repeated hard-lead passes polish the tooth flat and shiny, and later soft lead skids over it. **Neither `ba()` nor `da()` is ever given numerically**, in the paper or the thesis. Any curve we use is our own.
- **Saturation.** The paper's law is a hard per-grain cap `Lk` and then a geometric slowdown `M^p` once full. Below the cap, deposition is linear in passes.
- **Darkness ceiling (derived, not stated by the authors):** clay and wax are optically neutral and the total lead per site is capped, so the darkest possible `Ik ≈ 1 − Gp·(Tk/Ft)`. Max darkness is therefore ≈ `Gp`: 2H 0.60, HB 0.68, 2B 0.74, 4B 0.79, 6B 0.84. Real 2H and 6B differ much more than that (graphite sheen, packing), so stretch the range if you use it.
- Figure 20 gives the median intensity of real vs simulated swatches. The values printed are 0.97 (4B medium), 0.77 (4B heavy), 0.31 (6B medium) and 0.90 (6H light), but the extraction does not say which number goes with which swatch, so do not use them as targets without looking at the figure.

**Blenders (tortillon, stump) and kneaded eraser** (CGF 2000 §6–7, = GI 1999 §3–4). Same polygon + pressure-coefficient tip. A blender has a *buffer* the size of its footprint that carries lead.

```
paper → blender:   lmr = lm(x,y) × (ps × plr),  plr = 0.7                       (21)
                   lm(x,y) −= lmr;   buf(xb,yb) += lmr                          (22,23)
blender → paper:   lmr = buf(xb,yb) × (ps × plr),  plr = 0.5                    (24)
                   buf(xb,yb) −= lmr × t                                        (25)
                   lm(x,y)    += lmr × t                                        (26)
t = 0.2 tortillon, 0.5 stump   (small t = the blender stores more)
kneaded eraser: only (21) and (22). The lead sticks to the eraser and none comes back.
```

- **Version discrepancy.** In GI 1999 eq. 8–9 the paper gains `lmr` while the blender loses only `lmr·t`, which creates lead. CGF 2000 eq. 25–26 uses `lmr·t` on both sides and conserves mass. Use CGF 2000.
- Observations worth encoding: "Blending pushes the lead into the surface so that the paper's low grains become filled. This results in tones that seem smoother, more intense, and deeper in value." The kneaded eraser, "placing it firmly over an area, and then pulling quickly", lifts lead "without rubbing the paper surface". So it lifts uniformly, with no peaks-first bias.
- Tip coefficients: tortillon `ci` = 0.2, stump 0.5, kneaded eraser `ci` 0.7–0.9, with `c` = 1 in all cases.

### 1.2 Takagi, Nakajima, Fujishiro 1999: volumetric colored pencil

The paper is a thin voxel volume (paper microstructure), plus pigment distribution, plus pigment redistribution (smear/erase). It uses "volumetric offset distance accessibility" and LIC, and is "highly controllable with a small number of parameters" (abstract). The full text was not retrievable, so there are no equations here. One usable observation, from the authors' SIGGRAPH 97 sketch as paraphrased by a search summary (the rascunho page itself failed to load, so this is second-hand): **most pigment accumulates in the concave regions on the fore side of the fibres, relative to the stroke direction.** Lee 2006 (below) and the crayon model both encode the same directional effect.

### 1.3 Lee, Kwon, Lee 2006: real-time pencil (GPU, 3D shading)

Built for texture-mapped 3D shading, but two formulas transfer directly:

```
stroke overlap (eq. 3):  ca = ct·(1 − cs);   ct' = ct − µb·ca     µb ∈ [0.1, 0.3]
   (ct = current brightness 0 black..1 white, cs = stroke colour)
   in density terms D = 1 − ct, s = 1 − cs:   D' = D + µb·s·(1 − D)    → saturating build-up
white-keeping (eq. 4):   if ct is "white enough": ca ← µw·ca,  µw ∈ [0.3, 0.5]
   (paper left white by the first pass tends to stay white)
paper direction (eq. 5): ct' = ct − µp·(−d·n)  if the stroke runs against the paper slope
                         ct' = ct + µp·(d·n)   if it runs with it,      µp ∈ [0, 0.1]
   (d = stroke direction, n = paper normal from the height map)
paper tint (eq. 6):      c' = c·cp
```

Eq. 3 is the same law as libmypaint's normal-blend alpha (§2.2) and the engine's `D += a(cap − D)`. Eq. 5 is the cheap per-pixel version of Takagi's "fore side of the fibre" observation: compute `∂h/∂s` along the stroke direction and darken uphill-facing slopes.

### 1.4 AlMeraj, Wyvill, Isenberg, Gooch, Guy 2008: stroke shape

For generating lines from two endpoints. It is not for live input, but useful for a "straight-line" tool or for test strokes.

```
minimum-jerk path (Flash & Hogan), τ = t/tf:
  x(τ) = x0 + (xf − x0)(10τ³ − 15τ⁴ + 6τ⁵)       (paper prints the equivalent x0 + (x0−xf)(15τ⁴−6τ⁵−10τ³))
control points every Δt: 0.5 (< 200 px), 0.3 (200–400 px), 0.2 (> 400 px); tf = 2
"squiggle": displace each control point along the normal by D ∈ U[−5, +5] px, Catmull-Rom through them
texture: grey histogram along the centre + co-occurrence matrix of scanned real lines (2H…8B)
```

### 1.5 Rudolf, Mould, Neufeld 2005: wax crayon (the contact solve, done properly)

The cleanest published answer to "given force f and a height field, where does the tip touch?":

```
compression: F = λ·A·ΔL  (Hooke, crayon long)       λ = 0.0005
solve the tip height z by bisection/Newton so that Σ over cells of λ·max(0, hpaper+hwax − (htip − z)) = f,
   tolerance ε = λ/4
friction deposit ∝ µ·|F_N|, F_N = force projected on the local paper-slope plane facing the stroke heading;
   µpaper = 2, µwax = 0.5 (blended for thin layers)
smear mask (3×3): S_xy = α·Δz + β·(x̂,ŷ)·V̂,  α = 0.2, β = 0.8, normalised to viscosity ν = 0.5
reclaim (lift + carry): mask of max(0, V̂·(q,r)) scaled by γ·f, γ = 0.35
```

For graphite on an iPad this is overkill per dab. Its value is the cheap equivalent it suggests (§Recipe): a tip-plane threshold `t = 1 − reach·p^γ` stands in for the solve, and the deposit is weighted toward slopes facing the heading.

---

## 2. Open-source brush engines

### 2.1 libmypaint pencil presets (evaluated)

How a `.myb` value is computed (`mypaint-mapping.c`): `value = base_value + Σ_inputs f_i(input)`, where `f_i` is piecewise linear through the control points and extrapolates linearly past the ends. Opacity is `opaque × opaque_multiply`, and pencils always map `opaque_multiply` to pressure `[[0,0],[1,1]]`, so opacity = `opaque × p`. Radius = `exp(radius_logarithmic)` px, clamped to [0.2, 1000].

Evaluated at p = 0.1 / 0.5 / 1.0 (radius px, per-dab opacity, hardness, jitter σ in base radii):

| brush | r | opacity | hardness | jitter | dabs/actual r | other |
|---|---|---|---|---|---|---|
| deevad/4H_pencil | 1.20 / 1.97 / 2.82 | 0.003 / 0.013 / 0.026 | 0.23 / 0.35 / 0.50 | 0.47 / 0.35 / 0.20 | 4 | colour V 0.37 (grey) |
| deevad/2B_pencil | 1.20 / 1.97 / 2.82 | 0.015 / 0.075 / 0.150 | 0.23 / 0.35 / 0.50 | 0.47 / 0.35 / 0.20 | 4 | slow_tracking 1.03, slow_tracking_per_dab 1.5 |
| tanda/pencil-2b | 0.66 / 1.08 / 1.55 | 0.015 / 0.075 / 0.150 | same | same | 4 | anti_aliasing 1 |
| tanda/pencil-8b | 0.2(clamped) / 0.24 / 0.47 | 0.018 / 0.15 / 0.45 | 1.0 | 0.85 / 0.65 / 0.40 | 2.53 | sub-pixel dabs + heavy jitter = grain |
| ramon/2B_pencil | 1.49 const | 0.044 / 0.30 / 0.80 | 0.12 | 1.12 / 0.52 / 0.52 | 5 | |
| ramon/B-pencil | 2.45 / 1.74 / 1.11 (shrinks!) | 0.023 / 0.27 / 0.53 | 0.56 | 0.45 → none | 3.57 + 3.54 basic | opaque_linearize 0.45, smudge 0.1 |
| classic/pencil | 1.22 const | 0.07 / 0.35 / 0.70 | 0.13 / 0.25 / 0.40 | 0.47 / 0.35 / 0.20 | 4 | opaque_linearize 0.9, slow_tracking 1 |
| experimental/subtle_pencil | 2.03 / 2.48 / 3.19 | 0.1 / 0.5 / 1.0 | ≈0.5 | 0 | 2.2 | pressure via custom_input with slowness 9.23 |

Pressure curve shared by deevad and tanda: `radius_logarithmic += pwl(p; (0,−0.688), (0.753,0.236), (1,0.287))`, i.e. the radius rises fast to p ≈ 0.75 and then flattens. Hardness `+= 0.3·p`. `offset_by_random += −0.3·p`: **jitter shrinks as you press**, so a light touch looks scattered and grainy and a hard press looks solid.

Findings:
- **deevad 4H and 2B are identical except `opaque` (0.0257 vs 0.15) and colour.** That 1 : 5.8 ratio is the one sourced hardness → per-dab-opacity number in open source.
- **No stock pencil uses tilt.** Only `Dieterle/8B_Pencil#1` does: below declination ≈ 31.5° it switches to smudge 1 and adds opacity 0.6. Radius +0.19 log and jitter +1.8 apply near flat (0°) and fade to zero by 27°. Its `offset_multiplier` and `dabs_per_actual_radius` (up to 8.98) are driven by `attack_angle`, which is how far the stroke direction deviates from the pen's azimuth.
- **Most pencils set `opaque_linearize` = 0**, so per-dab opacity compounds with dab overlap and the tone depends on spacing. Only classic/pencil (0.9) and ramon/B (0.45) linearise.
- libmypaint has no paper texture. Grain comes from sub-pixel dabs + Gaussian jitter (`rand_gauss` = sum of 4 uniforms, scaled to σ = 1) + low opacity. That is why it reads as noise, not tooth.

### 2.2 libmypaint dab mask and compositing (quoted)

Dab mask (`mypaint-tiled-surface.c`, `render_dab_mask` + `calculate_opa`). `rr` = squared normalised elliptical distance:

```c
// rr = ((yy*cs-xx*sn)*aspect_ratio)^2 + (yy*sn+xx*cs)^2) / radius^2
float segment1_offset = (1.f)*(1.f-softness);
float segment1_slope  = -(1.0f/hardness - 1.0f)*(1.f-softness);
float segment2_offset = hardness/(1.0f-hardness)*(1.f-softness);
float segment2_slope  = -hardness/(1.0f-hardness)*(1.f-softness);
...
const float fac = rr <= hardness ? segment1_slope : segment2_slope;
float opa = rr <= hardness ? segment1_offset : segment2_offset;
opa += rr*fac;          if (rr > 1.0f) opa = 0.0f;
const uint16_t opa_ = opa * (1<<15);
```

So, with `rr = (d/r)²`: `opa = 1 − rr·(1/h − 1)` for `rr ≤ h` (it reaches `h` at `rr = h`), and `opa = h/(1−h)·(1 − rr)` beyond, falling to 0 at the rim. This is the legacy `dd + 1 − dd/hardness` form. Hardness 0 draws nothing. For radius < 3 px, `calculate_rr_antialiased` samples the pixel's nearest point and a point at `sqrt(1/π)` further out. `get_color` (smudge sampling) uses the same mask with hardness 0.5 and softness 0.5. It samples every pixel when r ≤ 2, otherwise every `7r`-th pixel plus a random 1/(7r) of the rest.

Anti-aliasing (`prepare_and_draw_dab`): if `radius·(1−hardness) < anti_aliasing` px (default 1), solve for a new hardness and radius that keep the "optical radius" `r − (1−h)r/2` and give exactly that fade: `h' = (R − a/2)/(R + a/2)`, `r' = a/(1 − h')`.

Opacity linearisation (`prepare_and_draw_dab`):

```c
dabs_per_pixel = (DABS_PER_ACTUAL_RADIUS + DABS_PER_BASIC_RADIUS) * 2.0;   // ≥ 1
dabs_per_pixel = 1.0 + opaque_linearize * (dabs_per_pixel - 1.0);
beta_dab = powf(1.0 - opaque, 1.0/dabs_per_pixel);   opaque = 1.0 - beta_dab;
```

Composite, normal mode (`brushmodes.c`). 15-bit fixed point, premultiplied:

```c
uint32_t opa_a = mask[0]*(uint32_t)opacity/(1<<15); // topAlpha
uint32_t opa_b = (1<<15)-opa_a;                     // bottomAlpha
rgba[3] = opa_a + opa_b * rgba[3] / (1<<15);
rgba[0] = (opa_a*color_r + opa_b*rgba[0])/(1<<15);  // g, b same
```

On a single graphite channel this is `D ← D + a·m·(1 − D)`. **Why 15 bits:** pencil per-dab opacities of 0.003–0.15 times a soft mask round to zero in 8 bits (see Recipe, quantisation).

Eraser / smudge-transparency mode (`draw_dab_pixels_BlendMode_Normal_and_Eraser`): the same, but `opa_a = opa_a * color_a / (1<<15)` *after* computing `opa_b`. With `color_a = eraser_target_alpha = 1 − eraser` (eraser = 1 gives 0), the alpha line becomes `α ← (1 − a·m)·α`. **The libmypaint eraser is a multiplicative lift**: `D ← D·(1 − a·m)`, with no texture term. `lock_alpha` scales `opa_a` by the existing alpha, i.e. paints only where there is already graphite.

Dab placement (`count_dabs_to`): `dabs = dist/r_actual·dabs_per_actual_radius + dist/r_base·dabs_per_basic_radius + dt·dabs_per_second`. For elliptical dabs the distance is measured in the ellipse's frame: `yyr = (dy·cs − dx·sn)·ratio`, `xxr = dy·sn + dx·cs`, `dist = sqrt(yyr² + xxr²)`. Between events, **x, y, pressure, declination and time are interpolated linearly per dab**, and ascension (azimuth) by `smallest_angular_difference`. Every input's mapping is re-evaluated at every dab.

Tilt input conversion (`mypaint_brush_stroke_to`): `ascension = deg(atan2(−xtilt, ytilt))`, `declination = 90 − 60·hypot(xtilt, ytilt)` (xtilt, ytilt ∈ [−1, 1]). `attack_angle = smallest_angular_difference(ascension, stroke_direction + 90)`.

### 2.3 libmypaint smudge (quoted)

State per bucket: `SMUDGE_RGBA` (carried colour) and `PREV_COL_*` (last canvas sample) with a `recentness` counter. Per dab, if `smudge_length < 1` and smudge is on (`update_smudge_color`):

```c
float update_factor = MAX(0.01, smudge_length);
const float recentness = smudge_bucket[PREV_COL_RECENTNESS] * update_factor;
smudge_bucket[PREV_COL_RECENTNESS] = recentness;
if (recentness < MIN(1.0, powf(0.5 * update_factor, smudge_length_log) + margin)) {
    if (recentness == 0.0) update_factor = 0.0;   // first dab: take the canvas colour outright
    smudge_bucket[PREV_COL_RECENTNESS] = 1.0;
    smudge_radius = CLAMP(radius * expf(smudge_radius_log), 0.2, 1000);
    get_color(surface, px, py, smudge_radius, &r,&g,&b,&a, ...);   // mask-weighted mean
    ...
} else { r,g,b,a = previous sample }       // resample at most when "stale"
// legacy (non-spectral) update:
const float fac_old = update_factor;
const float fac_new = (1.0 - update_factor) * a;
smudge_bucket[SMUDGE_R] = fac_old * smudge_bucket[SMUDGE_R] + fac_new * r;   // g, b same
smudge_bucket[SMUDGE_A] = CLAMP((fac_old * smudge_bucket[SMUDGE_A] + fac_new), 0.0, 1.0);
```

Applying it (`apply_smudge`, legacy): `k = min(1, smudge)`, `eraser_target_alpha = clamp((1−k) + k·SMUDGE_A)`, `colour = (k·SMUDGE_RGB + (1−k)·brush_colour)/eraser_target_alpha`, and then the dab is drawn with the Normal_and_Eraser op. So a transparent carried colour *erases toward* its transparency.

On one density channel (graphite only, paper = 0) this collapses to:

```
S ← L·S + (1 − L)·mean_m(D under the dab, radius r·e^{smudge_radius_log})       L = smudge_length
D ← D + a·m·(S − D)                                                               a = opacity × smudge
```

Preset values: `classic/smudge` length 0.35, opacity 1·p, radius e^1.6 ≈ 5 px, 2 dabs/r. `deevad/blending` length 0.54, opacity 0.558·p, r e^2.95 ≈ 19 px. `deevad/grainy_blending` length 0.95, smudge_radius_log 1.45, jitter 1.62. `Dieterle/Blender` smudge 1, length 0.5, smudge_radius_log −1.6 (samples a small core), 11.56 dabs/r.

### 2.4 Krita texture option (quoted)

Mask preparation (`KisTextureMaskInfo.cpp`), per pattern pixel:

```cpp
grayValue = (red*11 + green*16 + blue*5) / 32;
maskValue = (grayValue/255.0)*alpha + (1 - alpha);
maskValue = maskValue - m_brightness;
maskValue = ((maskValue - 0.5)*m_contrast) + 0.5;   clamp 0..1;   if (m_invert) maskValue = 1 - maskValue;
// neutral point: piecewise linear, v/(2n) below n, 0.5 + (v-n)/(2-2n) above
// cutoff policy 1 (pattern): outside [cutoffLeft, cutoffRight]/255 → transparent
// cutoff policy 2 (brush):   outside → opaque
```

**Grain anchoring** (`kis_texture_option.cpp`): `x = offset.x() % maskBounds.width() − effectiveOffsetX(info)`. The pattern is indexed by canvas position modulo pattern size, so **the grain is fixed to the paper**. Offsets can be randomised per stroke. Procreate's "Texturized" grain behaves the same ("a static texture 'behind' your brush stroke"). Its "Moving" grain is fixed to the brush and drags.

Composite of texture `src` onto dab alpha `dst` (`KisMaskingBrushCompositeOp.h`), with `s = strength` (sensor-driven, e.g. by pressure):

```
MULTIPLY        (strength): dst·src·s                         soft-texturing: dst·(src ∪ (1−s))
SUBTRACT        (strength): max(0, dst − (src + (1 − s)))     soft-texturing: max(0, dst − src·s)
HEIGHT  (s' = 0.99·s):      clamp(dst/(1−s') − (src + (1−s')), 0, 1)
                     soft:  clamp(dst/(1−s') − src·s', 0, 1)
LINEAR_HEIGHT:              max(height, multiply) of the above (softer transitions)
HEIGHT_PHOTOSHOP (w = 10·s): clamp(dst·w − src, 0, 1)
LIGHTNESS / GRADIENT:       act on colour channels, not alpha
DARKEN: min-type;  BURN/DODGE/LINEAR_*/HARD_MIX: standard alpha variants
```

(`a ∪ b` = `a + b − ab`.) Docs: Height "allows to achieve full coverage with one stroke", and Height (Photoshop) at strength 0.1 ≈ Subtract at 1. "Auto Invert For Eraser" (5.3) inverts the pattern when the brush is in eraser mode (docs wording; the docs do not say which part of the grain is lifted first). That is the only texture-aware eraser found in the sources.

**Mapping to graphite:** `src` is "how much the pattern removes". With our height field (1 = peak), feed `src = 1 − h`. Then HEIGHT with `s` = pressure is the per-pixel analogue of Sousa's eq. 7: low pressure removes everything but the peaks, high pressure (s → 1) divides `dst` by `1 − s` and fills the valleys.

### 2.5 Krita Color Smudge: smearing vs dulling (quoted)

`KisColorSmudgeStrategyBase.cpp`:

```cpp
colorRateOpacity   = colorRateValue * colorRateValue * opacity;   // paint colour is added with rate²
dullingRateOpacity = 0.8 * smudgeRateValue * opacity;
smearRateOpacity   = smudgeRateValue * opacity;
```

- **Smearing:** copy the canvas from the *previous dab position* (`srcDabRect = dstDabRect.translated(lastPaintPos − newCenterPos)`) into a blend buffer with opacity `smudgeRate·opacity`, either over the current canvas or as a straight copy (Smear Alpha on). Then mix in the paint colour at `colorRate²·opacity` and blit through the dab mask. A smear is a moving copy, so texture travels with the finger.
- **Dulling:** fill the blend buffer with the *average* colour under the dab (Smudge Radius, % of brush size, ≤ 300%) at `0.8·smudgeRate·opacity`, then add colour, then blit through the mask. This is the libmypaint model.
- Docs: below 50% opacity "there is practically no smudging left". For smearing, spacing ≤ 0.05 is smooth. For dulling, lower spacing makes a stronger effect.

For graphite, a finger mostly *dulls* and *pushes down into the valleys* (Sousa). Smearing is closer to a stump dragging a dark edge along.

---

## 3. Tilt on iPad: what the sources actually say

- **Apple, UIKit** ([Computing the perpendicular force of Apple Pencil](https://developer.apple.com/documentation/uikit/computing-the-perpendicular-force-of-apple-pencil)): Pencil force "is measured along its long axis". Apple's helper is `force / sin(altitudeAngle)` for pencil touches. (Note: the normal component of an axial force would be `F·sin(alt)`. Apple *divides*, presumably to correct sensor behaviour, so treat it as an empirical normalisation, keep it behind a toggle, and clamp the altitude.) PencilKit (WWDC19 *Introducing PencilKit*): altitude and azimuth come from a second touch point and may be *estimated* when it is occluded.
- **Procreate Brush Studio** ([handbook](https://help.procreate.com/procreate/handbook/brushes/brush-studio-settings)): "the tip of the Apple Pencil does not physically touch the canvas between 0 to 15 degrees … Between 16 to 30 degrees, the response … may be inaccurate. Tilt settings are best triggered between 30 to 90 degrees." The tilt graph sets a trigger angle. The tilt targets are Opacity, **Gradation** ("a softening effect when shading with a brush on an angle. This mimics the behavior of physical pencils"), Bleed and Size. Tilt Roundness squashes the stamp. "Azimuth" rotates the stamp with the pen direction. Pro Tip: a tilt graph gives "a sharp point … upright, switching to a broader, smoother surface for shading when you tilt".
- **Sketchbook** ([help](https://help.sketchbook.com/docs/setting-stylus-tilt)): tilt scaling elongates the stamp from 100% (no change) to **400% max** ("elongated and enlarged to a maximum of 4 times").
- **Kodeco Apple Pencil tutorial** (shading code): shading starts below `tiltThreshold = π/6`. Width = `60 · normalisedAngle(azimuth vector vs stroke direction, folded to [0, π/2]) · normalisedAltitude + 5`, with `normalisedAltitude = 1 − (max(alt, 0.25) − 0.25)/(π/6 − 0.25)`. Shading opacity = `force/5`. The useful part: **the mark is widest when you stroke across the lead's lean** and narrowest when you stroke along it, and the minimum altitude is clamped at 0.25 rad.
- Grain fixed to paper vs brush: Krita (code) and Procreate "Texturized" (docs) fix it to the paper. For graphite it must be paper-fixed, or crossings won't line up with the tooth.

---

## 4. Erasers

- **libmypaint:** `eraser` ∈ [0,1] gives `color_a = 1 − eraser`, so `α ← α·(1 − a·m)` (0.5 means "pixels go towards 50% transparency"). Presets: `deevad/thin_hard_eraser` opacity 1 (pressure steps 0 → 1 at p = 0.025), hardness 0.8, r 2.8 → 10.8 px. `deevad/kneaded_eraser` opacity **0.09** × pressure curve (≈ p², reaching 1 at p = 1), hardness ≈ 1, elliptical ratio 2.32 at 178°, r 2.9 → 7.9 px, 5.24 dabs/r. A kneaded eraser in MyPaint is a weak, many-dab multiplicative lift.
- **Krita:** eraser mode with a texture, plus "Auto Invert For Eraser", gives texture-aware lifting.
- **Sousa kneaded eraser:** `lm ← lm·(1 − 0.7·ps)`, with no paper term, `ps` = interpolated tip pressure and `ci` 0.7–0.9.
- All three have the same form, `D ← D·(1 − k·m)`, and differ only in `k`, the mask, and whether the paper height enters. **A peaks-first (height-weighted) plastic eraser is our own proposal.** No source models it numerically. A kneaded eraser should *not* be height-weighted.

---

## 5. Input conditioning

- **1€ filter** (Casiez, Roussel, Vogel, CHI 2012; [page](https://gery.casiez.net/1euro/), reference JS):
  ```
  α(fc) = 1 / (1 + τ/Te),  τ = 1/(2π·fc),  Te = 1/freq   (freq from event timestamps)
  dx̂ = LPF_{α(dcutoff)}((x − x̂_prev)·freq)
  fc = mincutoff + β·|dx̂|
  x̂ = LPF_{α(fc)}(x)
  defaults: mincutoff = 1 Hz, β = 0, dcutoff = 1 Hz
  tuning: set β = 0 and lower mincutoff until slow motion stops jittering; then raise β
          (start at 0.001 or 0.0001, ×10 steps) until fast motion stops lagging
  ```
- **libmypaint slow tracking:** `fac = 1 − exp(−100·dt / slow_tracking)`, `x ← x + (x_in − x)·fac`. This is a one-pole low-pass with time constant `slow_tracking × 10 ms` (deevad 2B: 1.03 → 10.3 ms). It is disabled when ≤ 0.001. Per dab: `fac = 1 − exp(−Δdabs / slow_tracking_per_dab)` (deevad 2B: 1.5 dabs). Direction filter: `fac = 1 − exp(−step_px / (e^{0.5·direction_filter} − 1))`, default 2 → 1.72 px. Speed inputs: `log(gamma + slow_speed)·m + q`, with speed slowness 0.04 s and 0.8 s.
- **Ink Stroke Modeler** (Google, defaults in `params.h`): position modeller spring-mass constant `11/32400`, drag `72`. Kalman predictor: acceleration weight 0.5, jerk weight 0.1, min stable iterations 4. A physics alternative to 1€.
- **Interpolation:** linear per dab for x, y, pressure, altitude and time. Azimuth uses the shortest angular difference (libmypaint). Re-evaluate every mapping at every dab. Use `getCoalescedEvents()` for the full sample rate.
- **Spacing:** libmypaint pencils use 4 dabs per actual radius (spacing 0.25 r), and Krita recommends 0.05–0.10 for smudge. Spacing can follow speed (Procreate "Spacing" dynamic). If tone depends on speed, keep it intentional: Paper's Draw tool got thicker when fast (see `05-graphite-brushes.md`).

---

## Recommended recipe for our engine

**Paper.** Tileable height field `h` (1 = peak), fixed to the sheet (Krita, Procreate Texturized). Optional Uint8 burnish map lowered by hard leads: `h_eff = h − burn`, `burn += (1−p)·da·w` (Sousa eq. 16–17; the `da` values below are ours).

**Footprint.** `r = r0·(0.7 + 0.6p)`. `tilt = clamp((π/2 − alt)/(π/2 − 0.25), 0, 1)`. Stretch along the azimuth `s = 1 + 3·tilt²` (≤ 4×, Sketchbook), shift toward the lead side by `(s−1)r/2`, and use `p_eff = p/s` (pressure spread over the area; our reading of Sousa's "larger tip"). Don't combine with `force/sin(alt)` by default. Log `azimuthAngle` to fix the sign.

**Deposit, per pixel:**
```
t = 1 − reach·p_eff^γ;   c = clamp((h_eff − t)/0.18, 0, 1)
a = flow·p_eff^γ·m·c·(1 + 0.1·∂h/∂s)          // Lee eq. 5
a_dab = 1 − (1−a)^(1/n),  n = 2·dabs/r         // tone per pass; skip if stroke.js already scales by spacing
D += a_dab·(cap·(1 − hold·(1−h)) − D)          // Lee eq. 3 = libmypaint blend
```

**8-bit.** Linearising divides `a` by ≈ 8, and `+0.5` rounding then kills light marks. It also leaves the kneaded eraser a grey floor near 22/255 and stalls the smudge where `k·m·|S−D| < 0.5`. Use stochastic rounding (xorshift of x, y, dab counter) or a Float32 stroke buffer.

**Grades (ours).** Flow: deevad 4H:2B ratio 1:5.8, interpolated geometrically. Cap: Sousa's `Gp`, stretched. Radius: Sousa's lead thickness.

| | 2H | HB | 2B | 4B | 6B |
|---|---|---|---|---|---|
| r0 px | 2.6 | 2.9 | 3.1 | 3.3 | 3.5 |
| flow/pass | 0.05 | 0.12 | 0.20 | 0.30 | 0.40 |
| γ | 1.6 | 1.4 | 1.25 | 1.1 | 1.0 |
| reach | 0.45 | 0.65 | 0.78 | 0.88 | 0.95 |
| cap | 0.50 | 0.70 | 0.82 | 0.92 | 0.98 |
| hold | 0.6 | 0.4 | 0.25 | 0.12 | 0.05 |
| da | 0.6 | 0.3 | 0.15 | 0.05 | 0 |

**Smudge** (libmypaint legacy): `S ← L·S + (1−L)·mean_m(D)`, with L = 0.5–0.9. Then `D += 0.3p·m·w·(S − D)`, where `w = S > D ? 1 − 0.5h : 0.5 + 0.5h`. The height weighting is our proposal. Stump: Sousa's buffer, pick up `0.7·ps` from the paper, give back `0.5·ps·t` (t = 0.5, tortillon 0.2).

**Erasers.** Plastic: `D ← D·(1 − 0.6p·m·(0.4 + 0.6h))`; the peak-first term is our proposal. Kneaded: `D ← D·(1 − 0.7·ps)` per pass (Sousa), with no height term and a wide soft mask, i.e. per dab about `0.09p²` (deevad).

**Input.** 1€ filter on x, y: β from 0.001, dcutoff 1 Hz, freq from timestamps, mincutoff ≈ 3 Hz (τ ≈ 53 ms; 1 Hz lags ≈ 160 ms). Flush to the last raw point on pen-up. Pressure gets its own low-pass (ours; MyPaint subtle_pencil uses `custom_input_slowness` 9.23). Interpolate linearly per dab, azimuth along the shortest arc, and space dabs 0.25·r by elliptical distance.
