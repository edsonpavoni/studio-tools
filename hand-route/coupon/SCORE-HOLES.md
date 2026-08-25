# Hole coupon — score sheet

Date: ______  Material: Qimoo FR4  Thickness: ______ mm  Air assist: ON

Fill recipe is already settled: 75 %, 1500 mm/s, 4 passes, 40 kHz, 0.05 mm, hatch +13.
This coupon is only about holes, which is where every flame so far has happened.

---

## Through, per size

Mark `-` not through · `OK` through and clean · `C` through but charred · `F` flame seen.

| | 0.6 mm | 1.0 mm | 2.4 mm | 6.6 mm |
|---|---|---|---|---|
| no wobble, 8x |  |  |  |  |
| no wobble, 16x |  |  |  |  |
| no wobble, 24x |  |  |  |  |
| wobble 0.10, 8x |  |  |  |  |
| wobble 0.10, 16x |  |  |  |  |
| wobble 0.10, 24x |  |  |  |  |
| wobble 0.20, 8x |  |  |  |  |
| wobble 0.20, 16x |  |  |  |  |
| wobble 0.20, 24x |  |  |  |  |
| 60 % 100 mm/s 32x |  |  |  |  |
| 60 % 100 mm/s 64x |  |  |  |  |

## The two questions this coupon exists to answer

**1. Does wobble reduce the fire?** Compare the no-wobble rows against the wobble rows at
the same pass count. Watch the job, not just the result.

**2. Does wobble let you use fewer passes?** If wobble 0.10 at 8 passes matches no-wobble
at 16, that halves the time and the heat.

## Hole diameter, measured

Wobble widens the kerf, so a wobbled hole comes out larger than drawn. Measure a few and
work out the offset, because that number has to be subtracted from the drawn diameter in
`circuit2lbrn.py` or every hole on a real board will be oversize.

| drawn | 0.6 | 1.0 | 2.4 | 6.6 |
|---|---|---|---|---|
| measured, no wobble |  |  |  |  |
| measured, wobble 0.10 |  |  |  |  |
| measured, wobble 0.20 |  |  |  |  |

**Kerf offset to apply: ______ mm**

## Winner

Setting: ______________________  Passes: ______  Wobble: ______
Flame? ______  Char? ______
