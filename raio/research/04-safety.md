# 04 · Safety: the B6 MOPA and what Raio must enforce

Companion to `03-machine.md`. Written 2026-10-21. Tags are the same: VERIFIED (manual or local files), WEB (URL), INFERRED, COMPUTED, UNKNOWN.

**The situation in one paragraph.** Our B6 is a **Class 4, 60 W, invisible 1064 nm** laser with pulses up to 2 mJ and peak power over 10 kW (JPT manual; ~15 kW at 2 ns by `03-machine.md` §5). It sits in an **open frame**:
- no enclosure;
- no key switch;
- no door interlock configured;
- no stop input configured;
- a **foot pedal wired to start jobs**.

The only hardware safety device is the mushroom E-stop on the base, and what it cuts is not yet known. Everything else is software and the operator. Raio becomes the main safety layer, so it must be stricter than LightBurn.

---

## 1. Hazards specific to our work

| Hazard | Where it comes from in our work | Notes |
|---|---|---|
| **Eye damage from direct or reflected beam** | Every job. Worst cases: polished copper and brass (≈95 % and ≈65 % reflective at 1064 nm, `MATERIAL-SETTINGS.md`); curved polished rings (the 304 Witness rings), which spray reflections sideways; the aluminium fixture under PCBs. | The beam is invisible. The red dot is a different, harmless laser, so seeing red tells you nothing about the 1064. The diffuse glow of a cut is not the hazard; the specular reflection is. |
| **0 % is not off** | Any "power 0" moment. | JPT M7-M-R manual: "even at 0 % power emitting, the average output … is still around 100 mW". That is a Class 3B level of invisible beam, enough to injure the eye (WEB, [JPT manual](https://pdfcoffee.com/ydflp-6-v1-pdf-free.html)). Only emission **disabled** is off. |
| **Skin burns** | Hands near the field: fixing parts, reaching under the head. | LightBurn forum: the beam "can be felt when reaching under it, even out of focus"; a UV-laser user got a burn reaching under the beam ([thread](https://forum.lightburnsoftware.com/t/galvo-fiber-laser-safety-issue/188757), Mar–Apr 2026). |
| **Beam left on during "pause"** | Pausing a running job. | On a BJJCZ galvo, LightBurn's framing-window Pause stopped the galvo but **left the beam on at 95 %** and burned a line across the sheet (Mar 30 2026, same thread). LightBurn's Oz: Pause sends one command and "it's up to the controller" to turn the beam off. It could not be reproduced afterwards; no fix is known. |
| **Pedal starts the loaded job (under LightBurn/EZCAD)** | The foot switch on input 14 (`03-machine.md` §2). The host software polls that input, so it is live while LightBurn or EZCAD is connected. Under Raio it does nothing unless Raio polls it (INFERRED from [EZM] §10.4.3: "in idle state, the software will start mark if…"). | A knock or electrical noise starts the job. LightBurn's docs advise setting Start Marking to None if unused, "to prevent accidental firing from electrical noise" ([docs](https://docs.lightburnsoftware.com/2.1/Reference/DeviceSettings/GalvoPorts/)). Whether a pedal start bypasses LightBurn's "Require Framing" is UNKNOWN; assume it does. |
| **Fire** | FR4 (it caught fire with visible flame in coupon run 3, 2026-08-18); paperboard and card tests; resin from PCB holes; aluminium dust plus heat plus air; dust and debris under the perforated bed. | Air assist feeds flames as well as clearing smoke. Through-cuts fire into whatever is under the bed: the bed is perforated with no barrier ([makerhacks review](https://www.makerhacks.com/commarker-b6-60w-mopa/)). **An aluminium fire is a metal fire (Class D): never water.** Use a Class D extinguisher or dry sand. |
| **Fumes** (the chemistry in the rows below is INFERRED: general industrial-hygiene knowledge, not measured here) | | |
| **Fumes: stainless 304** | The ring slots, about 7 min each. | Vaporised 304 gives chromium oxides, including **Cr(VI)** (a carcinogen), and nickel oxide. Extraction is mandatory (`MATERIAL-SETTINGS.md` already says so). |
| **Fumes: brass** | Lid engraves and cuts, pockets. | Zinc oxide fume causes metal fume fever. **Free-machining brass (C360) carries about 2.5–3.7 % lead** (INFERRED, general alloy data). Find out which brass the lids are. Brass dust is very fine (`MACHINES.md`). |
| **Fumes: copper** | Lids, PCB foil. | Copper oxide fume (also a metal fume fever agent). |
| **Fumes: FR4 / PCB** | Every board. | Glass-fibre epoxy with brominated flame retardant. Burning gives **hydrogen bromide and brominated organics** (dioxin and furan class at incomplete combustion), plus glass-fibre dust. Charring and smoke plumes were heavy at the wrong settings (run 3). |
| **Fumes: aluminium, anodised aluminium, galvanised steel** | Al lids; possible future stock. | Al: oxide dust and a flammable fine powder. Anodised: dyes and sealants burn off as organic fume. Galvanised: zinc fume. |
| **Fumes: plastics** | Listed as markable by ComMarker (PP, PE, ABS). | **ABS releases hydrogen cyanide; PVC/vinyl releases chlorine and HCl. Never laser PVC.** |
| **Falling cut parts** | PCB cutouts, small slugs. | The V3 board dropped at pass 5–6 and the remaining passes **fired into the loose board** (2026-08-23). A dropped part can also tilt and reflect. |
| **Thermal: hot parts** | Long cuts (100-pass stainless, 80-pass copper). | Parts and vise are hot after the job. |
| **Electrical** | Mains, an ungrounded outlet. | The manual demands a grounded supply with < 5 % fluctuation. |
| **Head crash** | The Z lift has no documented limit switches (`03-machine.md` §3). | A Down command can drive the lens into a tall part. |
| **Lens cap** | First use after storage. | Firing through the plastic cap burns it onto the lens [MAN] p.4. |

---

## 2. Rules Raio must enforce

Each rule is something the software does, not something it asks the operator to remember. "Block" means the Start control is disabled until the condition holds.

### A. Never fire without a confirmed preview
1. **A frame before every job, automatically.** Start is disabled until a red-light frame of *this exact job* has run with no edits since. This is the same idea as LightBurn's "Require Framing Before Start", which is on in our profile.
2. **The frame is the contour, not just the box.** On the board signature that LightBurn doesn't recognise, framing draws a straight line instead of the outline. If Raio's frame looks wrong, Raio must say so and refuse to continue (`03-machine.md` §8).
3. **Explicit arming.** After the frame, Start requires one deliberate confirmation showing material, recipe name, total passes, estimated time, and the "focus confirmed" state. No keyboard shortcut fires the laser.
4. **No "test fire" button.** EZCAD's "Test laser" fires for a set time into whatever is under the lens. A test in Raio is a normal small job and goes through the same gates.

### B. Confirm focus
5. Before each job the operator states how focus was set (autofocus, eye, or ruler) and the panel's Focal Length and Real focal length values. Raio logs them. Raio warns when autofocus was used on a curved, small or off-centre part: the sensor is off-centre and reads the vise or bed (`03-machine.md` §7).
6. **Planned Z steps become checkpoints.** Raio can't move Z (`03-machine.md` §3). A recipe that needs focus drops, such as 2.5 mm Al "150 passes, −1.0 mm, 50 passes", is split into blocks. Between blocks, Raio stops with emission disabled and asks for the move ("lower 1.0 mm now; panel should read X"). It resumes only on confirmation. This removes the unrecorded mid-job Z moves of ring cut #1.

### C. Validate the laser parameters
7. **Pulse width is picked from the source's discrete list only.** The list is frozen after the source label is read; until then, use the 60 W M7-M list in `03-machine.md` §5. An unlisted width may silently run the *previous* width.
8. **Frequency is clamped to the chosen width's maximum** (for example 500 ns ≤ 500 kHz, 350 ns ≤ 600 kHz). If it is below the full-power cutoff, Raio shows the real average power ("20 kHz at 350 ns = 30 W average").
9. **Power, speed and passes stay inside a per-material envelope** taken from the locked recipes in `MATERIAL-SETTINGS.md` and `B6-PCB-RECIPE.md`. Going outside the envelope needs a typed reason, which is logged.
10. **One pass count, shown as the total.** No hidden multiplier: the "Global Passes × Number of Passes" trap (10 × 100 = 1000) must be impossible. Raio shows the total passes and an estimated time; anything over a material's recorded breakthrough + 20 % needs confirmation.
11. **Breakthrough checkpoints for cuts.** For stainless, stop at 40–50 passes to check the kerf. For PCB cutouts, stop at pass 5 and confirm the board is still seated or has been removed. Continuing after release damages the part.

### D. Required environment
12. **Air assist and extraction are confirmed per job**, by checkbox until there is a sensor. For stainless, brass, FR4 and plastics, extraction "on" is required, not optional.
13. **Material must be declared.** No job starts on "unknown". PVC, vinyl, PTFE and unknown plastics are blocked.
14. **Lens cap check** on the first job of each session.
15. **Warm-up.** No emission within 12 s of the machine powering on (JPT: PA is accepted only after 12 s with MO high; `03-machine.md` §5).

### E. Presence and time
16. **Never unattended.** Raio asks for a "still here" press every few minutes during any job (suggested 5 min; 2 min for FR4 and plastics). No answer means a stop (rule 18). This is the software stand-in for a fire watch. It matters because the studio has run multi-hour cuts while working at another machine (§4).
17. **Maximum job time per material.** The estimate must be within limits. A job over 30 min needs an explicit "long job" acknowledgement and is broken into checkpoints (rule 11).

### F. A stop that is real
18. **Stop = abort, then emission off, then verify, in that order:**
    - (1) Abort the list on the board, so it stops executing and the buffer is cleared.
    - (2) Explicitly disable emission: laser off, then MO off. **Never rely on "pause" or on power 0.**
    - (3) Read the board status back and show "STOPPED, EMISSION OFF" only when it confirms.
    - If confirmation does not arrive within the measured stop latency plus margin (the reverse-engineered stack reports ~2 s; measure it in §3, and until then use 3 s), Raio shows in red: **"Cannot confirm the laser is off. Press the E-STOP."**
19. **No "pause" that leaves the job loaded.** A checkpoint stops and disables emission, then resumes as a fresh job from a pass index.
20. **Failure modes and what Raio does in each:**

| Failure | What Raio does | Status of the facts |
|---|---|---|
| Operator presses Stop | Rule 18 | — |
| Presence timeout | Rule 18 | — |
| Raio crashes or freezes, or the Mac sleeps | Raio cannot act. Raio must hold a macOS no-sleep assertion during jobs. Each list sent to the board should be short (one pass block), so the board runs out of work quickly. | Whether the board keeps executing what it has is UNKNOWN; test it (§3). |
| USB unplugged or dropped mid-job | Same as above, plus a red banner on reconnect: "Last job was interrupted at pass N. Do not restart without a new frame." | User report: it "would stop marking" (LightBurn forum). Not proven. |
| Pedal pressed unexpectedly | **Raio does not implement pedal start**, or ships with it off by default and only enables it per session. LightBurn's Start Marking should be set to None while LightBurn is still in use. | Pedal is on input 14 today, live under LightBurn/EZCAD. |
| Laser alarm (temperature) | Not detectable today: no alarm input is configured. If the board exposes it, show it and refuse new jobs. | UNKNOWN |

21. **The host must never be the only stop.** Whatever the USB test shows, the E-stop must be within reach, and the operator checklist (§5) says so.

### G. Software interlocks to copy from LightBurn and EZCAD

| Feature | Raio equivalent |
|---|---|
| Require Framing Before Start (LightBurn, on) | Rule 1 |
| Job Checklist (LightBurn, off) | §5 as a blocking checklist |
| Door Protect input (LightBurn) | Ready for the hardware in §6 |
| Stop Marking input (LightBurn and EZCAD) | Ready for the hardware in §6 |
| "Show start mark dialog" (EZCAD) | Rule 3 |
| "Marking IO", output high while marking (EZCAD) | Drive a warning beacon (§6) |

---

## 3. USB disconnect and host failure: unknown, so test it

**What is known.**
- LMC boards execute command lists from an internal buffer that the host streams to.
- The reverse-engineered stack reports that "stopping a job in process works but currently takes ~2 seconds" ([balor-meerk40t](https://github.com/tatarize/balor-meerk40t)).
- One user reports the job stopped when LightBurn lost the connection ([LightBurn forum](https://forum.lightburnsoftware.com/t/lightburn-galvo-latest-version-laser-random-disconnects/111196)).
- **Nobody documents what the board does with a list already buffered when USB goes away.**

**Test protocol.** Run it once, before Raio fires anything real.
1. Goggles on. E-stop within reach. Extraction on. **Non-flammable target**: a steel or anodised-aluminium offcut, not paperboard. If the beam sticks at one point, as in the pause incident, card ignites.
2. Use a job long enough that it cannot all sit in the board's buffer: a **hatch fill** of about 40 × 40 mm at 0.02 mm interval (thousands of vectors), **10–20 % power, 1000 mm/s, 30 kHz, 200 ns**, several minutes long. A short outline job (for example 50 passes of a square, about 16 s) may be fully buffered, so "finishes the buffered block" and "keeps going" would look the same.
3. Start it from LightBurn (or EZCAD). About **one minute in**, pull the USB cable at the Mac end. Time everything (phone video).
4. Watch the board's behaviour, then E-stop if it hasn't stopped within 3 s:
   - does marking stop at once;
   - does it finish a buffered block and then stop;
   - does it keep going;
   - is the beam left on at one point (a growing glowing dot)?
5. Repeat with: putting the Mac to sleep; force-quitting the app; pressing the E-stop mid-job (does USB drop? does the panel die?).
6. In the same session, **measure normal stop latency**: press Stop in LightBurn and time until marking ends. That number sets rule 18's timeout.
7. If a stop button is ever wired to the Stop Marking input (§6), repeat step 3 with the button: does the board halt on it with USB pulled, or only when the host is alive to read it?
8. Record the results in `03-machine.md` §12.

Whatever the outcome, Raio sends short lists and keeps the E-stop rule.

---

## 4. What went wrong before (the studio's own records)

| Date | What happened | Source | Lesson for Raio |
|---|---|---|---|
| 2026-05-11 | **90 mm lid in 2.5 mm Al: about 4 h of cutting, and it still would not release.** A residual under-cut arc was freed by hand. The field-edge angle and defocus starved the outer arcs. The lid workflow was replanned to mark, saw and sand. | `equipment/MACHINES.md`; `orbital-witnesses/logs/log.md` | Warn when a thick-stock cut leaves the central ~40 mm (`03-machine.md` §6). Long jobs need checkpoints. |
| 2026-05-11 | "Aluminium dust + heat + air = fire risk, never water on Al fire." | `MACHINES.md`, log.md l.1948 | Rule 12; a Class D extinguisher or sand at the machine. |
| 2026-05 (lid sprint) | Big lids cut at about 3 h each while other work ran ("Laser already cutting lids", the 12-hour parallel session). | `orbital-witnesses/logs/log.md` l.240, 289 | Rule 16: presence check. |
| 2026-08-18 | **FR4 coupon run 3: holes and cuts "went through, with fire and visible flame late in the job", heavy charring and soot plumes.** All at 100 % power, 200 mm/s. | `studio/trilha/COUPON-RUN-2026-08-18.md` | FR4 envelope; 2-min presence check; extraction required. |
| 2026-08-18 | Board lying flat on the **aluminium fixture**: the beam went through and **reflected back** off the fixture into the exit side; trapped resin burned. | same file, Run 5 | Lift work off reflective backing; a preflight item. |
| 2026-08-23 | **V3 board fell at pass 5–6 and the remaining passes fired into the loose board**, gouging it. Rule since then: "STAND AT THE MACHINE" for cutouts. | `studio/trilha/B6-PCB-RECIPE.md` | Rule 11: breakthrough checkpoint. |
| 2026-08-23 | A converter bug silently dropped 94 of 147 fill loops. Caught only by looking at the file in LightBurn before pressing Start ("two saves in one day"). | `B6-PCB-RECIPE.md` | The frame and preview must show the real geometry being sent. |
| 2026-09-21 | **Ring cut #1: settings changed mid-cut, and Z moved twice by hand without recording values.** The cut worked but couldn't be reproduced. | `orbital-witnesses/build/METAL-RING-LASER-CUT.md` | Rule 6: Z moves are logged checkpoints; parameters are locked during a run. |
| 2026-09-21 | The **Global Passes trap**: 10 × 100 = 1000 passes, warned in three files. | `MATERIAL-SETTINGS.md`, `METAL-RING-LASER-CUT.md`, README | Rule 10. |
| 2026-09-21 | Stainless "fast recipe" test performed clearly worse on a real ring (a ring's worth of time lost). | `MATERIAL-SETTINGS.md` | Envelope with "tested and rejected" zones. |
| Ongoing | The focus-direction sign check is still blank; the panel number is "relative". | `METAL-RING-LASER-CUT.md` | Rule 5; record the sign once. |

No eye or skin injury is recorded in the studio's files.

---

## 5. Operator pre-flight checklist (Raio shows it and blocks on it)

1. Goggles on: the right ones (§7), and everyone in the room.
2. E-stop within reach and released. Nothing on the floor between you and it.
3. Lens cap off; lens clean.
4. Material declared, and it is on the allowed list (not PVC, vinyl or unknown plastic).
5. Work clamped. Lifted off any reflective backing. Nothing flammable under the cut path or the perforated bed.
6. Polished copper or brass: scuffed matte, or accepted as a reflection risk. Curved polished parts: no one at eye level beside the machine.
7. Focus set; method and panel numbers entered.
8. Air assist on and aimed. Extraction on (required for stainless, brass, FR4 and plastics).
9. Fire kit at the machine: CO₂ extinguisher for general fire, Class D or dry sand for metal. No water near aluminium work.
10. Frame watched; the outline matches the part and sits inside the 150 mm field.
11. Pedal: off, unless the session is in pedal mode.
12. You will stay. Long jobs have checkpoints.

---

## 6. What a hardware interlock would need

The machine has the hooks, and none is used:
- the rear **Enclosure cable port**;
- LMC inputs that LightBurn calls **Door Protect** and **Stop Marking**;
- EZCAD "Stop Marking Input Port" and "Marking IO" output (`03-machine.md` §2, §10).

**Minimum:**
1. **A stop button on the bench**, normally closed, wired to an LMC input and configured as Stop Marking. **Assume it only works while the host software (Raio, LightBurn) is alive and polling it.** The EZCAD manual describes the Start and Stop inputs as things "the system detects", and gives no sign the board acts on them alone. Whether the board halts by itself is UNKNOWN; test it (§3, step 7). Which input pins are free, and their logic level, is also UNKNOWN. Map them with the EZCAD port monitor or LightBurn's port indicator boxes ([docs](https://docs.lightburnsoftware.com/2.1/Reference/DeviceSettings/GalvoPorts/)).
2. **A real emission cut that does not depend on software. This is the only stop that works when the Mac is dead.** The E-stop's wiring is UNKNOWN; test it first (`03-machine.md` §12 #3). If it only drops the controller, add a contactor or relay that removes the JPT's 48 V supply. That is the lead option. Some JPT DB25 tables label a line "emergency stop" (pin 23 is INFERRED, not traced to a source for our model). **This is internal wiring: power off and unplug before opening anything, and only after reading the source label.**
3. **An enclosure or curtain with a door switch** wired to the Door Protect input. With it, firing is refused while the door is open. ComMarker sells the "Safety Enclosure Pro" and an "OD6+" safety shield ([store](https://store.commarker.com/products/b6-jpt-mopa-fiber-laser-engraver)). The open frame is the single largest risk factor.
4. **Warning beacon.** Wire the "Marking IO" output to a light at the door, so anyone entering sees the laser is live.
5. **The foot switch as a dead-man**, not a start. The board's pedal input is a start trigger, so the pedal cannot act as a hold-to-run switch through the board. A true dead-man needs the hardware in point 2.

---

## 7. Eyewear

- **Minimum:** the JPT source manual requires **OD 4+ at 1064 nm** (WEB).
- **Recommended:** ComMarker sells an **OD 6+** shield for this machine. Choose goggles rated **OD 6+ at 1064 nm** that carry an **EN 207 marking covering pulsed operation at 1064**, not only D (continuous). Our source is Q-switched-like MOPA pulses up to 2 mJ, not CW.
- The OD numbers are taken from the manufacturers, not computed here.
- **The goggles in the box have no published OD** (WEB, store page). Read the marking on the frame. If there is no 1064 nm OD/EN 207 marking, do not rely on them.
- Green or clear lenses that look "dark enough" mean nothing at 1064 nm: the wavelength is invisible.
- Glasses protect against the beam, not against fumes or fire.

## 8. Fume extraction by material

| Material | Main hazard | Extraction |
|---|---|---|
| Stainless 304 | Cr(VI), Ni oxides (carcinogens) | Required. Vent outdoors, or HEPA + carbon at the source. Wait a few minutes before opening or leaning in. |
| Brass | Zinc oxide fume; lead if C360; fine dust | Required. HEPA. Clean the bed with a damp wipe, not compressed air. |
| Copper | Copper oxide fume | Required |
| Aluminium | Oxide dust; flammable fines | On. Keep the bed clear of dust (fire). |
| Anodised Al | Dye and sealant organics | Carbon stage |
| Galvanised | Zinc fume | Required |
| FR4 / PCB | HBr, brominated organics, glass fibre | Required, carbon + HEPA. Never at the "fire" settings. |
| PP / PE | Hydrocarbons, melt drips | On |
| ABS | Styrene, HCN | Required. Small jobs only. |
| PVC, vinyl, PTFE | HCl / chlorine; fluorine compounds | **Never** |

The extractor model, filter type and duct route are UNKNOWN (an open question in `equipment/b6-mopa.md`). Record them, and the filter change date.

## 9. Fire watch

- Never leave the machine running unattended (it is the manual's first rule). Raio enforces this with presence checks.
- Keep the bed and the area under the perforated plate free of debris and dust; the manual names accumulated residue as a fire source.
- After any FR4, card, wood or plastic job, watch for 2 minutes after the end for smouldering.
- If there is fire: Stop, then E-stop. Air assist **off** (it feeds flames). Extraction off if it is pulling flame into the duct. Smother. Class D or sand for metal fires; never water on aluminium.
