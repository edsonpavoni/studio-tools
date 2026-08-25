# Coupon 3 — score sheet

Run date: ______   FR4 thickness: ______   Copper: 35 um / other: ______
Surface: bright / scuffed matte

## ⚠️ AIR ASSIST ON. Run 1 had it off.

Run 1 was done without air assist and produced heavy soot plumes and charring. Air assist
blows the vaporised copper and resin out of the beam path instead of letting it sit there
absorbing the next pulse. **This alone may change the result more than any number below**,
which is exactly why it must be on for every cell here: one variable at a time.

Also: fume extraction. Vaporised copper plus heated epoxy is not something to breathe.

---

## A. Speed x passes — THE question

All at 100 %, 40 kHz, 200 ns, line space 0.05 mm. **Judge from the BACK of the board.**
A cell passes only if the copper is gone on the front AND the FR4 is unscorched behind it.

|            | 200 mm/s | 500 | 1000 | 1500 |
|------------|---|---|---|---|
| **1 pass**  |   |   |   |   |
| **2 passes**|   |   |   |   |
| **4 passes**|   |   |   |   |
| **8 passes**|   |   |   |   |

Mark each cell: `-` copper still there · `OK` clean copper removal, FR4 intact ·
`B` burned into the FR4 · `X` through the board.

**Best cell: ______ mm/s x ______ passes.** That is the production fill recipe.

Run 1 sat at 200 mm/s x 1 pass and went straight to `X`. ComMarker's own PCB
recommendation is the 1000 x 4 cell. If the whole 200 column is `X` and the 1000 column
is `OK`, the lesson is that **four fast passes beat one slow one**, which is the thing
worth writing down.

## B2. Hatch rotation between passes — the ComMarker tip

All at 1000 mm/s, 4 passes, 40 kHz, 0.05 mm. Only the rotation per pass changes.
Without rotation every pass retraces the same lines and leaves ridges between them.

| +0 deg | +13 deg | +45 deg | +90 deg |
|---|---|---|---|
| copper gone? |  |  |  |
| uniform, or striped? |  |  |  |
| FR4 clean behind? |  |  |  |

**Best rotation: ______ deg.** If +0 is visibly striped and the others are not, hatch
rotation becomes a permanent part of the fill recipe.

## B. Frequency, at 1000 mm/s x 4 with +13 deg

| 40 kHz | 100 kHz |
|---|---|
|  |  |

## E. Cleaning pass

The square marked `clean` is cleared the same way as the 40 kHz cell, then given
ComMarker's cleaning pass (20 %, 1500 mm/s, 100 kHz, 0.01 mm, 2 passes).

Compared with the plain 40 kHz square, is it: cleaner / the same / worse? ______
Does it measure open where the plain one does? ______

## C. Holes — 1.0, 2.4 and 6.6 mm at rising passes

| Passes | 8 | 24 | 48 |
|---|---|---|---|
| 1.0 mm through? |  |  |  |
| 2.4 mm through? |  |  |  |
| 6.6 mm through? |  |  |  |

**Passes needed: 1.0 mm ______ · 2.4 mm ______ · 6.6 mm ______**

If big holes need far more passes than small ones, holes must be split into layers by
diameter instead of sharing one recipe the way the 2025 file did.

## D. Cutout

| Passes | 32 | 64 |
|---|---|---|
| released? |  |  |
| edge quality |  |  |

Run 1's 12 passes did not come close, so the ladder starts higher.

## The measurement that decides everything

Meter across every cleared square. **Copper looking gone is not copper being gone.**
A square that reads short still has a conductive film on it.
