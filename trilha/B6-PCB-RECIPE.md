# B6 MOPA — PCB recipe

## ✅ HOLES DIALED IN — coupon ladder HOLES-2→5, all run 2026-08-24

**The hole recipe is now: 70 % power, 8 passes, 400 mm/s, 40 kHz, 200 ns, wobble
0.10/0.02, drawn diameter = target − 0.24.** Verified by pin fit: drawn 0.76 seats a
2.54 header pin at a 1.00 target with a TRIBE-class ring. Defaults updated in
`lbrn.py` and `circuit2lbrn.py` (--hole-kerf 0.24) the same day.

The finding that unlocked it: **above ~70 % power a hole finishes SMALLER and
dirtier** — surplus energy melts/chars the exit closed instead of ablating wider
(85 % and 100 % both failed the pin that 70 % passed, at identical geometry). Power
is not a widening lever on this stock; diameter is drawn for the kerf and energy is
kept at the minimum that penetrates.

Ladder for the record: HOLES-2 (8/10/12 passes all through at 0.85/1.00 — pass count
settled, everything oversize) → HOLES-3 (wobble beats the TRIBE no-wobble recipe;
0.55 no-fit / 0.70 fits-but-burnt) → HOLES-4 (power ladder; only 70 %/0.65 passed,
too tight) → HOLES-5 (0.68/0.72/0.76 at 70 % — **0.76 wins**).

Still open: does kerf 0.24 hold at Ø 2.0 mounts (`B6-MOUNT-COUPON.lbrn2`, drawn
1.70/1.76/1.82 + two cutout squares: S100 release-pass confirm, S85 char experiment).

## 🔴 HOLES-2 RUN 2026-08-24 — pass count settled, DIAMETER STILL OPEN *(superseded same day, above)*

All six HOLES-2 cells went through, **including 8 passes** — so 12 is no longer the
number, 8 is (and 6 is being tested). But every cell finished **oversize vs TRIBE
with a too-thin 1.5 mm pad ring**, so `--hole-kerf 0.15` is NOT the answer either.
Open question: is the true wobble kerf ~0.3+, or is wobble simply the wrong hole
strategy? (TRIBE ran **no wobble, 40 mm/s, 37 kHz, drawn at nominal, zero
compensation** and its holes are the reference.) `coupon/B6-HOLES3-COUPON.lbrn2`
(`make_holes3.py`) settles it: wobble cells drawn 0.55/0.70 at 8/6 passes vs
TRIBE-recipe control cells at 0.90/1.00, all with 1.8 mm pads.
**Do not cut V4's holes until HOLES-3 is scored.** Pad annulus likely also needs a
board-side fix (`--pad-grow`, unbuilt) — footprint pads are thin around a 1.0+ hole.

## 🔴 FIRST REAL BOARD — V3, 2026-08-23 — what the first article changed

The full V3 board (60x40, 56 holes, 72% cleared, hand-routed) was cut on 2026-08-23.
The fill recipe and the 0.3 mm traces were vindicated; holes and cutout were both
proven OVERKILL, which no coupon could show because coupons only asked "does it go
through?", never "what is the least that does?"

**What the board proved:**

- ✅ **0.3 mm drawn traces WORK** (0.40 finished after 2x0.05 pullback). All three read
  continuous, including a 7.4 mm run. 0.3 is now a standard width, not a gamble.
- ✅ Fill at 75% / 1500 / 4x / 0.05 int: clean full-board clear, meter-verified.
- ✅ Components mount: headers, IRLZ44N, 330 uF cap, bent-leg resistors all fit.

**What it corrected (defaults already changed in lbrn.py / circuit2lbrn.py):**

- 🔻 **HOLES 16 -> 12 passes.** 16 went through but finished oversize with a burned
  halo eating the pad annulus (side-by-side with TRIBE it is obvious). Risk is
  asymmetric: not-through can be re-run, oversize is forever.
- 🔻 **CUTOUT 8 -> 6 passes, and STAND AT THE MACHINE.** The board released on pass
  5-6 exactly as measured, fell to the machine floor, and the remaining passes fired
  into the loose board and gouged it. Margin after release is damage, not margin.
- 🔻 **--hole-kerf now defaults 0.15** (was 0). Wobble + kerf finishes holes well over
  drawn size. 0.15 is the interim compensation; `coupon/B6-HOLES2-COUPON.lbrn2`
  (8/10/12 passes x 0.85/1.00 drawn, with pad rings) measures the real number —
  run it before the next board and fill in `coupon/SCORE-HOLES2.md`.

**Also found the same day, before cutting:** the marching-squares stitcher had a
float-hashing bug that silently dropped 94 of 147 fill loops — LightBurn showed pads
with no boundary around them. Fixed with exact integer keys, and the converter now
rebuilds the even-odd fill from the polygons it is about to write and refuses to
build on any structural mismatch. Two saves in one day came from EYES ON THE FILE
IN LIGHTBURN before pressing start. Keep doing that.

## Preflight, in order — amended after V3

1. **Dimensions have sources.** Every footprint number is in the project's `PARTS.md`
   with provenance (datasheet / caliper / verified-on-board). A typed number is how
   V3 got a 10 mm XIAO that is really 15.24 mm.
2. **Cardboard fit test on any new or changed layout:** `circuit2lbrn.py --fit-test`
   → holes + outline + labels on cardboard, push the real parts through. 2 minutes.
3. Eyes on the file in LightBurn: layer table matches the recipe, every pad has a
   boundary around it, CLEAR interval 0.05.
4. Board off the bed, air ON, frame.
5. **Stay for the CUTOUT.** It releases on pass 5–6 and the board falls.

## ✅ THE RECIPE, measured 2026-08-18, amended 2026-08-23

Every number below was established on the bench, on **Qimoo FR4, 1.6 mm, 35 µm copper**,
with **air assist ON** and the **board lifted off the bed**. Each one has a recorded
failure for the alternatives; see `COUPON-RUN-2026-08-18.md` for the six runs that got here.

| Layer | Mode | Power | Speed | Passes | Wobble | Other |
|---|---|--:|--:|--:|---|---|
| **HOLES** | Cut | **70 %** *(dialed 2026-08-24; ≥85 % chars holes smaller)* | 400 mm/s | **8** | 0.10 / 0.02 | interleaved over two layers; draw holes **0.24** under target |
| **CLEAR** | Scan | 75 % | 1500 mm/s | 4 | off | 0.05 mm, hatch +13°/pass |
| **CUTOUT** | Cut | 100 % | 400 mm/s | **6** *(8 gouged the fallen board, V3)* | 0.30 / 0.04 | releases pass 5–6 — ATTEND IT |
| **LABELS** | Scan | 20 % | 1000 mm/s | 1 | off | 0.05 mm |

All at **40 kHz, 200 ns, min power 20 %**.

### The four things that actually mattered

1. **Speed, not passes.** 200 mm/s chars black at any pass count. Everything good happens
   at 400 and above. On the cutout, 400 mm/s needed *fewer* passes than 40 mm/s as well as
   being ten times quicker per pass: slow enough and the material melts and re-solidifies
   instead of ablating.
2. **Wobble.** Halves the passes on holes and is what makes the cutout work at all. The
   beam traces a small circle as it advances, so energy smears along a wider kerf instead
   of being dumped into a stationary point.
3. **The meter, not the eye.** Half the fill cells that looked cleared read short. Copper
   that has merely darkened looks exactly like copper that has gone.
4. **Heat is cumulative and it invalidates tests.** Hence interleaved holes, one file per
   test with cooling between, and text on its own feather-light layer.

### Known unknowns

- **Wobble kerf.** Confirmed real on V3 (oversize holes + halo). `--hole-kerf` now
  defaults to 0.15 as interim compensation; HOLES-2 coupon measures the exact number.
- **The taper.** Edson's wide-to-narrow wobble technique never ran; every test square fell
  during the first stage. Untested, not disproven. Likely relevant on thicker stock.
- **Long perimeters.** The cutout was proven on 10–30 mm squares. A 100 mm board edge has
  not been cut yet.

---

**Recovered 2026-08-17 by reading the files, not from memory.** Source: `2025 O.K./B6/ToR_008.lbrn2` (24 May 2025, the eighth and last iteration of the TRIBE / Touch of Red board) cross-checked against `2025 O.K./PCBs/pcb2gcode/ToR_008/drill.drl`.

A copy of both is frozen in `reference/`. **Do not edit those two files.** They are the only surviving record of a board that actually worked.

---

## The material this recipe is for

**35 µm copper foil on FR4** (standard 1 oz single-sided clad) — specifically Qimoo
1.6 mm. **The running measurement log for this material is `MATERIAL-QIMOO-FR4.md`**
(proven settings, capability floors, recorded failures — append new bench results
there). This is a different regime from the copper recipes in
`projects/B6 Mopa Laser/material-settings.md`, which are for **1.1 mm copper sheet**. Do not mix them.

| | copper foil on FR4 (this page) | 1.1 mm copper sheet (material-settings.md) |
|---|---|---|
| Job | ablate 35 µm off a substrate | cut through 1.1 mm |
| Frequency | **37 kHz** | 75 kHz |
| Speed | 200 mm/s scan, 40 mm/s cut | 400 mm/s |
| Wobble | **off** | on, step 0.030 size 0.300 |
| Proven on | the TRIBE board, May 2025 | Witness lids, May 2026 |

---

## The five layers, in the order they run

Priority is the run order. LightBurn runs priority 0 first. **This order came off a board that worked. Do not reorder it without a coupon test.**

| Pri | Layer | Mode | Power | Speed | Freq | Passes | What it does |
|:--:|---|---|--:|--:|--:|--:|---|
| **0** | **C02** | Cut | 100 % | 40 mm/s | 37 kHz | **8** | **Holes.** All 59 of them, every diameter, ring-cut as circles. Runs FIRST, while the board is still flat and registered. |
| **1** | **C01** | Scan | 95 % | 200 mm/s | 37 kHz | 1 | **Copper clearing, pass 1.** Raster fill of the isolation regions. Also carries the two Text objects (the TRIBE mark and the credit line). |
| **2** | **C03** | Scan | 95 % | 200 mm/s | 37 kHz | 1 | **Copper clearing, pass 2.** Second fill region set. |
| **3** | **C07** | Cut | 95 % | 200 mm/s | 37 kHz | 1 | **Isolation outline.** Vector pass around the trace edges, cleaning up what the raster left ragged. |
| **4** | **C08** | Cut | 100 % | 40 mm/s | 37 kHz | **12** | **Board cutout.** One closed path around the perimeter. Runs LAST, because after this the board is loose. |

Min power (`maxPower2`) is **20 %** on every layer.

### 📌 Q-Pulse Width is very likely 200 ns

**Deduced 2026-08-18, and worth acting on.** When the generated coupon was opened in
LightBurn Pro 2.1.04, the HOLES layer, for which this tool writes no `QPulseWidth` at
all, displayed **Q-Pulse 200 ns** and **Interval 0.1000 mm**. Those are the device
profile's defaults.

`ToR_008.lbrn2` also omits `QPulseWidth`. So the 2025 board almost certainly ran at
whatever the profile default was, and the profile default today is 200 ns.

This is inference, not proof: the profile could have been edited in the fifteen months
since. But it makes **200 ns the front-runner** rather than one of three equal guesses,
and the coupon still settles it properly by testing all three.

Same reasoning puts the missing **Line Interval at 0.1 mm**, not the 0.02 mm borrowed
from the copper-sheet engrave recipe. ⚠️ **0.1 mm is coarse for clearing a 0.10 mm
moat**, which is one more reason to read the coupon's fine end carefully.

### ⚠️ Two parameters are NOT in the file

`ToR_008.lbrn2` records no **Q-Pulse Width** and no **Line Interval**. In May 2025 both came from the device defaults, so they were never written down. They are **UNKNOWN** and must be recovered by coupon test, not guessed.

This matters more than it sounds. The 2026 copper page says plainly: *"Short pulse widths do NOT work on copper. Tested 6 ns, marked nothing."* Pulse width is the single parameter that decides whether 1064 nm couples into copper at all. Starting the coupon sweep at **200, 350 and 500 ns** is the sensible bracket, because those are the three that worked on copper sheet.

Line interval for the raster fill is likewise unknown. The copper-sheet engrave recipe used **0.020 mm**; that is a reasonable first guess and nothing more.

---

## Hole geometry, and how drill sizes were mapped

**Verified 2026-08-17.** Every hole in the drill file has exactly one circle on the laser hole layer. Perfect one-to-one, all six tools, all 59 holes:

| Drill tool | Ø | holes in `.drl` | circle size in `.lbrn2` | ÷ 39.3701 |
|---|--:|--:|--:|--:|
| T1 | 0.600 mm | 3 | 23.622 | **0.600 mm** |
| T2 | 0.900 mm | 38 | 35.4331 | **0.900 mm** |
| T3 | 1.000 mm | 14 | 39.3701 | **1.000 mm** |
| T4 | 1.300 mm | 2 | 51.1811 | **1.300 mm** |
| T5 | 2.400 mm | 1 | 94.4882 | **2.400 mm** |
| T6 | 6.600 mm | 1 | 259.843 | **6.600 mm** |

Three things this proves:

1. **No kerf compensation was applied.** The circle matches the nominal drill diameter exactly. Whatever the laser kerf did to the finished hole, it was accepted rather than corrected.
2. **Every hole is ring-cut, not point-drilled**, including the 0.600 mm ones, and all six diameters share one layer and one recipe. There is no separate small-hole strategy.
3. **The 6.6 mm mounting hole runs the same 8 passes as a 0.6 mm via.** That is why 8 passes and not fewer.

✅ **The radius-versus-diameter question is settled, and it is not a trap.** The attribute is named `Rx` and it *is* a radius, but the shape also carries its own XForm scale. In the reference file `Rx=23.622` with an XForm scale of `0.0127` resolves to **0.300 mm radius, i.e. a 0.600 mm hole**, which matches drill tool T1C0.600 exactly. Verified 2026-08-17 by reading the transform rather than the attribute alone. `gerber2lbrn.py` writes an identity transform and puts the radius straight in millimetres, which is equivalent and easier to check.

---

## What geometry the 2025 board actually used

**Measured 2026-08-17** from `TopCopper.gbr` and pcb2gcode's original-copper SVG, not from the photograph.

| | value | how it was obtained |
|---|--:|---|
| Trace width | **0.508 mm** (20 mil) | the only stroked aperture in the Gerber, `%ADD15C,0.508` |
| Typical copper-to-copper gap | **0.542 mm** | nearest-neighbour distance between copper boundary loops |
| **Tightest gap on the board** | **0.171 mm** | 3 of 40 loops |
| Nothing below | 0.15 mm | |

**The 0.171 mm figure is the important one: the laser cleared it and the board worked.** That is a proven process capability, not an estimate, and it is much finer than the 0.30 mm I would have guessed. It is why the coupon's moat ladder starts at 0.10 mm.

Note also that 0.508 mm traces with 0.542 mm gaps is close to a 20/20 mil design rule, which is a conservative fab-house rule from the 1990s. The board was drawn conservatively and the laser was never pushed.

---

## The pipeline that produced this file

1. **Design** in Flux.ai (project `touchofred-5a3a`), exported as a standard Gerber set: `TopCopper.gbr`, `edge_cuts.gbr`, `drill.drl`, plus mask/silk/paste that go unused here.
2. **`pcb2gcode`** turned the copper layer into isolation geometry. Its outputs are still on disk: `traced_front.svg`, `processed_front_final.svg`, `front.ngc`, `drill.ngc`.
3. **LightBurn** imported the SVG, the five layers above were assigned by hand, and the job ran on the B6.

`pcb2gcode` and `gerbv` are both installed on this machine (`/opt/homebrew/bin`). The heavy lifting is already solved; nothing here needs a Gerber parser written from scratch.

---

## What is still unknown

- Q-Pulse Width — **unknown**, bracket 200 / 350 / 500 ns. The coupon compares all three on identical geometry.
- Line Interval for the two Scan layers — **unknown**, start at 0.020 mm
- Air assist state — not recorded, assume on
- Focus height and whether any pass ran at a Z offset — not recorded
- Whether the copper was scuffed matte before the run. The 2026 notes call this out as a large effect on copper coupling, and the finished board's dark field suggests the substrate, not oxide. **Unknown.**
- The exact `pcb2gcode` invocation and its isolation width. Only the outputs survive, not the command.

*(2026-08-24 note: every unknown above was answered by the coupon runs of Aug 18–24;
the answers live at the top of this file. The generators are in `archive/`, their
outputs and score sheets in `coupon/`. This section stays as the record of what was
unknown when the 2025 files were recovered.)*
