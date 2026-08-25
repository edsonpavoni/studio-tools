# Cut test — six files, run one at a time

The board cutout is the last unmeasured layer. These six squares, 10 x 10 mm, are
positioned so that all six land on one board without overlapping, **but each lives in its
own file**.

## Why one file per test

Every coupon so far has been partly spoiled by the board still being hot from the
previous test. Separate files put the cooling under your control instead of LightBurn's.

**Run B6-CUT-01, then stop. Let the board come back to room temperature. Then 02.**
Touch it: if it is warm anywhere near the next square, wait longer. Two minutes is
usually plenty on 1.6 mm FR4 with air assist. Blowing compressed air across it helps.

The squares are 26 mm apart in X and 30 mm in Y, which is far enough that a cooled
neighbour stays cooled.

## The six

| file | recipe | speed | total passes | est. time |
| `B6-CUT-01.lbrn2` | taper 40 | 40 mm/s | 32 | 545 s |
| `B6-CUT-02.lbrn2` | taper 400 | 400 mm/s | 64 | 109 s |
| `B6-CUT-03.lbrn2` | w20 40 | 40 mm/s | 32 | 670 s |
| `B6-CUT-04.lbrn2` | w10 400 | 400 mm/s | 64 | 101 s |
| `B6-CUT-05.lbrn2` | w10 40 | 40 mm/s | 32 | 503 s |
| `B6-CUT-06.lbrn2` | none 40 | 40 mm/s | 32 | 32 s |

**01 and 02 are the tapered ones**, Edson's thick-metal technique: start at 0.30 mm
wobble so the kerf opens and the vapour escapes, then narrow through 0.20 and 0.10 to
0.05 so the energy concentrates at the bottom of the trench as it deepens.

**03, 05 and 06** are fixed-wobble and no-wobble controls at the current 40 mm/s.

**04** asks whether the hole lesson transfers: 400 mm/s did the clean work on holes, so
does it cut too, given enough passes.

## What to record

For each: **did the square fall out**, how clean is the edge, how much charring on the
underside, and how long it actually took.

The winner is the fastest one that releases the square with an edge you would put on a
sculpture. Speed matters less here than on the fills, because a board has one outline and
dozens of holes.

## Other cooling strategies worth using

- **Lift the board off the bed.** Already advised. Stops the beam reflecting off the
  fixture back into the exit side.
- **Interleave.** Already automatic for holes: no hole is drilled beside one still hot.
- **Order the job gentlest-first.** Fills at 75 % / 1500 mm/s barely warm the board;
  holes and the outline are the hot parts. The outline is already last, because after it
  the board is loose.
- **Air across the work between layers**, not just air assist at the nozzle.
- One that cuts both ways: **a metal backing sinks heat but reflects the beam.** Good
  under a fill, which never punches through. Bad under holes and the outline, which do.
