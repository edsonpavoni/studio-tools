# Coupon run 1 — 2026-08-18

**First time the recovered recipe met copper.** Read from the photographs of the front,
the back, and the board still in the fixture.

⚠️ **Two facts still needed from the bench before this is fully interpretable:**
which interval file was run (`-i0p1` or `-i0p02`), and the FR4 thickness.

---

## What happened, layer by layer

| Layer | Expected | What the copper shows | Verdict |
|---|---|---|---|
| **Moats** (Fill, 95 %, 200 mm/s) | clean isolation gaps | **all 8 widths cut, in all 3 blocks** | ✅ **worked, and better than hoped** |
| **6 mm field** (same settings) | copper removed, FR4 intact | **burned clean through the FR4**, deep crater, heavy soot plume | ❌ **catastrophic overshoot** |
| **Holes** (Line, 100 %, 40 mm/s, 8 passes) | 6 sizes through | small ones marked, only some through; **6.6 mm barely scribed** | ❌ **far too little** |
| **Cutout** (Line, 100 %, 40 mm/s, 12 passes) | board released | **scribed only, board intact** | ❌ **far too little** |

## The headline

**The same settings are simultaneously five times too hot for an area fill and nowhere
near hot enough for a cut.** That is not a recipe needing a tweak, it is two different
jobs that were sharing one set of numbers because the 2025 file made them look alike.

## Why the field burned and the moats did not

A moat is thin, so the copper on either side conducts the heat away. A 6 mm field has no
such neighbour: the first scan lines strip the copper, and every line after that lands on
**bare FR4, which absorbs 1064 nm far better than copper does and has nowhere to dump the
heat.** The fill does not stop when the copper is gone. It keeps going until it is through
the board.

This is the single most important thing the coupon taught, and it reframes the strategy:

> **Clearing the whole copper field, the way the 2025 board looks, is the expensive and
> dangerous way to make a board on this machine. Cutting isolation moats and leaving the
> surrounding copper in place is electrically identical, enormously faster, and the coupon
> just proved the moats come out clean at every width from 0.10 to 0.40 mm.**

## What this does NOT yet explain

The 2025 TRIBE board *did* clear its full field successfully, with intact FR4 underneath.
So a full clear is possible on this laser. Something about the 2025 configuration was
gentler, and the prime suspect remains **Q-Pulse**: that file recorded none, so it ran at
whatever the profile default was, and this coupon forced 200/350/500 ns. If the default in
May 2025 was much shorter, every pulse carried far less energy.

**Do not conclude that full-field clearing is impossible. Conclude that 95 % at 200 mm/s
with a 200 ns pulse is the wrong end of the dial for it.**

## Pulse width, first read

Across the three blocks the moats get visibly cleaner and deeper left to right, so
**500 ns cut best and 200 ns worst** for the thin features. The field burned through in
all three, worst at 500 ns, which is consistent.

No winner should be declared until the moats are probed with a meter. Cutting deep is not
the same as cutting *through* the copper, and the whole question is electrical.

---

## Later the same day: the material confound

Two photographs changed the priority. **The back of the 2025 TRIBE board is clean, with
crisp through-holes and no charring. The back of the coupon is charred, blistered and
delaminated at the edges.** Same laser, same operator.

Then the stock inventory: **the coupon was run on a board Edson has no more of, and the
TRIBE board was made on different stock he still has.** That is a confound large enough
to invalidate every parameter conclusion drawn so far.

### Two other variables that were not controlled on run 1

- **Air assist was OFF.** Without it the vaporised copper and resin sit in the beam path
  absorbing the next pulse. This may explain the soot plumes and the burning that
  continued after the copper was gone, independently of any setting.
- **Hatch angle was fixed.** ComMarker's guidance is to rotate it between passes,
  around 13 degrees, so successive passes do not retrace the same lines.

### Order of operations from here

1. **Identify the materials.** Thickness with calipers, and the colour of the substrate
   at a cut edge. Glass weave and a translucent green or yellow means FR-4. Brown or tan
   paper fibres means FR-2 phenolic, which chars badly and is the likely reason one of
   the stacks was remembered as "not ideal".
2. **Run `B6-MATERIAL-TEST.lbrn2` unchanged on each material**, air assist on. It is only
   52 x 34 mm, so it costs almost nothing to repeat. Any difference between the results
   is then the material, because nothing else moved.
3. **Only then** run the dense coupon 3, on whichever material wins.

### The standard to measure against

Not "did it clear" but "does it look like the TRIBE board's back". Clean holes, no
charring, intact substrate. That board proves the process works. Anything worse is a
material or a setting that has not been found yet, never evidence that it is impossible.

---

# Run 3 — coupon 3 on the TRIBE-family stock, air assist ON

**Material identified from the packaging: "Qimoo 5 Pcs FR4 Copper Clad Prototyping PCB
Board", 玻纤FR = glass-fibre FR4.** Six of the larger boards in stock. So the substrate
question is settled: it is FR4, not phenolic.

## The speed × passes matrix, read off the board

Columns 200 / 500 / 1000 / 1500 mm/s, rows 1 / 2 / 4 / 8 passes, all at 100 % power.

- **The entire 200 mm/s column is charred black at every pass count.** Speed is the
  dominant variable, not passes.
- Moving right the cells get progressively cleaner.
- **1500 × 1** barely marks the copper: the cell is still copper-coloured with striations.
- **1500 × 4** shows greenish glass weave, which is the closest thing on the board to
  copper removed with the substrate surviving.
- Every cell still shows heat damage to some degree. **Nothing on this coupon is a clean
  result.**

## Frequency

**100 kHz is worse than 40 kHz**, with the largest soot plume of the pair. That
contradicts the instinct that higher frequency is gentler; at fixed power the pulses get
weaker but far more numerous, and the average heating goes up.

## Hatch rotation

+0 / +13 / +45 / +90 are hard to separate by eye at this energy level. The test is not
wrong, it is drowned out: everything is over-cooked, so uniformity differences do not
show. Re-test once the energy is in range.

## Holes and cuts

Both went through, with fire and visible flame late in the job, and heavy charring
craters around every hole. **24 and 48 passes are enormous overkill.** Same for the
32 and 64 pass cut strips.

## The conclusion that matters

**Everything on this coupon ran at 100 % power. That was never varied, and it is now
clearly the wrong knob to have left fixed.** The winning direction is unambiguous:

> **faster and weaker.** 200 mm/s is catastrophic, 1500 is the best column, so the next
> coupon goes to 3000 mm/s. And 100 % power at 4 passes is far more energy than removing
> 35 µm of copper needs.

Next coupon: **power × speed in the low-energy regime**, plus hole and cut ladders that
start far lower than the ones that caught fire.

---

# Run 4 — the low-energy coupon. The regime was found.

**No soot plumes, no char craters, no fire.** Going faster and weaker was the right call,
and the difference between this board and run 3 is not subtle.

## Visual read of the fills, pending the meter

| | 1000 | 1500 | 2000 | 3000 |
|---|---|---|---|---|
| **50 %** | olive, textured | brown | brown | orange-brown |
| **75 %** | olive/green | **dark green, strongly textured** | dark green | brown |

The **olive and green cells look like exposed glass weave**, i.e. copper actually removed.
The **brown and orange cells look like darkened copper still in place**. If that reading
holds, the working window is **75 % at 1000-2000 mm/s**, and 3000 is too fast at any power
tested.

⚠️ **This is a colour judgement from a photograph and it is exactly the kind of call that
has been wrong twice in this project.** Brown could be exposed FR4 resin, or it could be
copper oxide, which is still copper. The meter decides, nothing else.

The 25 % row is cut off at the top of the photograph and has not been read.

## Holes

4 passes marks only. 8 passes gets the small ones through. **16 passes appears to take all
three sizes through**, including the 6.6 mm, with far less charring than run 3's 24 and 48.

## Cuts

8 passes scribes only. 16 passes is visibly deeper but the strip does not look released.
The cut ladder needs to go up again, though nothing like as far as 64.

## Moats

Three clean shallow lines, no charring. They read coppery rather than substrate-coloured,
which suggests they may not be through the copper. **Meter across them.**

---

# Run 5 — the hole coupon. A badly designed test.

**Material confirmed: 1.6 mm**, calipers, Qimoo FR4.

## What went wrong, and it was the coupon, not the laser

I packed **44 holes and 11 layers into roughly 60 x 50 mm**. Every group sat a few
millimetres from its neighbours, and the job ran for a very long time. By the time the
later layers ran, the surrounding copper was already hot from the earlier ones.

**The result is dominated by cumulative heating, which is a property of my layout, not of
any setting being tested.** The whole strip is discoloured with oxidation rainbows and
brown scorch, and it is not possible to attribute that to wobble, passes or power.

On a real board the holes are spread over the whole surface with copper between them to
sink the heat. That is the condition the 2025 TRIBE board was made under, and it is
probably a large part of why its holes came out clean.

**Lesson for any future hole test: space the groups far apart, cut the number of
variants, and give the board time to cool between layers.**

## What is still readable

**Two of the 6.6 mm holes came out clean and white** while everything around them
scorched. Those two are the only unambiguous successes on the board and it is worth
knowing which layers they belong to.

## The strategic conclusion

Coupon 4 already established that **16 passes opens every hole size**, on a board that was
not thermally crowded. That is enough to make a PCB with. Chasing a better hole recipe
before making a single real board is optimising a step whose true behaviour only shows up
at real board geometry, with real spacing.

**Stop optimising. Make a board.** The next thing to learn comes from a real layout, not
from another coupon.

## Run 5, the back side — a hypothesis worth testing before anything else

The exit side is almost uniformly black. The two clean 6.6 mm holes are clean because
**their slugs fell out**, taking the charring with them. Everywhere the slug stayed put,
the underside cooked.

**The board was lying flat on the metal fixture.** That matters more than it sounds:

- the beam punches through and then keeps going into aluminium, which reflects it
  straight back into the exit side of the hole
- the vaporised resin has nowhere to escape, so it sits in the hole and burns
- the fixture conducts heat back into the board between passes

**This is the standard reason laser-cut parts char on the underside, and the standard fix
is to lift the work off the bed** so the exit side is open air. Standoffs, a honeycomb
bed, or even two strips of scrap under the edges.

**None of the five runs so far controlled for this**, and it may explain more of the
charring than any setting we have tuned. It costs nothing to test.

The 2025 TRIBE board's clean back is consistent with it having been supported differently,
though that is inference, not something anyone recorded.

## Run 5, attributed — and wobble wins

Only two of the eleven hole recipes cut through, and Edson identified them:

| recipe | passes | verdict |
|---|--:|---|
| **wobble 0.10, 100 %, 40 mm/s** | **8** | ✅ through, and the fastest thing on the board |
| wobble 0.10, 60 %, 100 mm/s | 64 | ✅ through, but eight times the passes for no gain |
| everything without wobble | 8, 16, 24 | ✗ |

**Wobble halved the passes.** Coupon 4 needed 16 passes without it, and even then charred.
With a 0.10 mm wobble, 8 passes goes through 1.6 mm FR4.

The mechanism is the same one Edson already relies on for cutting thick metal: the beam
traces a small circle as it advances, so the energy is smeared along a wider kerf instead
of being dumped into a stationary point. On a 0.6 mm hole the beam is essentially standing
still, which is the worst case, and wobble is the direct fix.

**This was Edson's suggestion, and it is the single best hole finding of the day.**

⚠️ **Kerf.** A wobbled hole finishes larger than drawn by roughly the wobble size. Measure
one of each diameter and subtract the difference in `circuit2lbrn.py`, or every hole on a
real board comes out oversize.
