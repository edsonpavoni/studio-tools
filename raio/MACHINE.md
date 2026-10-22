# raio · the B6, as raio sees it

What raio can send to the machine, what it can read back, and what it cannot reach. Written 2026-10-21 after the first afternoon on the machine. **✅ proven today** on this B6 · **📄 documented** (open-source drivers + EZCAD's own DLLs, not yet exercised here) · **❌ not reachable**. Protocol detail: `research/02-protocol.md`; the day's evidence: `LOG.md`.

## The machine in numbers

| | |
|---|---|
| Controller | BJJCZ **LMC V4** USB galvo board, USB `9588:9899` "USBLMCV4", serial 20200507, signature `0000218409002002` ✅ |
| Transport | one bulk endpoint out (0x02) for 12-byte commands and 3072-byte job packets, one in (0x88) for 8-byte replies; pyusb, no driver ✅ |
| Source | JPT MOPA 60 W, 1064 nm, pulse 2–500 ns, frequency 1–4000 kHz (envelope per width; `research/03-machine.md` §5) |
| Field | nominal 157.5 mm in galvo units (416.095 units/mm), lens correction `jcz15.cor` uploaded at every init ✅; **measured 2026-10-21: true reach 155.8 (x) × 155.3 (y) mm, corrected per axis by `lmc/calibration.json` (1.0107 / 1.0139), verified 80.0 × 80.0** ✅; working field 150 mm; f = 210 mm lens |
| Frame | raio's mm frame = LightBurn's, centre at (0,0), +x machine right, +y toward the column ✅ (LightBurn's files: bottom-left origin, +78.75) |
| Lift (Z) | its own controller (touch panel, sensor, stepper, 8 mm screw, 0.04 mm/pulse), powered through the Type-C from the base; **not on the board's axis channels** ✅ |
| Host loss | the board finishes the job it holds ✅ (whole jobs are sent; E-stop is the backstop) |

## What raio can SEND

### Set-up (immediate commands)
| What | Status |
|---|---|
| Lens correction table (65 × 65 points) | ✅ |
| Enable laser, control / laser / delay / timing modes, standby tickle, first-pulse killer, PWM period and width, FPK2, fly-res, analog port mid-scale, the 0x3A tail | ✅ as a set, with the values from the captured EZCAD session on a Raycus machine. Parity with LightBurn's marks is the phase-1 gate; these values are the first suspect if raio marks lighter |
| Output port, 16 bits: **bit 0 = laser enable, bit 8 = red pilot** | ✅ both. The other 14 bits are free outputs if anything is ever wired to them (air-assist valve, beacon) 📄 |
| Master oscillator (MO) open / close | ✅ |
| Galvo jump to a point (immediate) | ✅ |
| Extended axes 0 and 1: speed, acceleration, absolute move in pulses, home, abort | ✅ the board moves them; nothing is attached (the Rotary port carries them; the lift ignores them) |
| List control: reset, execute, stop, pause, resume | ✅ reset/execute/stop; 📄 pause/resume |
| **Abort** (stop list → MO off → clear → dummy list → verify idle → centre) | ✅ 7 ms |
| Reset (0x40), disable laser (0x02) | 📄 |
| Direct laser gate on/off (0x0E/0x0F) | 📄 never used: no interlock |

### Inside a job (list commands, run by the board in real time)
| What | Status |
|---|---|
| Jump to / mark to a point, with distance word | ✅ |
| Jump speed, mark speed (mm/s → galvo units per ms) | ✅ |
| Laser-on delay (negative allowed), laser-off delay, polygon delay, jump delay, end delay | ✅ (LightBurn's B6 values: −300 / 100 / 100 µs) |
| **Power** 0–100 % (12-bit) | ✅ |
| **Frequency** 1–4000 kHz (period in 50 ns ticks) | ✅ at 20 and 30 kHz |
| **Pulse width** in nanoseconds, `[0x8026, 0, ns]` | ✅ settled against LightBurn |
| MO open / close inside the list, port write inside the list | ✅ |
| Dwell (laser on at a point, for dots and drilling) | 📄 |
| Wait for an input bit before continuing (a hardware gate) | 📄 |
| Mark-count change (repeats) | 📄 |
| JPT-specific parameter (0x8050) | 📄 unused |
| Dynamic-focus "DA-Z" words (a third galvo axis) | 📄 no such hardware on the B6 |

Everything geometric (fill, wobble, arcs, text, passes, kerf, Z scaling) is raio's job in software; the board only ever sees jumps, marks and the settings above.

## What raio can READ

| What | Status |
|---|---|
| Board identity: serial words, version / signature | ✅ |
| Status: READY, BUSY (a list is running), AXIS (an axis is moving) | ✅ |
| List status: running / paused | 📄 |
| Galvo position | ✅ |
| Input port word (idle 0xC012) | ✅ read; no bit mapped yet: the pedal socket is empty, the enclosure socket unwired |
| Extended axis positions | ✅ |
| Fiber source status word (idle 0x0041) | ✅ read; bit meanings unknown: logged on every job, learned the first time something trips |
| Mark count, time taken by the last job | 📄 |
| Source configuration (pulse-width table?) via 0x2F / 0x30 | 📄 untested; worth one read |

## What raio CANNOT reach (today)

| What | Why | Door |
|---|---|---|
| ❌ **Z height / focus** | the lift is a separate controller; the sensor's number stays on the panel | map the Type-C pins (data? button lines?); the base's `Laser_SW_V05` board (UP_KEY / DOWN_KEY in, UPLD / DWLD out); ComMarker's answer; hardware inside the tower (Edson) |
| ❌ **Source temperature** | the JPT keeps it internally; its serial port is not brought out | only an alarm, if the source's alarm line reaches a board input |
| ❌ **Fans** | wired to the supply, always on | a thermostat or a raio-switched relay (backlog 11) |
| ❌ **Actual emitted power** | no sensor | a power meter on the bench, once |
| ❌ **Door / stop inputs** | sockets exist, nothing wired | the enclosure socket + a bench button on an input (backlog 4–5) |
| ❌ **Pedal** | socket empty | plug it in, map the bit; raio does not start on it unless asked |
| ✅ **What the E-stop cuts** | **everything**: main power to board, source, lift, fans (tested 19:42: the board left the USB at the press; panel, head LED and fans dark) | the one stop that needs no Mac; keep it within reach |
| ❌ **Reading the job back from the board** | the board does not expose its buffer | raio keeps the job; the log is the record |

## Compared with LightBurn
Everything LightBurn sends to this board, raio can send; the one unknown left is **parity of the start-up values** (phase-1 gate: the same recipe on the same scrap). What LightBurn cannot do on this machine, raio cannot do yet either: move Z, read focus, read temperature. LightBurn's camera does not work on macOS; raio's does (port 8878).
