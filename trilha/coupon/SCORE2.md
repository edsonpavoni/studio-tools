# Coupon 2 — score sheet

Run date: ____________   FR4 thickness: ______   Pulse width used: ______ ns
Line interval: ______ mm

## 1. Field power ladder — THE question

**Look at the BACK of the board for each square, not the front.**

| Power | 95 % | 70 % | 50 % | 35 % | 25 % | 15 % |
|---|---|---|---|---|---|---|
| copper gone on the front? |  |  |  |  |  |  |
| FR4 scorched on the back? |  |  |  |  |  |  |
| resistance across the square |  |  |  |  |  |  |

**Highest power where copper is gone AND the back is clean: ______ %.**
That number is the production fill power. Write it into `B6-PCB-RECIPE.md` with today's date.

If NO power satisfies both, the full-field clear is off the table on this machine and the
pipeline switches to isolation moats only. That is not a defeat — run 1 already proved the
moats cut cleanly at every width from 0.10 to 0.40 mm, and moats are far faster anyway.

## 2. Hole pass ladder

| Passes | 8 | 16 | 32 | 64 |
|---|---|---|---|---|
| 1.0 mm hole through? |  |  |  |  |
| 6.6 mm circle through? |  |  |  |  |

**Passes needed for a clean 1.0 mm hole: ______   for 6.6 mm: ______**

If the big circle needs far more than the small hole, holes should be sized into
separate layers by diameter rather than all sharing one recipe the way the 2025 file did.

## 3. Cutout pass ladder

| Passes | 12 | 24 | 48 |
|---|---|---|---|
| released from the stock? |  |  |  |
| edge quality |  |  |  |

**Passes for a clean board edge: ______**

## 4. Anything that caught fire, smoked badly, or surprised you
