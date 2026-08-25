# Hole line — score sheet

Date: ______  Material: Qimoo FR4 1.6 mm  Air assist: ON
**Board lifted off the bed?** yes / no  ← if no, stop and lift it

30 holes, all drawn at **0.9 mm**, at **2.54 mm** pitch. Three holes per recipe, groups
numbered 1-10 left to right. Same diameter everywhere, so the measured hole minus 0.9 mm
IS the kerf for that recipe.

| # | recipe | through? | clean? | measured Ø | kerf | header pin fits? |
|---|---|---|---|---|---|---|
| 1 | 400 mm/s · 16x · wobble 0.10 |  |  |  |  |  |
| 2 | 400 mm/s · 32x · wobble 0.10 |  |  |  |  |  |
| 3 | 200 mm/s · 8x · wobble 0.10 |  |  |  |  |  |
| 4 | 200 mm/s · 16x · wobble 0.10 |  |  |  |  |  |
| 5 | 200 mm/s · 16x · wobble 0.20 |  |  |  |  |  |
| 6 | 100 mm/s · 8x · wobble 0.10 |  |  |  |  |  |
| 7 | 100 mm/s · 16x · wobble 0.10 |  |  |  |  |  |
| 8 | 100 mm/s · 8x · wobble 0.05 |  |  |  |  |  |
| 9 | 100 mm/s · 16x · NO wobble |  |  |  |  |  |
| 10 | 40 mm/s · 8x · wobble 0.10 — **run 5 control** |  |  |  |  |  |

All at 100 %, 40 kHz, 200 ns.

## What each comparison answers

**1 vs 2** — does doubling passes at 400 mm/s matter, or is 400 simply too fast?
**3 vs 6 vs 10** — 8 passes at 200 / 100 / 40 mm/s. How fast can the winner go?
**4 vs 5** — wobble 0.10 against 0.20 at the same speed and passes.
**6 vs 8** — wobble 0.10 against a tighter 0.05. Smaller wobble should mean a tighter
hole; does it still get through?
**7 vs 9** — the wobble question again, at speed. Run 5 answered it at 40 mm/s.

## The two numbers that decide it

**Kerf.** Measured Ø minus 0.9. Wobble widens the hole, and that offset has to go into
`circuit2lbrn.py` or every hole on a real board is oversize. If wobble 0.20 gives a much
larger kerf than 0.10, that is a reason to prefer 0.10 beyond speed.

**Fit.** Push a real 2.54 mm pin header into the holes. Through and clean is not the same
as usable.

## Also worth writing down

Did the row char progressively from left to right as heat accumulated? On a real header
the holes are this close together, so if group 10 looks worse than group 1 purely from
position, that is a spacing problem the recipe cannot fix and the answer is a pause
between holes rather than a different setting.

Fastest recipe that is through, clean and fits: ______________________
