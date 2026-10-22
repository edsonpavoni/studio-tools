# 03 · The machine: ComMarker B6 MOPA 60 W

Research for **Raio**, the studio's own control tool for the B6 (it replaces LightBurn). This file covers the machine. Safety is in `04-safety.md`.
Written 2026-10-21. Every fact carries a tag:

- **VERIFIED**: read in the ComMarker manual, the EZCAD manual, the EZCAD config files that shipped on the B6 USB stick, the LightBurn prefs on this Mac, or the studio's own records.
- **WEB**: from a web page, with the URL given.
- **INFERRED**: a reasoned conclusion. Treat it as a hypothesis to test.
- **COMPUTED**: arithmetic on stated inputs.
- **UNKNOWN**: not found anywhere. Each one comes with a way to settle it.

Local sources, all under `0000 AI/studio/B6-Mopa/files/install/B6 MOPA/`:
- `Users' manual ComMarker B6.pdf` (cited as **[MAN]**). The web copy, `commarker.com/dist/js/uploads/Machines/BSeries/B6/Manual/B6UserManual.pdf` (**[MAN-WEB]**), is the same text plus a Maintenance chapter.
- `EZCAD software Manual.pdf` (**[EZM]**, the EzCad2UNI manual).
- `EZCAD for ComMarker B6 MOPA/plug/markcfg7` (**[CFG]**). This is the factory board configuration that LightBurn imports.
- `B6- Assembly Video.mp4`: 149.5 s (ffprobe). Not watched.

The LightBurn device profile is `~/Library/Preferences/LightBurn/prefs.ini` (**[LB]**), read 2026-10-21.

---

## 0. The answers that matter most

1. **The Z column is driven by its own lift controller, not by the laser board.** That controller is the touch panel on the head, a triangulation distance sensor, and a stepper on an 8 mm lead screw. No documented path lets a computer drive it.
   - Today it moves only by hand: the base buttons, the panel buttons, typing a Focal Length and pressing Auto, or the manual crank on top.
   - LightBurn cannot move it: EZCad2 Z control was pulled from LightBurn 2.1.
   - Raio can't drive it either until we find out how the panel's board talks. See §3.
2. **The depth of focus is short.** Theory gives about ±1.5 mm before fluence halves (§6). The studio's cuts behave as if it were tighter: 0.4 mm of defocus visibly slowed the stainless cut. Treat **±0.3 mm as the working tolerance for cutting** until a ramp test measures it.
3. **Frequency has a hard maximum per pulse width and a soft "full-power" cutoff, not a hard minimum.** Below the cutoff, energy per pulse stops rising and average power falls (§5). Raio must only offer the source's discrete pulse widths and must clamp frequency to that width's maximum.
4. **The foot pedal is live under LightBurn and EZCAD.** Input 14 is set as "Start Mark" in both the factory config and LightBurn, so a pedal press starts the loaded job while either program is connected. The host polls the input, so under Raio the pedal does nothing unless Raio implements it (INFERRED) (§2, §9).
5. **No door or stop input is configured.** There is no enclosure. The rear "Enclosure cable port" is the hook for an interlock (§2, `04-safety.md`).

---

## 1. Spec sheet

| Item | Value | Tag / source |
|---|---|---|
| Model | ComMarker B6 MOPA, 60 W, JPT MOPA source | VERIFIED: studio `B6-Mopa/README.md`; [MAN] spec table |
| Laser source | JPT M7 series MOPA, 60 W. The product page names "JPT MOPA"; resellers name it YDFLP-(E-)60-M7-M-R. **The studio has not read the label on its own source.** | WEB: [store page](https://store.commarker.com/products/b6-jpt-mopa-fiber-laser-engraver); UNKNOWN for our unit. Read the source label. |
| Wavelength | 1064 nm, invisible | VERIFIED [MAN] |
| Frequency | 1–4000 kHz | VERIFIED [MAN]; LightBurn Min 1 / Max 4000 kHz [LB] |
| Pulse width | 2–500 ns, discrete steps (§5) | VERIFIED [MAN] for the range; WEB for the list |
| Max pulse energy | 2 mJ (60 W MOPA) | VERIFIED [MAN]. One ComMarker blog says 1.5 mJ; the product page and manual both say 2 mJ. |
| Beam quality | M² < 1.4 (the "M" suffix means near single-mode) | WEB: [JPT M7 manual excerpt](https://pdfcoffee.com/ydflp-6-v1-pdf-free.html), [Haotian](https://haotianlasers.com/product/fiber-laser-60w-jpt-m7-m/) |
| Collimated beam at source output | 7.0 ± 0.5 mm | WEB: Haotian (same source family). Whether the B6 head adds a beam expander is UNKNOWN. |
| Red pilot laser | Built into the source ("R" suffix) | WEB (JPT naming convention) |
| 0 % power emission | About 100 mW average **while emission is on** at 0 % setting | WEB: JPT M7-M-R manual safety page (pdfcoffee link above) |
| Source supply | 48 V DC, more than 6 A | WEB (JPT manual, Haotian). The external power brick in the box is INFERRED to be 48 V. |
| Cooling | Air, fans | VERIFIED [MAN] |
| Operating temperature | Machine: 10–28 °C best; outside that range "the laser may stop working" [MAN]. Machine spec: 5–35 °C, humidity ≤ 70 % [MAN]. Source: internal alarm outside 0–40 °C [JPT]. | VERIFIED / WEB |
| Mains | 110–130 V or 200–240 V; supply fluctuation < 5 %; must be grounded | VERIFIED [MAN] |
| Lens | F-Theta, f = 210 mm, λ 1064 nm, "sl: 150×150 mm" (read off the lens) | VERIFIED: `studio/equipment/MACHINES.md` 2026-05-10 |
| Field (configured) | **157.5 × 157.5 mm** in both [CFG] (`FIELDSIZE=1.575e2`) and [LB] (Width/Height 157.5) | VERIFIED. See §11 contradiction 1. |
| Correction file | `jcz15.cor`, 33,840 bytes, md5 `be209d694f845bfbf47aa92c2bd8b4fd` | VERIFIED (local copy in the install folder) |
| Galvo | Model not published. Galvo 2 is X (`Galvo_1_is_X: false` [LB]; `GALVOX=1` [CFG]) | VERIFIED for the axes |
| Max marking speed | 15,000 mm/s (marketing). LightBurn MaxSpeed is set to 7000 [LB]. | WEB / VERIFIED |
| "Spot 0.015 mm" | **Physically impossible** at f = 210 mm with a 7 mm beam (§6). Ignore it. | WEB claim; COMPUTED rebuttal |
| Laser class | Class 4 as used here (open frame). "Class 1" applies only inside the optional Safety Enclosure Pro. | VERIFIED [MAN] "Class IV"; WEB store page |
| Size / weight | 53 × 43 × 24 cm; 13.5 kg | VERIFIED [MAN] |
| Controller | BJJCZ (JCZ) LMC USB board, EZCad2 generation. It enumerates as `USBLMCV2` or `USBLMCV4` and installs as "BJJCZ Device". The software shipped is EzCad 2.14.11. | VERIFIED [MAN] pp.7–10 |

---

## 2. Every control and port

From [MAN] p.2 (the product-structure drawing) and p.3 (list of items):

| Control / port | Where | Function | Tag |
|---|---|---|---|
| **Switch** (power) | Base, front | Hold about 1 s before the machine starts | VERIFIED [MAN] p.5 note |
| **Emergency stop switch** | Base, front, left | Mushroom stop. **What it cuts is UNKNOWN.** The driver-install step requires it to be released, which suggests it de-powers the controller (INFERRED). Test: at idle, press it and see whether the BJJCZ USB device disappears and the panel goes dark. | VERIFIED presence; INFERRED behaviour |
| **Breathing light** | Base, front | Status LED, slow pulse. Meaning of its states is not documented. | VERIFIED presence |
| **Up / Down** buttons | Base, front, right | Raise or lower the head on the column. This is the lift controller, not the LMC board (§3). | VERIFIED [MAN] |
| **Auto focus touch screen** | On the laser head, facing the operator | Up / Auto / Down page, plus a Setting page (Speed, Screw Pitch, Pulse Count, Focal Length, Real Focal Length, Send Focus, OK, Stop, EN/中). The manual labels this "Only for B6 Pro", but **our B6 MOPA has it**: the panel is quoted in `METAL-RING-LASER-CUT.md`. | VERIFIED [MAN] pp.2, 11–12; local record |
| **Manual lifting** | Top of the column | Knob or crank that turns the lead screw by hand | VERIFIED [MAN] p.2 |
| **Galvanometer scanner + field lens** | Head | The plastic lens cap **must be removed** before firing, or the beam burns it onto the lens | VERIFIED [MAN] p.4 |
| **Auto focus cable port** | Column (low) **and** base (rear) | Type-C cable joining the column to the base. The manual requires it to be connected even to install the USB driver. | VERIFIED [MAN] pp.2, 7 |
| **Data cable** | Base, rear | USB to the computer (LMC board) | VERIFIED |
| **Power cable port** | Base, rear | DC in from the external adapter | VERIFIED |
| **Rotary device port** | Base, rear | Aviation connector, out to the "Rotary Drive" box (a stepper driver) and then to the R5 | VERIFIED presence; pinout UNKNOWN (§7) |
| **Pedal port** | Base, rear | Foot switch. **Configured as Start Mark, input 14** in [CFG] (`STARTMARKPORT=14`, `ENSTARTMARKSIGNAL=1`, `STARTSIGNALPULSEMODE=1`) and [LB] (`StartMarkPortBit: 14`, `StartMarkPulseMode: true`). Pressing it starts the job while LightBurn/EZCAD is connected and polling the input. | VERIFIED |
| **Enclosure cable port** | Base, rear | For the optional ComMarker enclosure's door sensor ("Door sensor (with enclosure only)", store page). Nothing is connected. **No door input is configured**: `DOORINPORT=-1` [CFG], `DoorProtectPortBit: -1` [LB]. | VERIFIED / WEB |
| Key switch | — | **None.** None is shown in the manual or listed on the store page. | VERIFIED (absence in [MAN]) |
| Air assist | — | **Not part of the machine.** The studio uses its own external air nozzle. Which compressor or pump, and at what flow, is not recorded. | VERIFIED absence; UNKNOWN details |
| Fume extraction | — | Not included (sold as a bundle). Which extractor the studio uses is an open question in `equipment/b6-mopa.md`. | UNKNOWN |

In the box ([MAN] p.3): goggles (no OD printed in the manual), a ruler (for the focus check), a "placing helper" (L-square), paperboard, a test steel disc, a riser (+~15 cm for big objects or the rotary), the Rotary Drive box, the foot switch, two OTG adapters, and the USB stick.

**The DB25 is not a user port.** It sits inside the base, between the LMC board and the JPT source (§8).

---

## 3. The Z column

| Question | Answer | Tag |
|---|---|---|
| Drive | Stepper on a lead screw. **Screw pitch 8 mm, 200 pulses per revolution, speed 12.5 mm/s.** These are the "optimized parameters adjusted by the manufacturer". The studio's panel shows the same: Speed 12.5, pitch 8, pulse count 200. | VERIFIED [MAN] p.12; `METAL-RING-LASER-CUT.md` |
| Resolution | 8 mm ÷ 200 = **0.04 mm per pulse**, if "pulse count" means pulses per revolution as the manual says. Any hidden microstepping in the driver would change this. | COMPUTED from VERIFIED inputs |
| Time per mm | 1 mm ÷ 12.5 mm/s = 0.08 s | COMPUTED |
| Who drives it | **The lift/autofocus controller behind the touch panel.** Its parameters are "stored by the control board" when you press OK on the panel, which means a board other than the LMC. | VERIFIED [MAN] p.12 |
| Height sensor | Triangulation distance sensor ("Z-height measurement by triangulation", store page). It works only from **120 to 280 mm**; outside that window a warning pops up and you must move the head by hand. The sensor is **not at the centre of the field**: the material must sit under the sensor's red dot when you press Auto. | VERIFIED [MAN] pp.10–11; WEB store page |
| Auto | Moves the head so that the sensor reads the stored "Focal Length". "Send Focus" copies the live "Real focal length" into "Focal Length". | VERIFIED [MAN] p.12 |
| Studio values | Focal Length **234 mm** (nominal). Real focal length read **255.15 mm** during the 2026-09-21 ring cut. A forum B6 owner found 233 mm correct; their factory setting was 182. | VERIFIED local; WEB [forum](https://forum.lightburnsoftware.com/t/commarker-b6-60w-mopa-initial-set-up/189402) |
| Travel | **UNKNOWN.** Not published. The 120–280 mm sensor window is not a travel limit. The column plus the 15 cm riser gives about 300 mm maximum object height (reseller). Do not use Haotian's "500 mm Z" figure; that is a different machine. | UNKNOWN; WEB (reseller) |
| Limit switches / home | **None documented.** The lift has no home routine; it positions by the distance sensor. Whether hard end-stops or switches exist is UNKNOWN. Assume none, so a runaway Down command can drive the lens into the work. | UNKNOWN; INFERRED risk |
| mm per button press | **UNKNOWN.** The manual text is ambiguous ("continuously go up when pressing the button when tapping the button"). It suggests a tap starts continuous motion and Stop ends it. Measure with a dial indicator: tap and hold, record mm. | UNKNOWN |
| Can software drive it today? | **No.** LightBurn: Z control for EZCad2 galvos was in 2.1 release candidates, then pulled ("not yet ready to go live"). LightBurn staff, October 2025: per-pass Z "requires re-architecting the sender". Even where LightBurn has Z (EZCad3), it drives a motor on the **board's** axis output. The B6 lift is not on that output. | WEB: [NewIn2.1](https://docs.lightburnsoftware.com/2.1/NewFeatures/NewIn2.1), [Z control thread p.9](https://forum.lightburnsoftware.com/t/z-control-for-galvo/161991?page=9), [B6 Z thread](https://forum.lightburnsoftware.com/t/dropping-z-per-pass-on-commarker-b6/169851) |
| The axis in [CFG] | `ACTIVEAXIS0=1`, `AXISROTATE0=0` (linear), `AXISSTEPPERRO0=200`, `AXISDISTPERRO0=5` mm/rev, no zero switch, range ±1000. **This is not the column**: a 5 mm/rev pitch doesn't match the column's 8 mm. It is the board's generic extension-axis default, wired to the Rotary port. | VERIFIED values; INFERRED meaning |
| Focus sign | Physics: to put the focal plane **into** the material (deeper), the head goes **down**, so the distance gets shorter and you **lower** Focal Length. The studio's sign check in `METAL-RING-LASER-CUT.md` is still blank ("write the direction here: ___"). | INFERRED. Do the 0.4 mm check once and record it. |

**How it is commanded today:** by hand. Use the base Up/Down, the panel Up/Auto/Stop/Down, or type a Focal Length and press Auto. The studio's "Z staircase" (the 2.5 mm Al recipe: 150 passes, drop 1.0 mm, 50 more) was done by stopping the job, moving Z on the panel, and restarting. `MACHINES.md` says it: "LightBurn+B6 has no automatic Z-step but manual focus entry on the laser panel is quick."

**Three tests settle whether Raio can ever drive Z:**
1. With the B6 on and connected, run `ioreg -p IOUSB -l -w 0` (or `system_profiler SPUSBDataType`). Does anything enumerate besides the BJJCZ device, such as a CH340, CP210x or HID device from the panel board? Nothing was connected when this was checked on 2026-10-21.
2. Unplug the column-to-base Type-C. Does the panel still work, and does the LMC still enumerate? This shows whether that cable carries only lift power and signals, or data too.
3. Email support@commarker.com and ask for the lift board's protocol, or for a Z input (STEP/DIR) on the panel board.

If none of these opens a door, the fallback for software-controlled Z steps is the Rotary port. It drives an external stepper on the board's extension axis. LightBurn forum users do exactly this (a motorized lift table or a raising work stage). In Raio it would be a job-split step move between pass blocks, not a move during marking.

---

## 4. The rotary port

- **Chain (VERIFIED, `R5-ROTARY.md` + [MAN] list of items):** B6 rear "Rotary device port" → "Rotary Drive" box (a stepper driver) → R5. The R5 is a 2-phase stepper set to 12,800 steps/rev (WEB, LightBurn forum, cited in `R5-ROTARY.md`).
- **Pinout: UNKNOWN.** ComMarker does not publish it.
  - Generic JCZ LMCV4 board side: DB15 "CON4" pin 14 = direction, pin 15 = pulse, both powered from the 24 V the board uses. The same page puts the foot pedal on pins 9 and 12. WEB: [Peter Verdone](http://www.peterverdone.com/laser-accessories/). That is the board header, not the B6's round connector.
  - To map the round connector, use a multimeter: the constant +24 V pin, the pin that toggles with jog direction (DIR), and the pin that pulses during a jog (PUL). This is the plan already in `R5-ROTARY.md`.
- **Software side:** EZCad2 "expansion axis" parameters in [EZM] §8: pulses per round, min/max speed, accel time, zero switch, "go to start position after finished". The [CFG] defaults are listed in §3.

---

## 5. The laser source: pulse widths, frequencies, energy

**How a MOPA trades frequency against pulse energy.** For each pulse width there are two numbers:
- **Max frequency.** Duty-cycle limit, a hard ceiling.
- **Cutoff frequency.** Above it the source delivers full 60 W average power. Below it, **peak power is held, energy per pulse stops growing, and average power falls.**

So there is **no per-width minimum frequency** other than the global 1 kHz. Going below the cutoff does not alarm the source; it wastes average power. This corrects the brief's premise.

Pulse-width/frequency table for the 60 W M7. **WEB**: a reseller's transcription of the JPT M7 manual, [Haotian 60 W M7-M](https://haotianlasers.com/product/fiber-laser-60w-jpt-m7-m/), not a JPT datasheet. The last two columns are COMPUTED.

| Pulse width | Full power from (cutoff) | Max frequency | Max energy per pulse (= 60 W ÷ cutoff) | Approx. peak power (energy ÷ width) |
|---|---|---|---|---|
| 2 ns | 1950 kHz | 4000 kHz | 31 µJ | ~15 kW |
| 4 ns | 1350 kHz | 4000 kHz | 44 µJ | ~11 kW |
| 6 ns | 975 kHz | 4000 kHz | 62 µJ | ~10 kW |
| 9 ns | 600 kHz | 4000 kHz | 100 µJ | ~11 kW |
| 13 ns | 412 kHz | 3000 kHz | 146 µJ | ~11 kW |
| 20 ns | 225 kHz | 3000 kHz | 267 µJ | ~13 kW |
| 30 ns | 187 kHz | 3000 kHz | 321 µJ | ~11 kW |
| 45 ns | 150 kHz | 2000 kHz | 400 µJ | ~9 kW |
| 60 ns | 135 kHz | 2000 kHz | 444 µJ | ~7 kW |
| 80 ns | 112 kHz | 2000 kHz | 536 µJ | ~7 kW |
| 100 ns | 105 kHz | 1000 kHz | 571 µJ | ~6 kW |
| 150 ns | 57 kHz | 1000 kHz | 1.05 mJ | ~7 kW |
| 200 ns | 45 kHz | 1000 kHz | 1.33 mJ | ~7 kW |
| 250 ns | 42 kHz | 900 kHz | 1.43 mJ | ~6 kW |
| 350 ns | 40 kHz | 600 kHz | 1.50 mJ | ~4 kW |
| 500 ns | 30 kHz | 500 kHz | 2.00 mJ | ~4 kW |

Peak power assumes a square pulse. Real MOPA pulses have a leading spike, so treat these as order-of-magnitude figures. The 500 ns row matches the manual's 2 mJ maximum (60 W ÷ 30 kHz), which is a useful cross-check.

**Sources disagree on the waveform list (flag):**
- The M7-M table above has 2, 4, 6, **9, 13**, 20, … 500 ns.
- The JPT M7-**L1** manual lists CW, 2, 4, 6, **8, 12**, 20, 30, 45, 60, 80, 100, 150, 200, 250, 350, 500 ns ([pdfcoffee](https://pdfcoffee.com/ydflp-6-v1-pdf-free.html)).

**Out-of-range pulse width (flag):** JPT manuals say the source accepts only its listed widths. One version says an unlisted value gives "the close pulse width value" ([forum](https://forum.lightburnsoftware.com/t/mopa-q-pulse-and-lightburn-material-test/104576)). Another says it "uses the default pulse width set last time" ([C-30-M7 manual p.17](https://www.manualslib.com/manual/2963603/Jpt-Ydflp-M-Series.html?page=17)). **The second means a typo can silently run the previous job's pulse width.**

What it means for Raio:
- Offer only the discrete widths.
- Freeze the list once the source label is read.
- Clamp frequency to that width's maximum.
- Show the energy per pulse and average power that the chosen pair really delivers.

**What the studio's recipes actually deliver (COMPUTED, using the table):**

| Recipe | Setting | Below cutoff? | Energy/pulse | Average power |
|---|---|---|---|---|
| Copper engrave (LOCKED) | 20 kHz, 350 ns | yes (cutoff 40) | 1.5 mJ | **30 W** (half power) |
| Copper cut 1.1 mm (LOCKED) | 75 kHz, 500 ns | no | 0.8 mJ | 60 W |
| Al cut 1.1 mm (LOCKED) | 65 kHz, 350 ns | no | 0.92 mJ | 60 W |
| Stainless 1.6 mm (PROVEN) | 20 kHz, 500 ns | yes (cutoff 30) | 2.0 mJ | **40 W** |
| PCB (all layers) | 40 kHz, 200 ns | yes (cutoff 45) | 1.33 mJ | 53 W |
| Copper 6 ns test (failed) | — | — | ≤ 62 µJ | — explains "marked nothing" |

This refines the studio's lesson "20 kHz = max pulse energy" (`B6-Mopa/README.md`). It holds for 500 ns, where the cutoff is 30 kHz. At 350 ns the energy is already maxed at 40 kHz, so 20 kHz only halves the average power.

**Other source facts:**
- **Warm-up / MO before PA (WEB, JPT C-30-M7 manual p.13):** the emission signal (PA) is accepted only after the source has been powered **12 s** and MO (master oscillator) is high. LightBurn's "Open MO Delay" is 8000 [LB], and EZCAD's `m_nIPGOpenMoDelayTimeMs=8` [CFG]. Raio must not start emission inside the first 12 s after the machine powers on.
- **Alarm (WEB, same manual):** DB25 pins 16 and 21. 16 low + 21 high = normal; 16 low + 21 low = temperature alarm. Whether the B6 wires these to an LMC input is UNKNOWN. [CFG] has `m_nAlarmOutport=-1` and `m_nEnableFiberLaserStateCheckInMarking=0`, so no state check is configured.
- **"Laser ready" signal:** not configured (`m_nLaserReadyInport=-1` [CFG]).
- **Fiber:** keep the bend **diameter > 15 cm** at all times (WEB, JPT M7 manual §1.3.2). It matters when mounting the riser or moving the head.
- **Cooling:** fans scale with ambient temperature. Keep 10 cm clear in front of and behind the source (inside the base, so don't block the base vents) (WEB, same).
- **Lens material:** JPT recommends fused silica over K9 glass because K9 lenses suffer thermal lensing and focus drift at high power. Our lens's glass is UNKNOWN (WEB, same).

---

## 6. Lens, field, working distance, depth of focus

**Field.** The lens is marked 150 × 150 mm; the config says 157.5 (see §11). The scan angle is θ ≈ r / f (COMPUTED):

| Where | r | θ |
|---|---|---|
| Field edge, mid-side | 75 mm | 75 / 210 = 0.357 rad ≈ **20°** |
| Corner | 106 mm | ≈ 29° |
| 90 mm lid edge | 45 mm | ≈ 12° |

F-theta lenses are **not telecentric**: the beam meets the work at that angle.

**Why big cuts in thick stock fail (COMPUTED).** In a kerf of width w, a beam tilted by θ hits the near wall after depth d ≈ w / tan θ.

| Where | Kerf w | θ | Shadowed after |
|---|---|---|---|
| 90 mm lid, 2.5 mm Al (the 4-hour cut) | 0.30 mm | 12° | ~1.4 mm, well short of 2.5 mm |
| Field edge | 0.30 mm | 20° | ~0.8 mm |

This is the mechanism behind "past ~40 mm diameter in thick stock the field edge slows and spoils cuts" (`equipment/b6-mopa.md`). **Rule: cut thick parts small and centred.**

**Working distance.** The panel's Focal Length (234 mm) is measured from the **sensor**, not the lens. The manual's "bottom line of the head to the surface" values are left blank for the owner to fill in [MAN] p.10. **UNKNOWN for our unit.** Measure it once with the supplied ruler at true focus and record it.

**Spot size and Rayleigh range (COMPUTED).** Assumptions:
- Gaussian beam, λ = 1.064 µm, f = 210 mm.
- 1/e² beam diameter D at the lens = 7.0 mm (the source's output; assumes **no beam expander** in the head).
- M² = 1.3–1.4.

Formulas: w₀ = M² λ f / (π D/2), z_R = π w₀² / (M² λ), w(z) = w₀ √(1 + (z/z_R)²), relative peak fluence = (w₀ / w(z))².

| D | M² | Spot Ø (2w₀) | z_R | Fluence halves at |
|---|---|---|---|---|
| 7.0 mm | 1.4 | 57 µm | 1.71 mm | ±1.7 mm |
| 7.0 mm | 1.3 | 53 µm | 1.59 mm | ±1.6 mm |
| 7.5 mm | 1.3 | 49 µm | 1.38 mm | ±1.4 mm |
| 8.0 mm | 1.3 | 46 µm | 1.21 mm | ±1.2 mm |

Fluence vs defocus, for D = 7 mm, M² = 1.4:

| Defocus | Fluence |
|---|---|
| ±0.4 mm | 95 % |
| ±0.5 mm | 92 % |
| ±1.0 mm | 74 % |
| ±2.0 mm | 42 % |
| ±3.0 mm | 25 % |

Even with M² = 1 the spot would be ~40 µm, so ComMarker's "0.015 mm spot" is not possible with this lens.

**The mismatch (do not smooth over it).** The studio's evidence says focus is more critical than this table:
- The ring slot with its ends ~0.4 mm out of focus cut "far slower" (theory: −5 % fluence).
- On 2.5 mm Al, flat focus would not penetrate at all, and a 1.0 mm drop was "essential" (theory: −26 %).

Possible reasons:
- (a) The beam at the lens is wider than 7 mm (an expander), giving a shorter z_R.
- (b) Cutting runs near an ablation threshold, so a small fluence loss costs a large share of the removal rate.
- (c) On the ring, the surface tilts away along with the defocus.

**Practical number for Raio until measured: ±0.3 mm for cutting, ±1 mm for marking.**

**Ramp test that settles it (≈10 min).**
1. Lay a flat stainless plate on a known wedge: about **6 mm of rise over 100 mm**, centred on the current focus (so the line spans about ±3 mm, past both √2 points).
2. Mark one straight line up the slope at fixed settings.
3. Measure line width and darkness against height.
4. The height of the narrowest point is true focus. The heights where width grows by √2 give z_R.

**Why deep cuts need Z stepping.** The focal plane stays put while the kerf floor goes down. After cutting 1 mm deep, the floor sits 1 mm below focus, so fluence there is about 74 % (more if (a) or (b) above is true). Material removal per pass falls, then stalls. Lowering the head by roughly the depth already removed puts focus back on the floor. Hence the studio's "150 passes at 0 → drop 1.0 mm → 50 passes" for 2.5 mm Al.

---

## 7. Focusing procedures

1. **Autofocus (our machine):** put the material **under the sensor's red dot** (not the field centre) and press **Auto**. The head moves until the sensor reads the stored Focal Length (234). Then you may move the material [MAN] p.10.
   - It fails on curved, tiny or off-centre parts, where the sensor sees the vise or the bed.
   - That is the likely reason the ring cut read 255.15 rather than 234 (INFERRED). **Raio must never trust the panel number on such setups.**
2. **Two red dots (B6 without panel):** press Up/Down until the two red light points overlap; that is focus [MAN] p.10.
3. **Ruler:** measure from the bottom line of the head to the surface. The value per lens is left blank in the manual for the owner to fill in [MAN] p.10.
4. **Studio method for cuts:** focus by eye on the surface at the cut, judged by the sharpest red/ablation spot. Then keep the method constant; "treat the panel number as relative" (`MATERIAL-SETTINGS.md`). Cutting speed is the tell: in true focus a cut goes through in a fraction of the passes.

---

## 8. Red light, connections, DB25

- **Red light.** The JPT's built-in red pilot goes through the same galvos and lens. EZCAD "Red (F1)" or LightBurn Frame traces the outline (`REDLIGHTSPEED=3000`, `FrameSpeed: 3000`). No GPIO is used for it (`RedLightPortBit: -1`), so the board drives it through the laser interface (INFERRED). On the JPT DB25, pin 22 high = red beam on and internally forces MO/PA off (WEB, JPT LP manual search excerpt).
  - **The red dot shows where the beam goes, not where it is in focus.** The focus aid is a separate pointer (B6) or the sensor (panel).
  - LightBurn reports one B6 60 W MOPA board signature, `0000238409002002`, as "unrecognized". On that board framing draws a single straight line instead of the outline (May 2026, LightBurn 2.0.05 and 2.1 RC). WEB: [thread](https://forum.lightburnsoftware.com/t/czfiber-unrecognized-board-signature-0000238409002002-framing-broken-on-commarker-b6-60w-mopa/189558). Our board's signature is UNKNOWN; read it in EZCAD → Param → HardInfo, or from LightBurn's console.
- **USB:** one cable, LMC board, libusb on macOS (`"Type": "LibUSB"` [LB]).
- **Foot switch:** see §2. Input 14, pulse mode.
- **DB25 (internal, LMC ↔ JPT).** It is not exposed, and this pinout comes from **other** JPT M7 models (WEB, [C-30-M7 manual p.13](https://www.manualslib.com/manual/2963603/Jpt-Ydflp-M-Series.html?page=13) and JPT LP manual excerpts):

| Pin(s) | Signal |
|---|---|
| 1–8 | Power, 8-bit TTL (0–255 = 0–100 %) |
| 9 | Latch (rising edge) |
| 10–15 | GND |
| 16, 21 | Alarm |
| 18 | MO (master oscillator enable) |
| 19 | PA / emission (high = on) |
| 20 | PRR (pulse repetition frequency, TTL) |
| 22 | Red guide |
| 23 | "Emergency stop" on some models (INFERRED; not traced to a source for our model) |

The pulse width is written as a command over the same interface (a 0xA5 0x01 + 16-bit width instruction in the C-30 manual). Logic levels: high 4.6–5.4 V, low < 0.5 V. Raio talks to the LMC over USB, not to this connector. It matters only for an emergency-stop retrofit (`04-safety.md`).

---

## 9. LightBurn device settings in use (VERIFIED, [LB] 2026-10-21)

There are **two** device entries named `JCZFiber`. The first is displayed as "B6 Mopa" and is the default. Settings of entry 1:

| Setting | Value |
|---|---|
| Field | 157.5 × 157.5; offset 0; angle 0 |
| COR | `…/B6 MOPA/EZCAD for ComMarker B6 MOPA 2/jcz15.cor` in an old Dropbox folder. **This path no longer exists** (checked 2026-10-21). Entry 2 points at another dead path. |
| Galvo | Galvo 1 is X = false (so Galvo 2 is X); signs +1; scales 1; bulge/skew/trapezoid 1 |
| Laser | Type 1 (Fiber); FiberType 1 (the enum's meaning is not documented; the manual says choose "IPG_YLP" or "JPT"); PWM on |
| Frequency | Min 1 / Max 4000 kHz |
| Q-Pulse | Q-Pulse Width enabled |
| MO | Open MO Delay 8000; OscillatorOnDemand false |
| Tickle | `Laser_TickleEnable: true` (a CO2-only setting; INFERRED harmless for fiber, but odd) |
| Timing defaults | LaserOn TC −300, LaserOff TC 100, End TC 300, Polygon TC 100, Jump speed 4000, jump delays 500 |
| Speeds | Frame speed 3000; MaxSpeed 7000 |
| Ports | Start Mark = **14** (high, pulse mode); Stop Mark −1; Door Protect −1; Red light −1; Ready/Busy/Done −1 |
| Safety options | **Require Framing Before Start = true**; Job checklist = false |
| Cut library | `LastDevLibraryPath` → an old Dropbox `.clb`. **Dead path.** A copy is kept in the studio's B6 folder. |

The ComMarker setup instructions ([MAN] pp.13–15) say: import `markcfg7`, load `JCZ15.cor`, set Freq min 1 / max 4000 (MOPA), turn on Galvo 2 and "Enable Q-Pulse Width", and set the fiber type to IPG_YLP or JPT. The LightBurn version is Pro 2.1.04 (`B6-Mopa/README.md`).

---

## 10. The EZCAD board identity (VERIFIED, [CFG] `markcfg7`, dated 2025-04-24)

- `LASERTYPE=3` (fiber); `ENPWMOUT=1`; PWM range 1 kHz–4 MHz; `m_bEnableIPGSetPulseWidth=1` (pulse width set through the laser interface).
- `ENFPK=1, FPK=40`; `ENPWMTICK=1`.
- `CORFILE=G:\…\jcz15.cor`, `ENABLECORFILE=1`.
- `STARTMARKPORT=14` with `ENSTARTMARKSIGNAL=1` (the pedal), `DOORINPORT=-1`, `STOPIOHIGH=0 / STOPIOLOW=0` (no stop input), `LASERPOWERPORT=-1`, `m_nLaserReadyInport=-1`, `m_nAlarmOutport=-1`.
- Extension axis 0 active, linear, 200 steps / 5 mm, no zero switch (§3).
- `TOTALPARTNUM=161252` and `MARKTOTALTIME=22419` s, about 6.2 h of factory marking time on the source unit the file came from (INFERRED: factory test history, not our machine's).
- **The board model string (LMCV4-FIBER-M) is not in any local file.** `R5-ROTARY.md` calls it "confirmed" without a source. Read the board type, version and SN from EZCAD → Param (F3) → HardInfo [EZM] §10.4.5.
- **EZCAD's own safety-relevant features** ([EZM] §10.4.3–10.4.4), all currently off:
  - "Stop Marking Input Port": an input that ends a running job.
  - "Show start mark dialog": asks before every mark.
  - "Red light pointer I/O".
  - "Marking IO": an output that is high while marking, usable for a warning beacon.
  - "Test laser" fires for a set time at a set power. **This is a hazard** (`04-safety.md`).

---

## 11. Where local records and the web or the files disagree

1. **Field 157.5 vs lens 150.** The studio note says "recalibrate LightBurn to 150". **Do not change it without a measured calibration square.** With this `.cor`, at 157.5:
   - 2.54 mm header pins seat in the PCB holes;
   - the ring slot's kerf came out right with zero offset.

   Dropping to 150 would shrink every part by 4.8 %, **if** LightBurn's field size sets the scale while a COR is loaded. `CorScaleOverride: false` may mean the COR's own scale wins instead (INFERRED either way). The right fix is to cut a 100 mm square, measure it, and adjust only if it's off. Separately, keep cuts inside the 150 mm corrected area.
2. **"20 kHz = max pulse energy"** is true only for 500 ns. At 350 ns the cutoff is 40 kHz, so the LOCKED copper engrave (20 kHz/350 ns) runs at about 30 W average (§5). Not wrong, but incomplete.
3. **Dead paths.** Both LightBurn COR paths and the cut-library path point to folders that no longer exist. Check in Device Settings that a COR is actually loaded (LightBurn may have cached it). Re-point it to the local copy (md5 above).
4. **Panel 234 vs 255.15.** Probably the off-centre sensor reading the vise or bed, not the ring. The panel number is relative.
5. **The manual's "B6 Pro" vs our "B6 MOPA".** Our MOPA has the panel and sensor that the manual attributes to the Pro. Use the Pro instructions.
6. **ComMarker's "0.015 mm spot"** vs a computed ~50 µm.
7. **"Class 1"** (store page) applies only inside the optional enclosure. We have none, so the machine is **Class 4**.
8. **Pulse-width list** (9/13 vs 8/12 ns) and the out-of-range behaviour ("closest" vs "last used"): see §5.
9. **Board model** asserted in `R5-ROTARY.md` without a source.
10. `MATERIAL-SETTINGS.md` still calls its home `tools/B6-Mopa/`. It lives at `studio/B6-Mopa/`.

## 12. Open measurements (each settles an UNKNOWN above)

| # | Measurement | Settles |
|---|---|---|
| 1 | Read the JPT source label (model, serial) | §1, §5 |
| 2 | EZCAD HardInfo: board type, version, SN | §10 |
| 3 | E-stop at idle: does USB drop and the panel go dark? | §2 |
| 4 | Lift: tap-and-hold travel per press, full travel top to bottom, presence of end-stops | §3 |
| 5 | USB enumeration and the column Type-C test | §3 |
| 6 | Working distance, lens bottom to work, at true focus | §6 |
| 7 | Focus ramp test | §6 |
| 8 | 100 mm calibration square | §11.1 |
| 9 | Rotary port pinout by multimeter | §4 |
| 10 | The included goggles' OD/EN 207 marking | `04-safety.md` |
