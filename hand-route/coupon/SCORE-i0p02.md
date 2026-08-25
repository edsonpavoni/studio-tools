# B6 PCB coupon — score sheet

Run date: ____________   FR4 thickness: ______   Copper: 35 µm / other: ______

**Line interval this coupon was generated at: 0.02 mm.**  Record it, because it changes
the energy per unit area by the same factor. Half the point of the exercise is
comparing 0.1 mm (the device default, and almost certainly what the 2025 board used)
against something finer.

Left half scuffed matte with maroon Scotch-Brite before the run: yes / no

## 1. Pulse width — the question this coupon exists to answer

| Block | Copper fully cleared in the 6 mm field? | Field time | Edge quality | Verdict |
|---|---|---|---|---|
| 200 ns | 350 ns | 500 ns |  |  |  |  |

**Winner: ________ ns.** Write it into `B6-PCB-RECIPE.md` with today's date.

## 2. Minimum isolation gap

Probe ACROSS each moat with a multimeter. It must read **open**.

| Moat | 0.1 mm | 0.125 mm | 0.15 mm | 0.175 mm | 0.2 mm | 0.25 mm | 0.3 mm | 0.4 mm |
|---|---|---|---|---|---|---|---|---|
| open? |   |   |   |   |   |   |   |   |

**Smallest gap that reads open on every block: ________ mm.** That is the floor for
every design from here on. **The 2025 TRIBE board already proves 0.171 mm works**, so
anything above that is a regression and worth re-running before accepting.

## 3. Holes

Caliper each one. The drawn circle is the nominal drill diameter with no kerf
compensation, so the finished hole will come out slightly LARGER by roughly one kerf.

| Drawn | 0.6 | 0.9 | 1.0 | 1.3 | 2.4 | 6.6 |
|---|---|---|---|---|---|---|
| measured |  |  |  |  |  |  |
| through? |  |  |  |  |  |  |

If the measured hole is consistently larger by a fixed amount, that amount is the kerf.
Subtract it from future drawn diameters.

## 4. Surface prep

Did the scuffed half clear noticeably better than the bright half?  yes / no / no difference

If yes, scuffing becomes a required step in the pipeline, not an option.

## 5. Time

Field of 6 × 6 mm took ______ s. A 50 × 50 mm board is about 70 fields, so a full
clear is roughly ______ min. If that number is unreasonable, switch from
clear-the-whole-field to isolation-moats-only and re-time.
