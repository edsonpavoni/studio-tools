# MATERIAL — Qimoo FR4, 1.6 mm, 35 µm copper (single-sided) — on the B6 MOPA

**The measurement log for THIS material on THIS machine.** Every number here was cut
and scored on the bench; append new results with the date, never overwrite — a
superseded number stays as history with a strikethrough or a note. The *procedure*
for making a board lives in `B6-PCB-RECIPE.md`; this file is what the material does.

⚠️ Different regime from `projects/B6 Mopa Laser/material-settings.md`, which is
**1.1 mm solid copper sheet** (75 kHz, wobble 0.30 — Witness lids). Do not mix them.

Identity: Qimoo brand FR4-laminate, 1.6 mm substrate, 1 oz (35 µm) copper one side.
All results with **air assist ON** and the **board lifted off the bed** unless noted.
Machine: ComMarker B6 MOPA, LightBurn Pro 2.1.04, all layers 200 ns / min power 20 %.

---

## Proven settings (the recipe, as measured)

| Operation | Power | Speed | Freq | Passes | Wobble | Notes |
|---|--:|--:|--:|--:|---|---|
| **Hole (ring-cut)** | **70 %** | 400 mm/s | 40 kHz | **8** | 0.10 / 0.02 | finished Ø = drawn + **0.24 mm** → draw target − 0.24. Interleave holes checkerboard so neighbours cool. |
| **Copper clear (raster)** | 75 % | 1500 mm/s | 40 kHz | 4 | off | interval **0.05 mm**, hatch +13°/pass. Meter-verified full clear. |
| **Board cutout** | 100 % | 400 mm/s | 40 kHz | **6** | 0.30 / 0.04 | releases on pass **6 exactly** (measured 2026-08-24, earlier squares 5–6) — zero spare, ATTEND IT. |
| **Labels / text** | 20 % | 1000 mm/s | 40 kHz | 1 | off | interval 0.05. Never share a layer with holes. |

## Capability floors (proven, not guessed)

| Quantity | Value | Evidence |
|---|--:|---|
| Trace width, proven | **0.30 mm drawn** (0.40 finished after 2×0.05 pullback) | V3 board 2026-08-23, incl. 7.4 mm run, meter-verified |
| Trace width, candidate | 0.20 mm | width coupon UNRUN (`coupon/B6-WIDTH-COUPON.lbrn2`) |
| Net-to-net isolation floor | **0.171 mm** | 2025 TRIBE board (this laser, same class of stock); V4 designed at ≥0.20 |
| Hole wobble kerf @ 70 %/8 | **+0.24 mm** on drawn Ø | HOLES-5, pin-gauged at Ø1.0; holds at Ø1.7–1.8 (MOUNT coupon) |
| Board size proven | 60 × 40 mm | V3 + V4. 100 mm edges untested. |

## What this material DOESN'T do (recorded failures — read before "improving" anything)

- **Power above ~70 % makes holes SMALLER and dirtier, not bigger.** 85 % and 100 %
  failed the pin gauge that 70 % passed, identical geometry: surplus energy melts and
  chars the exit closed instead of ablating wider. (HOLES-4, 2026-08-24.)
- **16 hole passes = oversize + burned halo** eating the pad annulus; even 8 passes
  penetrates. Risk is asymmetric: not-through can be re-run, oversize is forever.
  (V3 2026-08-23, HOLES-2 2026-08-24.)
- **No-wobble TRIBE-style holes (40 mm/s, 37 kHz, drawn at nominal) lost to wobble on
  this stock** — the 2025 reference recipe did not reproduce its own ring quality
  here. (HOLES-3, 2026-08-24.)
- **200 mm/s scanning chars black at any pass count**; everything good happens at
  400+ (cutting) / 1500 (clearing). Slow = melt-and-resolidify, not ablation.
- **0.1 mm scan interval is too coarse** for clearing fine moats; 0.05 is the number.
- **Cutout passes after release gouge the board** — the freed board drops and the
  beam keeps firing. 6 passes + attendance, always. (V3's edge, 2026-08-23.)
- Fill cells that LOOK cleared can still read short — **the meter, not the eye.**

## Open questions on this material

- Cutout edge char ("border burn", Edson 2026-08-24) — candidate: 85 % cutout
  (`make_mount_coupon.py` S85 square, cut but not yet scored against S100).
- 0.20 mm traces — width coupon unrun.
- Long perimeters (100 mm class) — untested.
- Scuffed-matte vs bright copper surface prep — never isolated on this stock.

## Result log (append here, newest first)

- **2026-08-24** — HOLES-2→5 + MOUNT coupon ladder: hole cell dialed (70 %/8/kerf
  0.24), pass count floor 8, power ceiling finding, kerf holds at Ø1.7–1.8, cutout
  release pass 6 confirmed. **V4 cut: first fully working board on this material.**
- **2026-08-23** — V3 first article: 0.3 mm traces proven, fill recipe vindicated,
  16-pass holes oversize, cutout gouge. Two converter bugs caught in LightBurn.
- **2026-08-18–22** — six coupon runs established fill 75 %/1500/4×/0.05, interleaved
  holes, wobble halves hole passes, 400 mm/s clean-exit finding, labels on feather
  layer. (`COUPON-RUN-2026-08-18.md`.)
- **2026-08-18 run 1** — burned through on fills, holes not through: air assist OFF,
  hatch not rotating, wrong stock. The run that taught "identify the material first."
