# 16-pin header test — score sheet

Date: ______   Material: Qimoo FR4 1.6 mm   Air assist: ON
**Board lifted off the bed?** yes / no

Recipe, both rows identical: 0.9 mm · 100 % · 400 mm/s · 40 kHz · 200 ns · 16 passes ·
wobble 0.10/0.02. The only difference is drilling order.

## Row A — drilled in order

| | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| through? |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| clean back? |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |

**Does it get worse left to right?** yes / no  ← this is the accumulation question

## Row B — odds first, then evens

| | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| through? |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| clean back? |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |

**Is B cleaner than A?** yes / no / same

If B is cleaner, interleaving becomes the default in `circuit2lbrn.py` for every board:
it costs nothing but the order the holes are written in.

## Measurements

Hole diameter, three of them: ______ / ______ / ______ mm
**Kerf = measured − 0.900 = ______ mm** ← this goes into the converter

**Does a real 16-pin 2.54 mm header drop in?** yes / tight / no

## Time

Row A took ______ s. Predicted 28 s for 16 holes at 1.78 s each.
