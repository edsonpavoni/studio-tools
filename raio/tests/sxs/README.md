# raio · side-by-side fixtures (phase-1 parity gate)

The same shape, run once from **LightBurn** and once from **raio**, on one scrap, so the two marks can be compared under a loupe. Written 2026-10-21. Rebuild everything with:

```
RAIO_NO_USB=1 ~/.venvs/raio/bin/python studio/raio/tests/sxs/make_sxs.py
```

Each fixture has three files:

- **`<name>-lightburn.lbrn2`**: LightBurn runs this one. It sits in the **upper row** (+y, toward the column).
- **`<name>-raio.lbrn2`**: the same file, moved to the **lower row** (−y) or sideways.
- **`<name>-raio.raio`**: raio's own import of the twin above. `raio mark` runs this one.

Because raio imports its twin, the importer is part of the test, and the two marks land side by side instead of on top of each other. All three files are written with trilha's `LbrnDoc` (LightBurn frame, +78.75). `<name>-raio.svg` is raio's preview.

| fixture | where | recipe | raio's estimate |
|---|---|---|---|
| `fill-square` | LightBurn: two 10 × 10 squares centred at (−8, **+12**) and (+8, **+12**) mm<br>raio: the same at (−8, **−12**) and (+8, **−12**) | **left: copper engrave "Test 2"**: Scan, 150 mm/s, 100 %, 20 kHz, 350 ns, interval 0.02, angle 0, bidir, **3 passes**. The locked recipe is 3 global × 3 = 9; the brief asked for 3.<br>**right: trilha CLEAR**: Scan, 1500 mm/s, 75 %, 40 kHz, 200 ns, interval 0.05, +13°/pass, 4 passes | 101 s + 6 s |
| `wobble-circle` | LightBurn: Ø10 circle centred at (0, **+12**)<br>raio: the same at (0, **−12**) | **aluminium 1.1 mm cut**: Line, 800 mm/s, 100 %, 65 kHz, 350 ns, wobble 0.15 / 0.025, 5 passes | 3.7 s; 9.3 s if the board waits the polygon delay at every vertex. LightBurn under advance semantics: about 0.2 s of motion |
| `trilha-coupon` | LightBurn: `B6-HOLES5-COUPON` at its own place, x −75…−31, y −63…−47<br>raio: the same, moved **+50 mm in x** (x −25…+19) | as in the coupon:<br>H_P070: 70 %, 400 mm/s, 40 kHz, 200 ns, 8 passes, wobble 0.10/0.02<br>CLEAR: 75 %, 1500 mm/s, 4 passes, 0.05, +13° | 36 s |

**`trilha-coupon` is not "as-is".** Every trilha coupon carries Text labels, and raio refuses Text (FORMAT.md). Both copies are therefore `B6-HOLES5-COUPON.lbrn2` with its 4 Text labels removed ("0.68", "0.72", "0.76", and the caption), and nothing else changed. raio's twin wraps all the shapes in one Group whose XForm moves it +50 mm, so the run also tests group transforms.

## How the orchestrator runs a pair

**Run `wobble-circle` first.** It takes about 4 s, and it settles two questions that affect every cut recipe: wobble speed semantics and wobble size semantics.


Only one program can own the board, so LightBurn must be **quit** before raio runs, and raio must be idle before LightBurn opens.

1. **Place the scrap.**
   - `fill-square` and `wobble-circle`: the same aluminium scrap as today's pulse-width rows.
   - `trilha-coupon`: a Qimoo FR4 scrap, **board off the bed, air on** (B6-PCB-RECIPE preflight).
   - In every case: focus as usual, goggles on, extraction on, E-stop in reach.
2. **LightBurn.**
   - Open `studio/raio/tests/sxs/<name>-lightburn.lbrn2` with device **B6 Mopa**.
   - Check the layer table against the recipe column above. LightBurn will hide 20 kHz and 200 ns because they are its defaults.
   - **Frame**, then **Start**. **Stopwatch it** from Start to the end of emission, and note LightBurn's own job time too.
   - **Quit LightBurn.**
3. **raio**, from the `0000 AI` folder, without `RAIO_NO_USB`:
   ```
   ~/.venvs/raio/bin/python studio/raio/raio.py plan studio/raio/tests/sxs/<name>-raio.raio --svg /tmp/<name>.svg
   ~/.venvs/raio/bin/python studio/raio/raio.py mark studio/raio/tests/sxs/<name>-raio.raio
   ```
   - `mark` prints the layer table and the plan, then traces the **red frame** of the job's bounding box and holds it until the go.
   - On Edson's word: `touch ~/Library/Caches/raio/go.flag`. To cancel: `touch ~/Library/Caches/raio/stop.flag`.
   - On the go, raio re-inits and fires. This is the same flow as `mark_test.py`.
   - The log is written to `studio/raio/logs/raio-mark-*.json` and includes `mark_seconds`.

## What to compare (upper row = LightBurn, lower = raio)

- **Position:** the rows are exactly 24 mm apart in y (50 mm in x for the coupon), and the same in x. Any skew or offset is a frame or scale error.
- **Size:** squares 10.00 mm and circle Ø10.00 (outer edge of the wobble ≈ 10.15). Measure with calipers.
- **Fill:**
  - Colour and depth.
  - Visible line pitch. 0.02 shows no lines; 0.05 just shows them.
  - Edge quality: raio's lines stop exactly at the outline. LightBurn may overscan or trim.
  - On CLEAR, the +13°/pass cross texture.
  - Whether a ridge appears where the serpentine turns.
- **Wobble.** This pair settles two things that affect every cut recipe, so run it first.
  - **Speed semantics: depth and darkness first, time second.**
    - raio's beam runs its loops at 800 mm/s, about 2.9 m over 5 passes.
    - If LightBurn instead applies 800 mm/s to the forward advance, its beam runs about 19× faster along the loop. Its circle then gets about 19× less energy per mm and will look clearly lighter and shallower.
    - Equal depth and darkness means the semantics match.
  - **Time, read in this order.**
    - First raio's own `mark_seconds`: about 3.7 s means the board does not wait the polygon delay at each MarkTo vertex. About 9.3 s means it waits 100 µs at every vertex (56 k vertices).
    - Then LightBurn's stopwatch, read with that known.
    - Timing alone is ambiguous: a dense LightBurn polyline with per-vertex delays could look like "loop" even under advance semantics.
  - **Size semantics: is Size a diameter or a radius?** Measure the kerf width and the outer diameter of both circles. raio treats Size as the **diameter**, which gives a kerf of about 0.15 + spot and an outer Ø of about 10.15 + spot.
    - If LightBurn's kerf is about 0.30 + spot, LightBurn's Size is a radius, and every raio wobble cuts at half width.
    - The archive conflicts. MATERIAL-SETTINGS says size 0.30 gives a kerf of about 0.3, which reads as diameter. HOLES-5 *measured* a 0.24 kerf at size 0.10, which fits radius better.
  - Also compare the burr, and whether raio's 5 passes go as deep as LightBurn's.
- **Time** (every pair): LightBurn's stopwatch against raio's `mark_seconds` and raio's two estimates.
- **Coupon:**
  - Every hole goes through.
  - Hole diameter (0.76 drawn should seat a 2.54 header pin with light pressure, SCORE-HOLES5).
  - CLEAR rings fully cleared. Use the meter, not the eye.

If raio marks lighter at the same recipe, the first suspects are the start-up values in `lmc.init()` (MACHINE.md "parity of the start-up values"). The next suspect is the jump delay: raio sends `DelayTime(50)` (500 µs) after each hatch jump, while LightBurn may use `0x800D`. Log every result in `LOG.md`.
