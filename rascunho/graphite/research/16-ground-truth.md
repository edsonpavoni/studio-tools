# 16 · Ground truth from 8bitpaint pencil (v1.5.0.0)

Measured on 2026-10-20 from the live app at https://minordaimyo.net/8bitpaintpencil/ with controlled synthetic input. We only observed its output pixels. No code was copied. All data is in `16-ground-truth/` (JSON per experiment, `png/` for crops).

## Method

**Where the pixels come from.** The app keeps its document as a WebAssembly bitmap: **10928 × 7224 px, 8 bits per pixel, a single grey channel**. Two engine calls point into the WASM heap: `GetCanvasBmpPointerEvent` returns a BMP header with a 256-entry palette, and `GetCanvasBmpPixelPointerEvent` returns the pixel pointer, length, W and H. I read the doc pixels straight from the heap after each stroke. The on-screen `#view_canvas` is only a downsampled preview.

- **The palette is a gamma curve.** The index is linear coverage; the displayed grey is `palette[idx] ≈ 255·(idx/255)^(1/2.2)`. For example, idx 128 shows as 186 and idx 30 shows as 95. Fitted gamma ≈ 2.18.
- **Cross-check.** A view pixel equals `palette[mean of the 4×4 doc idx]`, so the view averages in linear space and then applies gamma.
- **Two darkness measures are reported everywhere:**
  - **disp** = 255 − palette[idx]: displayed darkness, what the eye sees. This is the task's "255 − luminance".
  - **lin** = 255 − idx: linear coverage, the quantity the engine works in.
- **Units are document px.** At the default view (`GetViewCanvasScaleEvent` = 4, DPR 2), 1 CSS px = 2 view px = 8 doc px. The doc is centred in the view: `doc = 4·view + ((W − 4·viewW)/2, (H − 4·viewH)/2)`. The offset changes when the browser window is resized, so I recomputed it before every stroke. The task's "300 px stroke, 2 px steps, 3 px spacing" are all in doc px, which means sub-CSS-pixel event steps (0.25 CSS px).

**How input was injected.**
- I dispatched synthetic `PointerEvent`s on `#view_canvas`: pointerType `pen`, pointerId 1, isPrimary, buttons 1, `pressure`, and `altitudeAngle`/`azimuthAngle` in radians. The host reads `pageX/pageY` and prefers `altitudeAngle`/`azimuthAngle`, falling back to tiltX/tiltY.
- I wrapped `Module.ccall` only to log the `TabletEvent` arguments, not to change them. The log confirmed:
  - fractional coordinates arrive intact;
  - pressure is passed through unchanged;
  - the altitude and azimuth I set are the ones the engine receives;
  - pointerdown sends `TabletEvent(x, y, 0, alt, az)`, the moves follow, and the up path sends zero-pressure events.
- On desktop, `IPAD = IPHONE = false`. So **the host's 10-event pressure ramp and its tilt-position correction were not active**: both are iOS-only branches.
- Tools were selected through the app's own handlers (`brush_group_clicked`, `brush_clicked`, size slider). A hidden brush, index 3, was selected through the engine's `BrushSelectionEvent`.
- Defaults: 4B/HB/2H size 16 (hardness 40/40/50), Eraser and Kneaded eraser size 100, Smudge1 size 200, brush correction (smoothing) 8, paper texture on.

**Reproducibility.** The engine is **fully deterministic**: the same stroke at the same doc coordinates, after a clear, gives identical pixels across sessions. Whether the grain is a fixed doc-space paper map or noise reseeded deterministically per stroke or clear was **not isolated** (see caveats). Re-drawing the same stroke at the same doc position in a later session, with a different window size, gave identical numbers (HB p0.5: core 139.4, width 12.23; Smudge patches 112.1 / 33.6 / 254.9 / 251.4). PNG crops were extracted losslessly. The E patch PNG re-derives exactly mean 145.3 and std 42.3.

## A. Pressure ladder, HB (size 16, tilt 0, 300 px stroke)

Core = rows ≥ 50 % of peak, averaged along x 1040–1260. Width = interpolated width at 10 % of peak.

| p | disp core | disp peak | lin core | width10 (px) |
|---|---|---|---|---|
| 0.1 | 82.8 | 93.6 | 118.1 | 5.5 |
| 0.2 | 116.4 | 129.3 | 169.7 | 7.7 |
| 0.3 | 129.7 | 146.8 | 185.6 | 9.5 |
| 0.4 | 139.1 | 150.1 | 189.8 | 10.9 |
| 0.5 | 139.4 | 157.5 | 198.6 | 12.2 |
| 0.6 | 146.9 | **160** | 208.2 | 13.3 |
| 0.7 | 148.2 | 160 | 210.1 | 13.7 |
| 0.8 | 150.3 | 160 | 212.5 | 14.8 |
| 0.9 | 150.7 | 160 | 213.0 | 15.7 |
| 1.0 | 154.9 | 160 | 218.4 | 15.8 |

## B. 4B and 2H ladders

| p | 4B disp core | 4B width | 2H disp core | 2H width |
|---|---|---|---|---|
| 0.1 | 110.4 | 5.4 | 6.2 | 3.8 |
| 0.2 | 177.6 | 7.5 | 23.2 | 5.3 |
| 0.3 | 203.0 | 9.4 | 41.3 | 6.7 |
| 0.4 | 218.8 | 10.7 | 47.9 | 8.5 |
| 0.5 | 219.5 | 12.0 | 53.5 | 10.0 |
| 0.6 | 232.2 | 13.1 | 55.4 | 11.6 |
| 0.7 | 234.5 | 13.7 | 56.2 | 12.8 |
| 0.8 | 238.3 | 14.8 | 58.9 | 13.7 |
| 0.9 | 239.0 | 15.7 | 60.1 | 15.6 |
| 1.0 | 246.1 | 15.8 | 61.1 | 15.8 |

**Fitted curves:**

- **Each grade has a hard per-pixel darkness cap.** No pixel ever goes darker than it:

  | Grade | Cap (idx) | Cap (lin) | Cap (disp) |
  |---|---|---|---|
  | 4B | 0 | 255 (pure black) | 255 |
  | HB | 30 | 225 | 160 |
  | 2H | 137 | 118 | 63 |

  The core profile is flat-topped at the cap from p ≈ 0.6 upward.
- **Width vs pressure follows a square root**, so stroke area is proportional to pressure:
  - HB: `w = 16.4·p^0.47` (R² 0.993);
  - 4B: `w = 16.4·p^0.48` (R² 0.995);
  - 2H: `w = 15.9·p^0.66` (R² 0.993).
  
  At p = 1 the width ≈ size (15.8 for size 16).
- **Darkness vs pressure saturates.** Core coverage as a fraction of the cap, f = lin core / lin cap, fits `f = 0.93·(1 − e^(−p/0.13))` for HB and 4B (R² 0.96). The best power law is much worse: `f ≈ p^0.23` (R² 0.89). 2H is softer, with a low-pressure toe: `f = 1 − e^(−p/0.32)` (R² 0.93). Below p 0.6 the darkness deficit is made of texture holes, not lighter grey: along-stroke std in the core goes 56 → 12 for HB.
- **Profile shape.** It is a flat plateau with ~2 px soft shoulders. There is no Gaussian falloff.

## C. Tilt (HB p0.5, stroke along +y, azimuth 0 = lead toward +x)

| altitude | disp core | width10 | centroid offset (px, + = toward lead) |
|---|---|---|---|
| 90° | 140.1 | 12.2 | +0.2 |
| 60° | 147.2 | 13.6 | +0.2 |
| 45° | 144.4 | 13.7 | +0.1 |
| 35° | 146.3 | 13.8 | +0.05 |
| 30° | 144.0 | 14.8 | +0.5 |
| 25° | 135.2 | 25.9 | +4.2 |
| 20° | 130.9 | 44.0 | +11.3 |
| 15° | 129.9 | ≥ 69 (clipped by window) | ≥ +22.6 |
| 10° | 140.9 | ≥ 68 (clipped) | ≥ +26.4 |
| 20°, azimuth 180° | 131.2 | 43.8 | −10.9 (mirrored) |

- **Tilt is a threshold behaviour.** From 90° down to ~30° the mark barely changes (width +20 %).
- **Below ~28° a shading mode appears.** It has a sharp edge on the side away from the lead, about one normal radius (−9 to −11 px) from the axis. A long one-sided ramp extends toward the lead, and its darkness decays roughly linearly: at 20° it goes 150 → 85 over ~35 px, then drops off.
- Core darkness drops only ~7 %. The side the shading extends to flips exactly with azimuth.

## D. Build-up (same stroke drawn n times)

| passes | HB disp core | HB lin core | HB width | HB along-std | 4B disp core |
|---|---|---|---|---|---|
| 1 | 138.4 | 189.5 | 10.9 | 45.2 | 220.4 |
| 2 | 141.5 | 200.8 | 11.4 | 39.5 | 224.8 |
| 4 | 140.2 | 198.2 | 11.7 | 35.8 | 224.9 |
| 8 | 142.5 | 201.2 | 11.7 | 32.6 | 229.8 |

Overdraw barely darkens: +3 % after 8 passes. Each pass seems to raise a pixel only toward that grade's pressure-dependent target, never past the cap; this is a max- or target-style blend, not additive. Repeats mainly fill texture holes (std falls) and add ~0.8 px of width.

## E. Texture (HB, 60×60 patch of 20 strokes 3 px apart)

| p | mean disp | std disp | mean lin | std lin | pixels at cap |
|---|---|---|---|---|---|
| 0.3 | 145.3 | **42.3** | 205.9 | 56.3 | 88 % |
| 0.6 | 160.0 | 0 | 225 | 0 | 100 % |
| 1.0 | 160.0 | 0 | 225 | 0 | 100 % |

- The paper breaks the mark only at low pressure.
- At p 0.3, 88 % of pixels sit exactly at the HB cap. The rest are speckle holes of 1–2 px, mostly near-white, with a few mid-greys (`png/E_HB_p0.3_patch.png`).
- From p 0.6, an overlapped patch becomes a perfectly flat cap with zero texture.
- The texture is pixel-scale white noise, with no visible tooth pattern at this zoom. The same noise reappears for the same stroke at the same doc coordinates. Whether that is a fixed paper map was not isolated.

## F. Erasers (4B p0.8 patch, saturated disp 255; one horizontal erase stroke)

| tool | size | p | width cleared (px) | remaining at centre (disp) | pixels fully white in band |
|---|---|---|---|---|---|
| Eraser | 100 | 0.3 | 30 | 0 | 100 % |
| Eraser | 100 | 0.6 | 60 | 0 | 100 % |
| Eraser | 100 | 1.0 | 100 | 0 | 100 % |
| Eraser | 16 | 0.6 | 10 | 0 | — |
| Kneaded | 100 | 0.3 | 49 | 63 (min 29) | 72 % |
| Kneaded | 100 | 0.6 | 50 | 12 (min 2) | 91 % |
| Kneaded | 100 | 1.0 | 50 | 0 | 100 % |
| Kneaded | 16 | 0.6 | 8 | 0 | — |

- **Eraser** is a hard binary cut back to paper white. There is no residue and no soft edge. Its width = size × pressure.
- **Kneaded eraser:**
  - its width is fixed at ≈ size / 2, independent of pressure;
  - the share of pixels lifted depends on **pressure and size**. At size 100: 75 % of the graphite at p 0.3, 95 % at 0.6, 100 % at 1.0 in one pass. At size 16, p 0.6 already cleans fully;
  - the lift is per-pixel and close to binary, so pixels go fully white or stay. That gives a speckled, grainy result (`png/F_Kneaded_*.png`), not a uniform lightening;
  - edges are hard.

## G. Smudge (4B p0.8 60×60 patch, stroke from patch centre 180 px to +x)

| tool | size | p | patch mean after (was 255) | fade to 50 % beyond edge | fade to 10 % | dragged darkness just outside → at +150 px |
|---|---|---|---|---|---|---|
| Smudge1 | 200 | 0.5 | 112.1 | 20 px | 81 px | ~20 → ~5 |
| Smudge1 | 200 | 1.0 | 33.6 | 122 px | > 220 px | ~20 → ~11 |
| Smudge1 | 40 | 0.5 | 254.9 | 14 px | 30 px | 244 at edge → ~2 |
| Smudge1 | 40 | 1.0 | 251.4 | 15 px | 49 px | 247 → ~3 |
| Smudge2 (hidden, brush 3) | 40 | 1.0 | 255 | no fade | no fade | solid 255 to stroke end |

- **Smudge1 (menu) at its default size of 200** strips most of the patch and spreads it as a faint veil: disp ~15–20, about ±85 px perpendicular and > 200 px along. So the patch lightens strongly: 255 → 112 at p 0.5, → 34 at p 1.0.
- **At size 40** the patch keeps its overall darkness, but the stroke path inside it lightens (a "bite"). Graphite is dragged with a quick exponential-like fall: half in ~15 px, 10 % in 30–50 px, then a very long faint tail of 2–3 in disp.
- The dragged band is ~70 px wide, wider than the 40 px brush, with darkness ~20–30.
- **Smudge2 exists in settings but is not in the menu.** It copies full black along the whole stroke with no decay, acting like a solid drag/clone. It is probably unfinished; treat it as a curiosity.

## H. Event spacing (HB p0.5, size 16)

| step (px) | events | disp core | width10 | along-stroke std | gaps |
|---|---|---|---|---|---|
| 1 | 325 | 141.2 | 12.17 | 8.7 | 0 |
| 2 | 165 | 142.5 | 12.11 | 7.9 | 0 |
| 4 | 85 | 140.3 | 12.18 | 7.7 | 0 |
| 16 | 25 | 141.5 | 12.16 | 8.7 | 0 |
| 40 | 13 | 141.1 | 11.79 | 11.6 | 0 |
| 80 | 9 | 132.7 | 10.63 | 18.0 | 0 |

- The engine interpolates between events. The stroke is continuous at every spacing tried.
- Darkness and width are spacing-independent up to 16 px.
- At 40–80 px steps the mark gets slightly thinner and lighter and more uneven along its length. This is consistent with the brush-correction smoothing cutting corners on sparse input.
- `TabletEvent` carries no timestamp, so "speed" can only mean event spacing here.

## Size → width (HB p0.5)

| size | width10 | width / size | disp core |
|---|---|---|---|
| 2 | 1.8 | 0.90 | 64.9 (sub-pixel, lighter) |
| 4 | 3.3 | 0.83 | 158 peak |
| 16 (default) | 12.3 | 0.77 | 140.8 |
| 40 | 29.2 | 0.73 | 135.6 |
| 100 | 72.3 | 0.72 | 133.7 |

Width ≈ size·√p, and √0.5 = 0.71. Darkness is size-independent above ~4 px.

## Model in one paragraph (for the fit)

- **Grade.** Each grade is a per-pixel cap in linear coverage: 4B 255, HB 225, 2H 118.
- **Pressure** sets two things:
  1. footprint width ≈ size·√p (2H: p^0.66);
  2. the probability that a covered pixel reaches the cap, about `0.93·(1 − e^(−p/0.13))`; the rest are holes from a deterministic white-noise paper grain (fixed map vs reseeded noise not isolated).
- **Profile.** It is flat-topped with ~2 px shoulders.
- **Overdraw** is near-idempotent (max-style).
- **Tilt** is ignored above ~30°. Below that it switches to a one-sided shading ramp toward the lead.
- **Eraser** is a binary disc of size·p. **Kneaded eraser** is a size/2 disc that lifts a pressure- and size-dependent fraction of pixels completely (smaller sizes lift more).
- **Smudge** is a reservoir drag with ~15 px half-distance (size 40) plus a wide faint veil.
- **Display** is gamma 2.2 over linear coverage.

## Files

- `16-ground-truth/A_B_pressure_ladder.json`: all three grades, the full perpendicular profiles (disp and lin), and stats.
- `16-ground-truth/C_tilt.json`, `D_buildup.json`, `E_texture.json`, `F_erasers.json`, `G_smudge.json`, `H_spacing.json`, `size_width.json`.
- `16-ground-truth/png/`: 8-bit grey crops at doc resolution:
  - pressure ladders for HB, 4B and 2H;
  - the tilt row;
  - the E patch;
  - Eraser and Kneaded results;
  - Smudge1 at sizes 200 (half-res) and 40, and Smudge2.
- `png/E_HB_p0.6_patch60_uniform.png` and `png/E_HB_p1.0_patch60_uniform.png` are **reconstructed**, not captured. Those patches measured std 0, every pixel at idx 30 (grey 95), so they are flat 60×60 grey-95 images.
- **Session note.** The first browser tab disappeared mid-run. G, H and all PNGs were regenerated in a second tab. G reproduced the first run's patch means exactly. H's first-run numbers were within 0.1 of the second run for steps 1–40 (e.g. 141.2/12.17 vs 141.2/12.17 at step 1), but the saved H file is from the second run.

## Confidence / caveats

- **Synthetic events, not a real Apple Pencil.**
  - Pressure was held exactly constant.
  - Real strokes have pressure noise, start and end ramps, and speed. The engine sees no time at all.
  - On iPad the host additionally applies a 10-event pressure ramp at stroke start and a tilt-based position correction. **Neither was active here** (desktop path). Real iPad strokes will have lighter, thinner starts over the first ~10 events.
  - The trimmed core measurements (x 1040–1260 of 1000–1300) exclude start and end caps.
- **Smoothing.** Brush correction was left at its default of 8. It smooths positions and is likely why sparse events (40–80 px) thin the mark. It does not affect dense input.
- **Paper texture.** Default texture on. Output is deterministic: the same stroke at the same coordinates gives identical pixels. Two readings fit that result: (a) a fixed doc-space grain map, or (b) noise reseeded deterministically per stroke or clear. D argues somewhat against a strict (a) plus max blend, because a repeat pass still filled holes (along-stroke std 45 → 33). **First follow-up test:** draw two overlapping strokes with different start points and compare their hole maps. The std values describe this particular noise field. Another texture choice in "Paper texture…" was not tested.
- **"Darkness" scale.** Tables use displayed darkness (gamma-encoded), as asked. For a physically based engine, fit the **lin** columns: coverage in linear light, from the JSON.
- **Units.** Engine/document pixels. Rendering at a different doc zoom does not change engine output (verified across two window sizes).
- **Scope.**
  - Hardness was left at default.
  - Tilt was tested only with HB.
  - The tilt widths at 15° and 10° are lower bounds because the measurement window clipped them.
  - Smudge2 is an unlisted brush and may not be meant for use.
- **Side effects.** The app's saved settings (localStorage) were restored to their original values and the canvas was cleared before closing the tab.
