# 05 · Focus and the Z axis — research for Raio

**Date:** 2026-10-21 · **Machine:** ComMarker B6 MOPA 60 W (JPT M7), galvo head, F-theta f = 210 mm, 150 × 150 mm field, BJJCZ LMC board, electric lifting column.
**Brief from Edson:** *"VERY IMPORTANT: focus is the most important thing on the laser work. And we have suffered in the past because LightBurn does not have a way to automatically move the Z axis as a work is being made. This tool should fix that."*

Tags: **VERIFIED** = read in a studio file, the B6 manual on disk, or the installed binary · **WEB** = online source, linked · **INFERRED** = my reading of the evidence · **COMPUTED** = calculated here, with the assumptions given.

---

## 0 · The answer on one page

1. **How the B6 column is driven today (VERIFIED, B6 manual on disk).** A stepper and an 8 mm lead screw at 200 pulses per revolution. That gives **0.04 mm per pulse**, at 12.5 mm/s. The column is run by the **head's own touch panel / control board**, not by the PC. Its autofocus uses an **"inner sensor"**: a non-contact rangefinder that is off-centre (it sits under the red dot) and works only from **120 to 280 mm**. The panel stores a target "Focal length" and shows the live "Real focal length". The studio's reading of the latter is **255.15**.
2. **Software control through the LMC board is possible but unproven for the B6.** Evidence for and against is in §3.2. The protocol already has the primitive: `MoveAxisTo` (0x0029), `GetAxisPos` (0x002A), `AxisGoOrigin` (0x0028), `SetAxisMotionParam` (0x0026), plus the AXIS-busy status bit (0x40). meerk40t uses these for the rotary. ComMarker's own app, ComMarker Studio, has a full Z feature set:
   - Z enable, pitch and pulse settings, min/max limits
   - "Move Z axis (mm)"
   - autofocus wired through board GPIO
   - a 3D mode with **"Z axis descending distance" every N layers**, which is exactly Raio's schedule

   On at least one ComMarker model (Omni X), LightBurn's 2.1 release candidate jogged Z as "Motor 2". **What nobody has shown is that the B6's column motor is wired to the LMC axis output. Everything points to the head panel driving it.** Three tests in §3.6 settle it in an hour, with laser emission off.
3. **If the column is panel-only, the cleanest route is a motorised Z table under the work** (§3.5, path B). Drive it from the B6's own rear **Rotary port** through a stepper driver: the R5's driver box, or the MKS driver already on hand. The machine is not opened. Raio moves the table with `MoveAxisTo` between passes.
4. **Depth of focus (COMPUTED).** Assumptions: M² ≈ 1.3, raw beam ≈ 7 mm.
   - Spot ≈ **53 µm**; range 43–71 µm over M² 1.2–1.5 and D 6–8 mm.
   - Rayleigh range ≈ **±1.6 mm**; range ±1.1 to ±2.5 mm.
   - Relative fluence is 91 % at 0.5 mm off focus, 72 % at 1.0 mm and 53 % at 1.5 mm.
   - **Usable cutting DOF is about ±0.5 mm**, not ±1.6 mm. The studio's fast recipes run close to the fluence where melt still gets out. Removal there goes like ln(F/F_th), so losing 10–30 % of fluence costs a large share of the removal. The ring slot that cut "far slower" with its ends 0.4 mm out of focus is the field evidence (§1.4).
5. **Recommended z-step strategy (§2.6).**
   - Track the kerf floor: start with focus on the surface.
   - Drop **0.48 mm** (12 column pulses) every N passes, where N = 0.48 mm ÷ the measured removal per pass at that depth.
   - Keep the focus within about 0.5 mm of the floor at all times.
   - **Scale the job's XY by (1 + Δz/f) at each step**, because the F-theta lens is not telecentric. Without it, the kerf on a part 90 mm across walks 0.2 mm inward for every 1 mm of Z.
   - Measure removal on scrap as a curve, depth against pass count, not as one number.

---

## PART 1 — What the studio has already learned

### 1.1 Every focus and depth episode on record

| Date | Job | Thickness | Passes | Focus handling | What happened | Source |
|---|---|---|---|---|---|---|
| Feb 2026 | Copper cut, slow recipe | 1 mm | 50 global (wobble 0.03/0.06) | not recorded | "Without wobble, even 120 passes will not cut through. With wobble at 50 passes, clean cuts" | `studio/equipment/MACHINES.md` |
| Feb 2026 | Brass cut | 1.6 mm | 80 global | not recorded | Worked. "Pause every 40–50 passes to blow off brass dust" | `MACHINES.md` |
| ~2026-05-08 | Brass lid hole-poking | 1 mm | 50 | — | "worked, 50 passes, quick and clean" | `artworks/orbital-witnesses/logs/log.md` l.1944 |
| ~2026-05-08 | Brass holes (note) | — | **~200 passes "split across focus drops"** | **manual focus drops** | Hole recipe: 400 mm/s · 100 % · 75 kHz · 500 ns · wobble | `studio/B6-Mopa/MATERIAL-SETTINGS.md` § Notes |
| 2026-05-10 | Laser pockets in brass | Ø8 × 1.5 mm deep | — (~20 min) | — | "precise pockets … exact dimensions"; removal "20–33 µm/pass" | `log.md` l.626, l.879; `build/JOINTS.md` l.263, l.341 |
| 2026-05-10/11 | **2.5 mm Al, SLOW recipe** | 2.5 mm | 200 | **"flat at top surface (no Z staircase)"** | Clean through on a ~20 mm disk; "Slight V-taper on the edge (beam wider at top)" | `MACHINES.md` |
| 2026-05-10/11 | **2.5 mm Al, FAST recipe, Test 4** | 2.5 mm | 75 | **flat focus only** | **"does NOT penetrate"** | `MACHINES.md` |
| 2026-05-10/11 | **2.5 mm Al, FAST recipe** | 2.5 mm | 200 = **150 @ focus 0 → drop 1.0 mm → 50 @ −1.0 mm** | **one manual drop on the panel** | Through on a small disk; "last ~0.1 mm needed light force to release". "**the 1.0 mm focus drop is essential for reaching the bottom.** A single focus drop reaches the bottom; a 2nd drop (−2.0 mm) adds margin." | `MACHINES.md`; `log.md` l.1947 |
| 2026-05-11 | **OW2 large lid, 2.5 mm Al, Ø ~90 mm** | 2.5 mm | fast recipe, stopped at 16 % after 13 min, then resumed | as above | **~4 h and "the disk still wouldn't release cleanly (had to free a residual under-cut arc by hand)"**. Cause given: "the galvo field edge ruins it at large diameter — the cut path runs off-axis and defocused out near the field edge, so those arcs cut slowly and unevenly and the disk hangs on them." Outcome: lids replanned to mark + saw + sand; "For lids >~40 mm, outsource" | `MACHINES.md` l.127; `log.md` l.854–858, 1949 |
| 2026-05-13 | Al cut, test square | 1.1 mm | through at **~17** of 50 | not recorded | LOCKED at 20 global | `MATERIAL-SETTINGS.md` |
| 2026-05-13 | Copper cut | 1.1 mm | through at **~72** of 150 | not recorded | LOCKED at 80 | `MATERIAL-SETTINGS.md` |
| 2026-05-15/17 | Big lids (various) | — | — | — | "~3 hours on laser" each | `log.md` l.240 |
| Aug 2026 | PCB coupons (FR4 1.6 mm) | 1.6 mm FR4 | 6–8 | **"Focus height and whether any pass ran at a Z offset — not recorded"** | Board "lifted off the bed" for clean exit | `studio/trilha/B6-PCB-RECIPE.md` l.244; `COUPON-RUN-2026-08-18.md` l.242 |
| **2026-09-21** | **304 ring USB-C slot, cut #1** | 1.6 mm | 100 per run | **"Z was moved twice by hand, without recorded values"**; settings changed mid-cut | Through, kerf right, slow | `artworks/orbital-witnesses/build/METAL-RING-LASER-CUT.md` |
| **2026-09-21** | **Ring slot, cut #2** | 1.6 mm | 100 (check at 40–50) | Focus by eye on the outer surface; panel "Real focal length 255.15" | **"probably more in focus, because the cut is happening very fast."** Two causes: sharper focus, and the slot turned vertical so its ends are no longer **~0.4 mm out of focus** on the Ø57 curve | `METAL-RING-LASER-CUT.md`; `MATERIAL-SETTINGS.md` |
| 2026-09-21 | 11 more rings | 1.6 mm | frozen recipe | same method | ~7 min each | same |

### 1.2 What the recipes say about focus, word for word (VERIFIED)

- "Focus: flat at top surface (no Z staircase)." *(2.5 mm Al slow)*
- "150 passes @ focus 0mm → drop focus 1.0mm → 50 passes @ -1.0mm." *(2.5 mm Al fast)*
- "**high-freq/high-speed needs focus stepping, low-freq/slow-speed punches deeper with flat focus**" … "**LightBurn+B6 has no automatic Z-step but manual focus entry on the laser panel is quick.**" *(MACHINES.md key learnings)*
- "Focus: by eye on the outer surface at the slot … **treat that number as relative, not absolute**; what matters is repeating the same focusing method." *(stainless)*
- "**Sign check, do it once:** moving the head **down** pushes the focal point **into** the material. Move 0.4 mm, look at where the spot sharpens, and write the direction here: `______`" — **still blank** *(METAL-RING-LASER-CUT.md)*
- "ComMarker panel → SETTING: Focal Length **234 mm** (nominal) · **Real Focal length 255.15 mm** · Speed 12.5 mm/s · Screw pitch 8 mm · Pulse count 200/round" *(METAL-RING-LASER-CUT.md)*
- "Speed of cutting is the tell: at true focus it goes through in a fraction of the passes." *(same)*

### 1.3 The pattern (INFERRED)

1. **Every time the studio has been stuck on a cut, it was a depth or focus problem**: 2.5 mm Al flat focus, the 90 mm lid, ring cut #1. Every fix was a hand-made focus change on the panel, and none of those changes was recorded. Raio must record z per pass as a first-class part of the job log.
2. **The rule of thumb is already in the notes.** High rep rate and fast speed (75 kHz, 0.8 mJ) is focus-sensitive. Low rep rate and slow speed (20 kHz, up to 2 mJ) is forgiving. §2.4 explains why: fluence margin over threshold.
3. **The 90 mm lid was mainly a field-position problem, not a depth problem.** Off-axis the beam arrives tilted and larger. A Z-step schedule alone would not have saved it; with no XY correction it would have walked the kerf (§2.7). A large thick lid stays an outsourcing job, as the notes already decided.

### 1.4 Removal rates already measured (COMPUTED from VERIFIED counts)

| Material | Thickness | Recipe | Passes to breakthrough | Average µm per pass |
|---|---|---|---|---|
| Aluminium | 1.1 mm | 800 mm/s · 65 kHz · 350 ns · wobble 0.15 | ~17 | **~65** |
| Aluminium | 2.5 mm | 400 mm/s · 75 kHz · 500 ns · wobble 0.30, one 1 mm drop | ~200 | **~12.5** (it stalls without the drop) |
| Copper | 1.1 mm | 400 mm/s · 75 kHz · 500 ns · wobble 0.30 | ~72 | **~15** |
| Stainless 304 | 1.6 mm | 50 mm/s · 20 kHz · 500 ns · wobble 0.10 | ≤ 40–50 (breakthrough not logged; check at 40–50) | **≥ 32–40** |
| Brass, pocket | 1.5–2 mm | various | — | **20–33** (log), 5–20 (JOINTS research) |

Aluminium falls from about 65 µm/pass at 1.1 mm to about 12.5 µm/pass averaged over 2.5 mm. That **is the stall, made visible**: removal per pass drops as the floor sinks. The planner has to model depth against pass count as a curve.

---

## PART 2 — The physics, with numbers

### 2.1 Assumptions

- λ = 1064 nm; f = 210 mm (lens inscription, VERIFIED).
- **Raw beam diameter D ≈ 7 mm, M² ≈ 1.3** (ASSUMED). JPT does not publish a 60 W M7 datasheet that I could find. Resellers give 2 mJ maximum pulse energy and 2–500 ns ([woodartsupply listing](https://woodartsupply.com/products/us-stock-60w-jpt-m7-mopa-ydflp-60-m7-m-r-fiber-laser-marking-machine-fiber-laser-engraver-laser-marker-175-175mm-with-80mm-rotary-axis-compatible-with-lightburn), WEB). A distributor gives M² < 1.4 for the 80/100 W M7 ([jpt-laser.com](https://jpt-laser.com/product/80w-fiber-laser/), WEB). The B6 manual gives 60 W MOPA: 1–4000 kHz, 2–500 ns, **max pulse energy 2 mJ** (VERIFIED, `studio/B6-Mopa/files/install/B6 MOPA/Users' manual ComMarker B6.pdf` p.3).
- I do not know whether the B6 has a beam expander in front of the galvo. If it does, D is larger and every DOF below shrinks by D². **Measure; do not trust the table** (§4.6).

### 2.2 Spot and Rayleigh range (COMPUTED)

w₀ = 2M²λf / (πD) · z_R = πw₀² / (M²λ) = 4M²λf² / (πD²) · convergence half-angle θ ≈ D / 2f

| M² | D (mm) | spot 2w₀ (µm) | z_R (mm) | 2z_R (mm) |
|---|---|---|---|---|
| 1.2 | 6 / 7 / 8 | 57 / 49 / 43 | 1.99 / 1.46 / 1.12 | 4.0 / 2.9 / 2.2 |
| **1.3** | 6 / **7** / 8 | 62 / **53** / 46 | 2.16 / **1.59** / 1.21 | 4.3 / **3.2** / 2.4 |
| 1.5 | 6 / 7 / 8 | 71 / 61 / 53 | 2.49 / 1.83 / 1.40 | 5.0 / 3.7 / 2.8 |

θ ≈ 14–19 mrad (about 1°). The cone itself is very narrow: the geometric beam grows only about 0.03 mm in diameter per mm of depth. **Walls shadowing the incoming cone is not the main limit. Kerf taper, recast and melt that cannot get out are** (§2.5).

### 2.3 How fluence falls with defocus (COMPUTED, nominal case z_R = 1.59 mm)

| Defocus z | 0 | 0.25 | 0.5 | 0.75 | 1.0 | 1.5 | 2.0 | 2.5 | 3.0 mm |
|---|---|---|---|---|---|---|---|---|---|
| Spot (µm) | 53 | 54 | 55 | 59 | 63 | 73 | 85 | 99 | 113 |
| Peak fluence (relative) | 1.00 | 0.98 | **0.91** | 0.82 | **0.72** | 0.53 | 0.39 | 0.29 | 0.22 |

Peak fluence at focus is 2E/(πw₀²):

| Repetition rate | Pulse energy | Peak fluence at focus |
|---|---|---|
| 75 kHz | 0.8 mJ (60 W ÷ 75 kHz) | ≈ 73 J/cm² |
| 20 kHz | 2 mJ (capped; 60 W ÷ 20 kHz would be 3 mJ, so average power at 20 kHz is ≈ 40 W) | ≈ 180 J/cm² |

### 2.4 Why the useful DOF is much shorter than the Rayleigh range (INFERRED + COMPUTED)

Nanosecond ablation removes depth per pulse roughly as δ·ln(F/F_th). When fluence is far above threshold, a 20–30 % drop barely changes removal. When the process runs close to the fluence where melt still gets expelled, the same drop costs a large share. "Close to threshold" here means: deep in a kerf, with energy spread by wobble and absorbed in plasma and recast.

**Allowed defocus for a fluence margin m = F₀/F_needed is z_max = z_R·√(m − 1):**

| Margin m | 1.1 | 1.2 | 1.5 | 2 | 3 | 5 |
|---|---|---|---|---|---|---|
| z_max (mm) | 0.50 | 0.71 | 1.12 | 1.59 | 2.24 | 3.17 |

This accounts for both of the studio's observations:

- **Fast recipe (75 kHz, 0.8 mJ) works with little margin**, so it needs focus stepping and is hurt by about 0.4 mm of defocus.
- **Slow recipe (20 kHz, about 2 mJ) has 2.5 times the pulse energy and a large margin**, so it "punches deeper with flat focus".

**Working number for Raio: plan cutting so the focus stays within ±0.5 mm of the kerf floor.** Keep ±1 mm as the outer limit.

Thermal focal shift is another reason to plan on the short number. It has been measured at up to several Rayleigh ranges in high-power fiber cutting ([ICALEO 2012 paper 802](https://lia.org/store/product/icaleo-2012-paper-802-impact-thermal-focal-shift-laser-cutting-processes-high), WEB). At 60 W it is far smaller, but it is not zero over a 4 h job.

### 2.5 Why a 1–2.5 mm cut stalls (INFERRED, with WEB support)

1. **The floor leaves the usable DOF.** With focus on the surface, the floor reaches about 0.5 mm and fluence is down 10 %. At 1.5 mm it is down about 50 %. With little margin, removal per pass collapses. The 2.5 mm Al Test 4 at flat focus did not penetrate; one 1 mm drop fixed it.
2. **Melt and recast.** A ns pulse removes metal mostly as melt pushed out by vapour pressure. In a deep, narrow groove the melt cannot leave. It re-solidifies on the walls and floor and the kerf narrows into a V ("Slight V-taper … beam wider at top"). Wide wobble (0.30 mm, about 6 times the spot) keeps the slot open enough for melt and debris to escape and for air assist to reach the floor. That is why wobble width is "the dominant variable".
3. **Plasma and particle shielding.** At high rep rate the vapour plume from one pulse is still there when the next arrives. It absorbs and scatters part of that pulse. This gets worse in a confined groove.
4. **Aspect ratio.** A nanosecond pulsed fiber laser cutting metal along repeated passes loses efficiency as "the groove's depth and aspect ratio increase" ([Laser Focus World](https://www.laserfocusworld.com/lasers-sources/article/16551640/photonics-applied-materials-processing-nanosecond-pulsed-fiber-lasers-advance-in-metal-cutting), WEB). With a 0.3 mm kerf, 2.5 mm is an aspect ratio of about 8:1 — about the practical ceiling for a 60 W ns galvo.
5. **Off-axis (field edge).** At field radius r the chief ray is tilted by about r/f (12° at r = 45 mm, 20° at the 75 mm corner). The kerf follows the tilted ray, so the effective thickness rises and the spot becomes elliptical. F-theta field curvature adds defocus. This is the 90 mm lid.
6. **Heat.** Thin parts and copper sink heat; aluminium and brass dust is a fire risk. Neither is a focus problem, but both limit how hard each pass can be pushed.

**Realistic ceiling for this machine (INFERRED from the studio's data):**

| Material | Thickness | Verdict |
|---|---|---|
| Aluminium | ≤ 1.1 mm | routine |
| Aluminium | 2.5 mm | small parts only, with Z-stepping |
| Copper | ≤ 1.1 mm | routine |
| Copper | ~1.5 mm | probably the edge |
| Brass | ≤ 1–1.6 mm | routine |
| 304 stainless | 1.6 mm | ✓ (slow recipe) |
| 304 stainless | ~2 mm | possible with Z-stepping, untested |

Anything past about 2.5 mm, or larger than about 40 mm across in ≥ 2 mm stock: outsource. Z-stepping widens the window. It does not abolish it.

### 2.6 What "fast + wide wobble beats slow passes" means for focus (INFERRED)

Fast passes remove a **thin, steady layer** each time (about 12–65 µm), so the floor descends **predictably**. That makes the fast recipes the ones where **an open-loop Z schedule pays off most**. They are also the ones that need it, because their fluence margin is small. Slow, heavy recipes such as the stainless one are more forgiving of flat focus, but still gain from a single mid-job drop.

### 2.7 Best focus position by job (WEB + INFERRED)

| Job | Focus | Notes |
|---|---|---|
| Engrave / fill / mark | **On the surface** | Smallest spot = sharpest line. The studio's engrave recipes all assume this. |
| Deep engrave / pocket | **Track the floor**: step down about every 0.1–0.3 mm of depth | EZCAD's "Z per layer" and ComMarker Studio's "descending height every N layers" do exactly this (§3.3). |
| Through-cut, thin (≤ 0.5 mm) | Surface, or about −0.1 to −0.2 mm | |
| Through-cut, thick (≥ 1 mm) | Start on the surface, then **track the floor**, staying no more than about 0.5 mm away | The general rule is focus at about ⅓ of the depth for single-pass gas cutting. Multi-pass ablation is different because the floor moves. |
| Cleaning / annealing / colour on stainless | **Defocused, often + (head up) 1–3 mm** | Larger, gentler spot. A B6 owner reports stainless annealing worked at "out of focus +3mm" ([plasmaspider](https://plasmaspider.com/viewtopic.php?p=247887), WEB). |

### 2.8 Recommended Z-step strategy (COMPUTED + INFERRED)

**Convention.** z = 0 is focus on the top surface, as set by the operator. **Negative z = focal point inside the material**: the head goes down, or the work goes up. The sign still needs confirming on the machine (§4.6, test 1).

**Rule.**

1. **Step size Δ = 0.48 mm** (12 column pulses at 0.04 mm/pulse). Under the floor-tracking rule this is about ⅓ of z_R and keeps the focus within ±0.5 mm of the floor. Other conventions give other numbers:
   - Focus half a step below the floor, so the floor sweeps from −Δ/2 to +Δ/2: Δ can be **about 1.0 mm** (25 pulses). The studio's single 1 mm drop on 2.5 mm Al was this regime.
   - Fine floor tracking for deep pockets: **0.20–0.24 mm** (5–6 pulses).

   Always quantise Δ to whole pulses: multiples of 0.04 mm.
2. **Passes per step N = Δ ÷ r(d)**, where r(d) is the measured removal per pass **at the current depth d**, read from the depth curve (§2.9).
   - Fallback before any curve exists: r = the average from the table in §1.4, with N cut by 20 % so focus leads the floor rather than lags it.
   - Example, 2.5 mm Al fast recipe at about 12.5 µm/pass and Δ = 0.48 mm: N ≈ 38 → 30 passes per step; about 5 steps to 2.4 mm, plus a 20 % breakthrough margin. Compare the hand-made 150 @ 0 / 50 @ −1.
3. **Stop going down at z_min = −(thickness − 0.25 mm).** Never put the focus below the bottom face; that only heats the bed.
4. **Correct XY at every step (essential off-centre).** Lowering the head by Δ moves the beam at field radius r inward by about **r·Δ/f**:

   | r (mm) | 10 | 20 | 30 | 45 | 60 | 75 |
   |---|---|---|---|---|---|---|
   | inward shift per 1 mm of Z (mm) | 0.05 | 0.10 | 0.14 | **0.21** | 0.29 | 0.36 |

   With a 0.3 mm kerf, a 0.2 mm shift means the new passes open a second, displaced kerf. Raio scales the job's coordinates about the optical axis by **s = 1 + |z|/f** for each step (about +0.48 % per mm). This is easy for Raio because it builds the galvo lists itself. **Moving the work instead of the head (Z table, §3.5 B) does not remove this**; the geometry is the same. Validate it with test 4 in §4.6.
5. **End of job:** return to z0, always approaching from the same direction (backlash).

### 2.9 Measuring removal per pass on scrap (protocol)

Use a **depth-curve coupon**:

- Ten short lines, 10 mm long, side by side on the same scrap, all at the production recipe and **flat focus**.
- Pass counts N = 5, 10, 20, 30, 40, 60, 80, 100, 150, 200.

Read the depth at each N with one of:

1. **a needle-point depth gauge or dial indicator on a stand.** The kerf is 0.3 mm wide, so use a pointed probe.
2. **a cross-section.** Saw across the coupon, sand, photograph at macro with a scale. This is the gold standard and also shows the taper.
3. **a cheap substitute:** lay the coupon in a vise and focus a USB microscope on the floor, then on the surface, and read the stage travel.

Fit d(N) and store r(d) = Δd/ΔN in Raio's material library. Run it **twice, at the field centre and at r ≈ 45 mm**. Then repeat with Z-stepping enabled to show the curve no longer flattens. Expect d(N) to bend over: that bend is the stall depth, which tells you where the first step should be.

---

## PART 3 — Moving Z from software on this machine

### 3.1 How the B6 column is driven today (VERIFIED, `Users' manual ComMarker B6.pdf` pp.10–12 on disk)

- The head has **Lift up / Auto focus / Stop / Lift down** buttons and a **Setting page**:
  - "**Speed: 12.5 mm/s**"
  - "**Screw pitch: 8 mm** for ComMarker B6"
  - "**Pulse count: 200 round** — the number of pulses required for the stepper motor to complete one revolution"
  - "**Focal length**: the distance from the **inner sensor** to the engraving surface; the laser head will go up or down according to this focal length number when pressing 'Auto'"
  - "**Real focal length**: display the current focal distance while the laser head goes up or down"
  - "**Send focus**: input the number displayed on 'Real Focal length' onto 'Focus Length'"
  - "**OK: parameters will be stored by the control board**"
- "**The sensor in the machine only works in the range of 120 mm to 280 mm**; this warning will pop up while it is out of the range."
- "**The sensor is not at the center of the engraving area.** Please place the material directly under the red dot before pressing the 'Auto' button."
- Non-autofocus B6: "Press up or down button … until **the two red light points overlap**, this is the best focal point." So the two-converging-dot method exists on this family.

**What follows (COMPUTED / INFERRED).**

- Resolution is 8 mm ÷ 200 = **0.04 mm per pulse** (full-step; the panel's "200/round" means no microstepping, or the panel hides it).
- A 0.48 mm step takes 12 pulses, about 0.04 s plus acceleration.
- The column is a **closed system: stepper + lead screw + rangefinder + panel MCU**. It works with no PC attached.
- "Real focal length" is a **live rangefinder reading** in the sensor's frame. That is why 255.15 (the studio's by-eye focus) differs from the 234/233 targets (forum: factory 182 → manual 233, [LightBurn forum](https://forum.lightburnsoftware.com/t/commarker-b6-60w-mopa-initial-set-up/189402), WEB). The notes are right that it is **relative**.
- **The rangefinder gives z0 only.** Once the cut starts, the surface under the sensor does not change, so everything after z0 is open-loop. That is fine: the floor is what moves, and it cannot be sensed from above anyway.

### 3.2 Is the column on the LMC board's axis output? Evidence

**Against (the column belongs to the head panel):**
- The manual stores pitch, pulses, speed and focal length **in "the control board"** behind the head's touch panel. All motion happens from panel buttons, with no PC. (VERIFIED)
- The factory EZCAD2 config for this machine has extended axis 0 **active but generic**: `AXISSTEPPERRO0=200`, `AXISDISTPERRO0=5` mm, `AXISROTATE0=0`, no zero switch. It is not set up as an 8 mm-lead Z. (VERIFIED, `studio/B6-Mopa/files/install/B6 MOPA/EZCAD for ComMarker B6 MOPA/plug/markcfg7`, lines 30–75; `EZCAD.CFG` `m_dDefaultPulsePerUnit=200`.)
- B6 owners on LightBurn: "I have no 'enable Z axis' option … the two green buttons below it to raise and lower manually" ([forum](https://forum.lightburnsoftware.com/t/no-z-axis-option-more-newbie-trying-to-get-started-with-1st-galvo-fiber-laser/173455), WEB). A community member photographed an extra board: "likely a step generator for the extra microstep driver powering the stepper on the Z axis" (same thread, WEB).
- "Dropping Z per pass on Commarker B6": "At this current time, no" ([forum](https://forum.lightburnsoftware.com/t/dropping-z-per-pass-on-commarker-b6/169851), WEB).

**For (ComMarker does wire Z into the board on some machines):**
- **ComMarker Studio v1.0.42** (`/Applications/ComMarker_Studio.app`, VERIFIED by strings, nothing executed) holds a device-parameter block saved to the board ("SaveParamToDevice ok"). It contains:
  - `zEnable, zRevert, zSignal, zStartS, zRunS, zAcc, zOffset, zPreciseRunS, zOrder, zTimeout, bPreciseZ`
  - limits `lEnable, lLeftP, lRightP`
  - `pitchPulse, screwPitch, axisId, axisEnable`
  - `axisZDriverPar / axisZParExt`
  - GPIO roles **`autoFocusGpi, zUpGpi, zDownGpi, fcousGpi` (focus done), `fcousFailGpi`, `fcous1Gpo`** (focus-trigger output — "Conflict with focus output port")
  - the code path `UiGWK_CalcMovePluses: pitchPulse=, screwPitch=, fMoveDistance=, pulse=` and `MarkSet::UiGWK_AdjustHeight pulse:%d`

  This is exactly the B6 panel's own parameter set (pitch, pulses per rev), reproduced on the PC side. **INFERRED:** on ComMarker's newer machines, the head's up/down/auto signals and the Z stepper are wired to the main board, and the app moves Z in pulses computed from pitch.
- LightBurn 2.1.00 RC: "Galvo Z Control … also applies to BSL and EZ2 machines". Tested on an **Omni X**: "jogging the Z-Axis from the device settings is working" on "Motor 2"; homing not yet ([forum, 2026-04-16](https://forum.lightburnsoftware.com/t/omni-x-galvo-z-axis-control/189107/3), WEB).

**Board identity conflict to resolve.** `studio/B6-Mopa/R5-ROTARY.md` says the B6 contains a "**BJJCZ/JCZ LMCV4-FIBER-M**". The Raio brief says "**LMC V2u**". Either way it is the EZCAD2 family with extended-axis outputs. Read the label on the board, or the USB descriptor (protocol agent).

**Verdict: unknown until tested.** My prior is about 70 % that the B6's column is driven only by the head panel's own driver, not by an LMC axis output. Tests are in §3.6.

### 3.3 What each program offers for Z today

**LightBurn**
- Docs describe galvo **Z-Axis Control**:
  - Enable Z Axis
  - **Motor 1/2** (the LMC extended axis)
  - Steps per unit
  - acceleration, minimum and maximum steps per second, homing ([docs, Galvo Ports](https://docs.lightburnsoftware.com/2.1/Reference/DeviceSettings/GalvoPorts/), WEB)
- **In the 2.1 final release (2026-05-19), EZCad2 Z control was pulled**:
  - "We added initial support for Z control for EZCad2-based Galvo lasers … in the first several Release Candidates … After testing, we decided this feature was not yet ready to go live."
  - "EZCad2 Galvo Z Control will return soon™."
  - EZCad3: jogging only; "we will add support for automatic Z stepping during jobs in a future update" ([announcement](https://forum.lightburnsoftware.com/t/lightburn-2-1-quick-nest-enhanced-camera-support-undo-history-and-more/189743), WEB)
- Oz (LightBurn, 2025-10-14): "doing Z-per-pass within a job is the FIRST thing everyone is going to ask for" and it requires "re-architecting the sender" ([forum](https://forum.lightburnsoftware.com/t/z-control-for-galvo/161991?page=9), WEB).
- Support manager Colin Worobetz, 2025-01-10: "Z control isn't strongly supported in EZCAD2 based devices" ([forum](https://forum.lightburnsoftware.com/t/z-control-for-galvo/161991), WEB).
- A July 2026 timeline thread gives only "Month(s)" ([forum](https://forum.lightburnsoftware.com/t/galvo-z-axis-control-addition-timeline/190767), WEB).
- I found **no release after May 2026 that restored EZCad2 Z or added Z-per-pass**. The studio runs 2.1.04; check Device Settings → Galvo for a Z section to be sure.
- **Even if LightBurn adds it, it can only drive Z if the column is on the board** (§3.2).

**EZCAD2** (VERIFIED, `EZCAD software Manual.pdf` on disk)
- §4.18 "**ExtAxis**" is a control object you place in the object list between marking objects. It moves an extended axis absolutely or relatively.
- Chapter 8 configures the expansion axis:
  - reverse
  - pulses per round (X = 360/N · n)
  - minimum and maximum speed
  - acceleration time
  - go to start after finish
  - zero switch, zero timeout, accurate zero
- Field practice (INFERRED) builds "deep engraving with Z step" as: object (n loops) → ExtAxis −Δ relative → object → … This again only works if the column is on the axis output. EZCAD2's object "Z position" and the board's `EnableZ/SetZData` commands are for **3-axis dynamic-focus heads** (a moving lens), not a lifting column.

**ComMarker Studio** (VERIFIED by strings; operator-level reading)
- **Z panel in the mark window:** `widget_z`, `lineEdit_z`, focal position label/edit, `btn_tofocalpos` ("go to focal position"), `btn_setfocalpos` ("set focal position"), `btn_up`/`btn_down`, `lineEdit_zpluse` (Z in pulses), left/right limit, work height, `btn_home`, `btn_stop`. Strings include "Move axis failed", "移动Z轴(mm)" (*move Z axis, mm*), "使能Z轴" (*enable Z axis*) and "手动Z轴" (*manual Z axis*).
- **AutoFocus panel:** `pushButton_AutoFocus`, `pushButton_HCalib` (height calibration), manual focus distance entry. Messages:
  - "对焦完毕！高度值：" (*focus finished! height value:*)
  - "对焦完成，设备非最佳焦距，请重新调整" (*focus done, device not at best focal distance, please readjust*)
  - "获取焦距测高数据发生错误" (*error reading the height-measurement data*)
  - "[最佳焦距]应该在电机Z轴[最小坐标]和[最大坐标]范围内" (*best focal distance must lie within the motor Z axis min/max coordinates*)
  - "最小坐标为最低点，应设置为零" (*minimum coordinate is the lowest point, set it to zero*)
  - `FocusDistanceRange` default **"0,300"**
  - stored `fBestFocalDistance`, `fAdjustHeightModuleValue` with a "Refresh adjust-height value" button

  Read together, this is an autofocus driven by a **height-measuring module** whose reading the app pulls from the device. The app compares it with a stored best focal distance and moves the Z motor within min/max soft limits.
- **AutoFocus help line:** "用罩子遮挡光线，对焦更精准" — *"cover with the hood to block light; focusing is more accurate."* Ambient light matters, so the sensor is **optical** (laser triangulation / ToF / LiDAR) (INFERRED). ComMarker markets "**LiDAR Focus Always Ready**" on its Gen-X line ([commarker.com](https://www.commarker.com/products/b6-mopa-fiber-laser-engraver), WEB). There is also a camera path (`Vision_AutoFocus`, `VisionAdjustHeightThread`) for camera models; "拍照前…完成对焦" means *focus before taking the photo*.
- **3D layered engraving dialog** (`Occ3DDialog`, `DlgThreeDCarvePara`):
  - "Number of layers"
  - "Every N layers"
  - "**Descending height**"
  - "**Z axis descending distance**"
  - "Adjust Z-axis"
  - "Cleaning" / "Cleaning layer interval"
  - "Axis Depth", "Calibration Depth", "Z Spacing", "每层高度" (*height per layer*)

  **INFERRED from the labels:** this is "lower Z by D every N layers", with optional cleaning passes every M layers. **That is Raio's focus plan, already shipped by ComMarker**, but only for 3D relief engraving and only on machines whose Z is on the board. Confirm by opening the dialog with no machine connected. The `.cfg` files in `Data/config` are obfuscated, so the B6 device profile (pulses/mm, travel) could not be read.
- **Which boards it drives:** `liblcsDI`, `libfpgaUpdate`, `LcsLmcParam`, `LmCrypto`; version string "**LCS2.1.8595**". That is ComMarker's BSL/LCS controller family; whether it talks to the studio's LMC board is for the protocol agent to confirm. LightBurn treats "BSL fiber" as a family of its own with Z homing ("BSL fiber Z homing was using ZMotorIndex…", 2.1 changelog, WEB).

**meerk40t / balor** (VERIFIED, `meerk40t/balormk/controller.py` and `galvo_commands.py`, fetched to scratch)
- Opcodes:
  - `SetAxisMotionParam = 0x0026` (min, max speed)
  - `SetAxisOriginParam = 0x0027` (acceleration time)
  - `AxisGoOrigin = 0x0028`
  - `MoveAxisTo = 0x0029` (position as two 16-bit words, sign bit 0x80000000)
  - `GetAxisPos = 0x002A` (index)
- Status bit `AXIS = 0x40`; `wait_axis()` polls until it clears.
- Console commands `rotary_to`, `rotary_relative` (defaults minspeed 100, maxspeed 5000, acc 100) and `rotary_pos`.
- **So a "move extended axis" primitive exists and is a stand-alone command, not a list command.** It runs between lists, which fits "stop → move → wait → resume".
- `EnableZ 0x003A / DisableZ 0x0039 / SetZData 0x003B` also exist. They are the dynamic-focus Z, not the column. Do not confuse them.

### 3.4 The B6's other door: the rear Rotary port (VERIFIED, `studio/B6-Mopa/R5-ROTARY.md`)

- The B6 already outputs **pulse/dir (+24 V) on the rear "Rotary" aviation port** to an external DM542-class driver box. That box drives the R5's 4-wire stepper (12,800 steps/rev on the R5).
- The pinout is unpublished. It can be found with ComMarker support or a multimeter.
- The studio has a spare **NEMA 17 (17HE15-1504S)**, a **NEMA 23** and an **MKS stepper driver**.
- In balor terms this is extended axis 0 (EZCAD "axis A"). LightBurn's rotary uses it.

### 3.5 Paths for Raio, best first

| Path | What | Software | Hardware risk | Notes |
|---|---|---|---|---|
| **A. Column already on the board** (if test b passes) | Raio calls `MoveAxisTo` on the axis the column uses | Native: stop list → move → wait AXIS → next list | none | Ideal. The panel's autofocus probably still sets z0. |
| **B. Motorised Z table under the work, on the Rotary port** | A small lab-jack or lead-screw stage (NEMA 17 + 1–2 mm lead + linear rails, ≥ 10 mm travel), driven by the R5 driver box or the MKS driver from the rear Rotary port | Same `MoveAxisTo` primitive; steps/mm set in Raio | **none to the machine** (external plug) | **Recommended if A fails.** Moving the work up by Δ = moving the head down by Δ. Resolution about 1 µm with microstepping. Light load. The machine keeps its own autofocus for z0. Cannot be used together with the rotary, which is fine. Needs the Rotary-port pinout, already an open question. |
| **C. Take over the column motor** | Put a DPDT relay or 4-pole switch on the column stepper's 4 coil wires: panel driver ↔ external driver fed from the Rotary port | `MoveAxisTo` | **medium**: open the head, cut into the harness; a wrong switch under power can kill either driver; warranty | Never switch while a driver is energised. The panel's autofocus is lost while in Raio mode. |
| **D. Separate Z controller** | ESP32/GRBL board + driver on the column motor (as C) or on a table (as B), on its own USB serial port | Raio sends serial "move Z" between lists | as B or C | Use only if the Rotary port is unusable. Two USB devices, but completely independent of the LMC. |
| **E. Drive the panel's own inputs** | If tracing shows the panel's Up/Down/Auto are simple active-low inputs, have the LMC output ports (`WritePort`) or an opto-isolator pull them for timed pulses | `WritePort` + timing | low–medium | Open-loop by time (12.5 mm/s → 0.04 s per 0.5 mm). Poor resolution. **Better variant:** "Auto" with a changed target is not reachable without the touch panel. Fallback only. |

### 3.6 The tests that decide it (all with emission disabled: key off or source unpowered, shutter capped)

1. **ComMarker Studio test (5 min).** With the B6 on USB, does ComMarker Studio connect at all? Do its Z+/Z− or AutoFocus move the column? **If yes, path A is proven**, and the protocol agent can sniff the commands it sends.
2. **meerk40t / Raio-probe test (10 min).** Send `rotary_relative 25` and `rotary_relative -25` (25 pulses = 1 mm if the column were on that axis at 200 pulses/rev), then the same on axis index 1. **If the column moves, path A.** If nothing moves, put a scope or LED on the Rotary port: it should pulse, proving the port is a usable path B.
3. **Trace the wire (30 min, machine unplugged).** Follow the column stepper's cable. Does it end on the head panel PCB (expected), on an LMC header, or at the rear port? Photograph the panel board's connectors and any header labelled UP/DOWN/AUTO/FOCUS. That photograph decides path C or E.
4. While inside: **read the board label** (LMCV4-FIBER-M or V2u) and note whether there is a beam expander between the source and the galvo. That changes D in §2.2.

### 3.7 Knowing the true focus (feedback)

| Method | What it gives | Verdict |
|---|---|---|
| **The B6's own rangefinder** (Auto button) | z0 relative to the sensor frame; 120–280 mm; off-centre | Use it for z0, then **trust Raio's own step count**. Re-auto only between jobs. |
| **Two converging red dots** (non-Pro B6) | Visual focus, about ±0.3–0.5 mm by eye | Fine for setup; not automatable without a camera. |
| **Mechanical focus gauge** (a printed block of the measured lens-to-work distance) | Repeatable, ±0.1 mm | Cheap; the reference for calibrating everything else. |
| **Spot test / ramp test** (a line on a tilted scrap, or the staircase in §4.6) | The **true optical focus**, ±0.1–0.2 mm | **Do this once per lens / per material** and store the offset between the sensor's z0 and true focus. |
| **ToF sensor (VL53L1X)** | ±1–5 mm on bare metal | Too coarse for focus. No. |
| **Sharp IR triangulation** | ±0.5–1 mm, poor on shiny metal | No. |
| **Industrial laser triangulation** (Keyence IL / Panasonic HG-C1050, about ±10–30 µm at 50 mm) | Real surface height near the spot | Yes, if Raio later wants closed-loop height mapping (warped sheet, curved rings). Mount off-axis on the head; **compensate the offset as the B6's sensor does**. About $150–400 used. |
| **Camera contrast** (focus on the red-dot spot or a low-power test mark) | Relative sharpness | Possible later; the red dot is not at 1064 nm focus, so calibrate the offset. |

**Note on mid-job feedback.** None of these can see the kerf floor while cutting. Floor tracking stays **open-loop on the measured removal curve**, checked by "does the cut speed up?" (Edson's tell) and, later, by a coaxial camera.

---

## PART 4 — Raio feature spec: Focus Plan (proposal)

### 4.1 The focus-plan object

```yaml
focus_plan:
  id: al-2.5-fast-v1
  material: aluminium-6061      # from Raio material library
  thickness_mm: 2.5
  recipe_ref: al-2.5-cut-fast   # speed/freq/pulse/wobble live in the recipe, not here
  z_axis: column | table        # which actuator (see §3.5)
  z0_source: panel_autofocus | gauge | manual
  z0_offset_mm: 0.00            # measured: true focus minus z0 from the staircase test
  sign: head_down_is_negative   # confirmed by test 1 (§4.6)
  step_mm: 0.48                 # quantised to actuator pulses (0.04 on the B6 column)
  schedule:                     # explicit and editable; generated from the removal curve
    - {z: 0.00,  passes: 30}
    - {z: -0.48, passes: 30}
    - {z: -0.96, passes: 32}
    - {z: -1.44, passes: 36}
    - {z: -1.92, passes: 40}
    - {z: -2.24, passes: 30}    # z_min = -(t - 0.25)
  xy_scale_per_mm: 0.00476      # 1/f; applied as s = 1 + |z| * k about the field centre
  check_after_pass: [120, 160]  # Raio pauses to show "look at the kerf"
  breakthrough_margin: 0.20
  return_to_z0: true
```

`schedule` can also be generated: `auto: {removal_curve: al-2.5-fast-curve, step_mm: 0.48, lead: 0.8}`.

### 4.2 Operator flow

1. Place the work. Focus on the surface using the method the plan names: press **Auto** on the panel, or use the gauge. Raio reads or records it as **z0** (axis position = 0).
2. Raio shows the plan: steps, pass counts, total time, max depth, the XY scale per step, and a warning if the part extends past r ≈ 40 mm in ≥ 2 mm stock.
3. **Run.** For each step:
   - send the pass lists at the current z
   - **wait until the list has finished** (READY and not BUSY)
   - confirm the laser is off
   - move Z by Δ
   - **wait for AXIS (0x40) to clear** and settle 200 ms
   - re-scale XY
   - continue
4. At `check_after_pass`, pause with the light on and a prompt: *through? stop / continue / add 10*.
5. End: return to **z0, approaching from above** (one direction only, against backlash), then log every pass's z, time and parameters to the job record.

### 4.3 Safety rules (hard)

- **Never move Z while the laser can fire.** Moves are allowed only after the mark list has fully finished, `LaserSignalOff` has been sent, and status shows not BUSY. Moves are never placed inside a list.
- **Never move during list execution.** Z moves are never interleaved into a list; they always go between lists.
- **Soft limits:** z ∈ [z0 − (thickness + 0.5), z0 + 10] mm, and inside the column's or table's absolute travel. Refuse any plan that exceeds them. Use the head-to-work clearance to avoid collisions, especially with a vise or angle block (the rings).
- **Pause and resume:** Pause completes the current pass (or aborts the list) and **never moves Z**. Resume re-reads the axis position before continuing; if it differs from the logged z, stop and ask.
- **Abort:** laser off, list stopped, Z left where it is (no automatic retract into a clamp), position logged.
- **The panel's buttons are hot.** Tell the operator not to touch Up/Down/Auto during a Raio job. If path E is used, Raio owns those lines. A position that moves without Raio moving it fails the run.
- **Air assist must stay on across Z moves.** A pause is not a reason to stop air (fire risk with Al and brass dust).

### 4.4 Calibrating steps per mm

1. Start from nameplate: column 8 mm lead ÷ 200 pulses = 25 pulses/mm. For a table: lead ÷ (steps × microsteps).
2. **Measure:** a dial indicator on the bed touching the head (or the table top). Command +5.00 mm and −5.00 mm, three times each, approaching from the same side. The mean gives true pulses/mm; the up-versus-down difference gives **backlash**.
3. Cross-check with the panel's "Real focal length" before and after a 5 mm Raio move: it should change by 5.00 ± 0.05.
4. Store pulses/mm, backlash and the direction sign in the device profile.

### 4.5 Required data in the material library

- For each (material, thickness, recipe): the **removal curve d(N)** at the field centre and at r = 45 mm (§2.9), the **z0 offset** from the staircase test, and the breakthrough pass count.

### 4.6 First experiments on scrap (order matters)

| # | Test | How | Reads |
|---|---|---|---|
| 0 | Decide the actuator | §3.6 tests 1–3 (emission off) | Path A / B / C |
| 1 | **Sign check** (fills the blank in METAL-RING-LASER-CUT.md) | Mark a short line at z0, then move the head down 1 mm and mark again | Which direction makes the second line wider. Record it. |
| 2 | **Staircase** | Same short line (10 mm, production recipe, a fixed N such as 30 passes) at **z = +0.5, +0.25, 0, −0.25, −0.5, −0.75, −1.0 mm** (steps of 6 pulses = 0.24 mm), on one scrap, at the field centre. Repeat at r ≈ 45 mm. | The **deepest line = true cutting focus**; the curve width = effective DOF. The offset from z0 → `z0_offset_mm`. The + side brackets the sign and shows the curve is symmetric. |
| 3 | **Removal curve** | §2.9 coupon, flat focus, N = 5…200 | d(N), and the stall depth |
| 4 | **Telecentricity / XY scale** | Mark a 100 mm square at z0 and at z0 − 2 mm (head down) | Measure both with calipers; expect the second square's sides about 0.95 mm shorter (each edge moves inward 50 × 2 / 210 ≈ 0.48 mm). That confirms k = 1/f or gives the true value. |
| 5 | **Z-step vs flat, A/B** | Two identical 20 mm discs in 2.5 mm Al: (a) the old 150 @ 0 / 50 @ −1, (b) a Raio plan from tests 2–3 | Passes to release, time, edge quality |
| 6 | Field-edge rerun | Same plan at r = 45 mm, with and without the XY scale | Whether off-axis thick cuts become possible at all |

---

## Sources

**Studio files (VERIFIED):**
- `studio/B6-Mopa/MATERIAL-SETTINGS.md`, `README.md`, `R5-ROTARY.md`
- `studio/equipment/b6-mopa.md`, `studio/equipment/MACHINES.md` (B6 section, l.8–135)
- `artworks/orbital-witnesses/build/METAL-RING-LASER-CUT.md`, `build/JOINTS.md` (l.263, 341)
- `artworks/orbital-witnesses/logs/log.md` (l.240, 626, 854–858, 879, 1935–1950)
- `studio/trilha/B6-PCB-RECIPE.md` (l.244), `COUPON-RUN-2026-08-18.md`, `MATERIAL-QIMOO-FR4.md`
- `studio/B6-Mopa/files/install/B6 MOPA/Users' manual ComMarker B6.pdf` (pp.3, 9–12)
- `…/EZCAD software Manual.pdf` (§4.18, ch.8)
- `…/EZCAD for ComMarker B6 MOPA/plug/markcfg7`, `EZCAD.CFG`

**Installed app (VERIFIED, strings only, nothing executed):**
- `/Applications/ComMarker_Studio.app/Contents/MacOS/ComMarker_Studio` (v1.0.42, log "LCS2.1.8595")
- `Contents/Frameworks/liblcsDI.dylib`, `libmark.dylib`, `libparam.dylib`, `libtransfer.dylib`
- extracted string dump: `/private/tmp/claude-501/raio-z/cms.txt`

**Code (VERIFIED):** meerk40t `meerk40t/balormk/controller.py` (opcodes l.60–130, `wait_axis` l.797, axis methods l.1592–1605) and `galvo_commands.py` (`rotary_to` / `rotary_relative` / `rotary_pos`, l.672–737), from github.com/meerk40t/meerk40t `main`.

**Web:**
- LightBurn docs, Galvo Ports / Z-Axis Control: https://docs.lightburnsoftware.com/2.1/Reference/DeviceSettings/GalvoPorts/
- LightBurn 2.1 announcement (EZCad2 Z pulled, 2026-05-19): https://forum.lightburnsoftware.com/t/lightburn-2-1-quick-nest-enhanced-camera-support-undo-history-and-more/189743
- Omni X Z jog on Motor 2 in the 2.1 RC: https://forum.lightburnsoftware.com/t/omni-x-galvo-z-axis-control/189107/3
- Z control for Galvo (Oz 2025-10-14; Worobetz 2025-01-10): https://forum.lightburnsoftware.com/t/z-control-for-galvo/161991 and `?page=9`
- Galvo Z timeline: https://forum.lightburnsoftware.com/t/galvo-z-axis-control-addition-timeline/190767
- Dropping Z per pass on Commarker B6: https://forum.lightburnsoftware.com/t/dropping-z-per-pass-on-commarker-b6/169851
- No Z option, galvo fiber: https://forum.lightburnsoftware.com/t/no-z-axis-option-more-newbie-trying-to-get-started-with-1st-galvo-fiber-laser/173455
- Z in JCZFiber driver (Omni 1 UV): https://forum.lightburnsoftware.com/t/z-axis-setting-in-jczfiber-driver/179854
- Omni X autofocus via ComMarker Studio: https://forum.lightburnsoftware.com/t/autofocus-for-omni-x-and-z-axis-movement/190001
- B6 60 W initial set-up (autofocus 182 → 233 mm): https://forum.lightburnsoftware.com/t/commarker-b6-60w-mopa-initial-set-up/189402
- B6 owners, plasmaspider (autofocus faults; anneal at +3 mm): https://plasmaspider.com/viewtopic.php?p=247887
- ComMarker B6 MOPA product page ("Auto-Focus", "LiDAR Focus" on Gen-X): https://www.commarker.com/products/b6-mopa-fiber-laser-engraver
- Laser Focus World, ns fiber metal cutting, aspect ratio: https://www.laserfocusworld.com/lasers-sources/article/16551640/photonics-applied-materials-processing-nanosecond-pulsed-fiber-lasers-advance-in-metal-cutting
- ICALEO 2012 #802, thermal focal shift: https://lia.org/store/product/icaleo-2012-paper-802-impact-thermal-focal-shift-laser-cutting-processes-high
- JPT M7 specs (reseller / distributor): https://woodartsupply.com/products/us-stock-60w-jpt-m7-mopa-ydflp-60-m7-m-r-fiber-laser-marking-machine-fiber-laser-engraver-laser-marker-175-175mm-with-80mm-rotary-axis-compatible-with-lightburn · https://jpt-laser.com/product/80w-fiber-laser/
- Peter Verdone, JCZ axis wiring (via R5-ROTARY.md): http://www.peterverdone.com/laser-accessories/

## Open questions for Edson

- ❓ Can we run tests 0–1 from §3.6 / §4.6 (emission off) this week? Everything else in the spec waits on "is the column on the board?"
- ❓ Is there room on the bed for a ~100 × 100 mm Z table with about 15 mm of travel under the work (path B)?
- ❓ The board label: LMCV4-FIBER-M (R5 note) or LMC V2u (Raio brief)?
