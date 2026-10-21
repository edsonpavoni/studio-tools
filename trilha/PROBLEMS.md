# PROBLEMS.md — what actually went wrong building The Source P2 laser board

*Started 2026-08-27 at Edson's request, mid-bring-up: "create a log for the hand-route
tool, with all the problems we are having with this project. No solutions. Just what
happened. After the project is done, we will use it to polish our tool."*

*That is the contract of this file: symptoms and events only, with the time they ate
where we know it. Fix-thinking goes to BACKLOG.md, after the project ships. Where a
mid-session fix is part of what happened, it is stated as an event, not endorsed.
Sources: `pcb-v3/LOG.md` (20+ dated entries), `pcb-v3/PARTS.md`, the 2026-08-26/27
bench transcripts, photos in `pcb-v3/evidence/`.*

---

## A. Problems that were born in DESIGN, before any copper was cut

**A1. A dimension was typed instead of measured, and no check could catch it.**
V3 was cut with the XIAO's rows 10 mm apart. The real module is 15.24 mm. The module
physically could not seat; V3 became wall art. Every verifier we have checks the board
against the design — nothing checks the design against the physical part. (2026-08-23,
one full board lost.)

**A2. Nothing in the toolchain ever declared which face of a single-sided board is
copper.** `<board layers={1}>`, pour `layer="top"`, no mirror anywhere in the converter.
Hole positions are the same from both faces, but pin order reverses — and for four board
versions nothing forced that question. Found 2026-08-27, 01:00, by photographing a module
that could only fit upside down.

**A3. The XIAO is mounted upside down on the working board, as a live workaround for A2.**
Costs, discovered one at a time rather than up front: its USB-C port faces the board and
cannot be plugged; the antenna sits ~1.6 mm off the ground copper, so the radio is
effectively spent; and every reflash means pulling the module out of its socket — until a
cold joint elsewhere made flashing-through-the-board work, that was the only way.

**A4. Which wire is D+ and which is D− churned for four days.** It was an open item on
2026-08-23, a decision ("board defines, wires follow") on 08-24, re-opened by a photo
read on 08-26, entangled with A2 on 08-27 at 01:00, and finally settled on the bench at
02:25 — where the actual blocker turned out to be a cold solder joint, not the mapping.
Five log entries about two wires.

**A5. The netlist's names are meaningless at the bench.** `NET_16` tells you nothing
standing over a board with a probe. Every diagnostic conversation began by translating
net ids to SDA / GATE_B / XSHUT_A by hand from a comment block in the tsx. (The
signals.json layer was built mid-project, 2026-08-27, because of this.)

**A6. The MOSFET footprint's pin order and the package's lead order disagree, and no
artifact said so.** The design routes footprint pin1→Source, pin3→Gate; the IRLZ44N is
physically G-D-S. The part must go in "reversed", and the only place that fact lived was
in the routing itself — invisible in every view, unknown at the moment of soldering.
Both MOSFETs went in the naive way. Both laser channels were dark for a whole evening.

**A7. The orientation truth then flip-flopped during diagnosis.** It was derived from
the datasheet (reversed), reversed again by a wrong reading of which parts had been
reworked ("QA was never touched"), then re-corrected when Edson said both had been
reversed. The correct answer was only ever pinned by the bench: laser A fired. A fact
that should have been recorded once at design time was re-derived three times under
pressure, twice wrongly, and one rework cycle was spent on the wrong conclusion.

**A8. Values on the board and values in the source disagree, silently.** The source
says 330 µF 63 V; the fitted can reads 16 V. The source says 120R gates; the fitted
parts are 150R. The gate pulldowns (10k) appeared in no document at all until their
bands were read from a photo on 08-27. None of these mattered electrically — but each
one had to be *checked* before it could be dismissed, at the bench, mid-fault-hunt.

**A9. The board has no I2C pull-ups, and nothing records whether that was a decision.**
The pods happen to carry their own. Discovered as a question ("does the pod bring
pull-ups?") during the dead-bus hunt.

**A10. Known autorouter floor: tscircuit will not open clearances past 0.1 mm** while
the process floor is 0.171 mm proven. Worked around by hand-routing everything — which
is the tool's whole reason to exist, but the constraint shaped the project.

---

## B. Problems of the PROCESS — laser-cut, maskless, single-sided FR4

**B1. Removing a component removes copper.** Unplated holes, no mask, hand-soldered
joints: pulling the wrongly-oriented MOSFETs tore the ground path. 4 V appeared between
two pads of the same net. The repair is a bare wire jumper across half the board.
Edson: "taking out a component damages its traces — so I have to make that crazy jumper."

**B2. The board has a small heat budget.** Every joint has now been heated one to three
times. By the end of the session the working assumption was "we cannot heat this board
too much" — reflow candidates had to be *ranked* rather than just done.

**B3. On a maskless board, every bare thing is a short waiting to happen.** The repair
jumper is uninsulated and crosses live copper. Uncut leads stand proud everywhere.
Nothing prevents contact; only attention does.

**B4. Burnt FR4 + flux leaks at the megohm level everywhere.** A resistance reading
between two unrelated nets settles near 1.85 MΩ instead of OL. Every "is this a short?"
measurement had to be interpreted through that haze.

**B5. A cold joint on a hand-soldered mod wire mimicked a design error.** The D− pad
joint behind the XIAO was cold. The symptom — no USB enumeration ever — was
indistinguishable from the D± mapping being wrong (A4), and the mapping got the blame
for hours. Cable, breakout orientation, and wiring were all suspected first; the joint
was found last.

**B6. Connector wiring at the pod was crossed, twice.** Pod A's SDA/SCL arrived
swapped; the bus scanned empty. Found only by brute-forcing every pin pair from
firmware. Pod B is suspected of the same crossing and is still unconfirmed as of this
writing.

**B7. An intermittent fault moved when probed and never got caught.** Channel B crashed
the board reliably; after a session of meter probing, the crash stopped reproducing;
laser B lit; then it went dark again twenty minutes later. Every static measurement in
between read clean. As of this writing the fault is somewhere in a ranked list of nine
joints, and the honest status is "displaced, not found."

**B8. What "the board crashed" even was took an hour to pin.** The same symptom — port
gone mid-command — was, at different points, plausibly: a power brownout, a USB data-line
disturbance, the chip fully rebooting, or the bench diag's own zero-ramp double-laser
slam tripping the host's current limit. Instrument and fault were entangled: the crude
diag had no ramps, while the real firmware (with ramps, stagger, both-on caps) was the
thing being protected from.

---

## C. Problems of the BENCH LOOP — human, tool, and assistant in one room

**C1. "Measure between QB pin 3 and pin 1" is a terrible interface.** For most of the
session, pad identification was verbal: a name in chat, then counting pads on a dense
board by eye. Slow, error-prone, and it produced at least one wrong reading relay
(10 Ω reported, 10 kΩ actual — which flipped the diagnosis for several minutes until
corrected). (The probe() overlay was built mid-session because of this.)

**C2. Orientation could not be checked against reality on screen.** The schematic view
showed pin numbers and, later, S/D/G letters — but nothing showed *the part as it
physically sits*, so "is this thing in right?" always needed a datasheet plus mental
rotation, the exact operation Edson names as his weak point: "I'm not naturally good
at it. I need a way to not error."

**C3. The tool assumed a full screen; the real desk is a split screen.** The whole
session ran with hand-route in half a window beside Claude Code. Labels collided and
the layout cramped at that width; every screenshot documents it.

**C4. Every flash failed once.** The CDC port dies on the first esptool attempt, the
chip drops to ROM bootloader on a *different port name*, and the retry succeeds there.
Known dance, never automated; a dozen occurrences today.

**C5. Toggling test state did not survive power cycles, and looked like a hardware
fault when it didn't.** The bench diag boots into "laser A solid". After any unplug —
and soldering means unplugging — the toggle that was running is gone. "No blinking" was
reported as a fault once when the true state was "board rebooted into a different mode."

**C6. Firmware safety facts were wrong or absent at the moment they mattered.** The
firmware boots ARMED while its own platformio.ini says it boots disarmed; the pulse
command bypasses the armed flag entirely (traced in source mid-session, before firing).
Neither fact lived anywhere a bench operator would meet it.

**C7. Measurement results lived only in chat scroll.** Ten probe steps produced ten
readings, each reported as a chat message, none accumulated anywhere. The 10Ω/10k
mis-relay (C1) survived long enough to steer the diagnosis because there was no
readback surface where the number sat next to the expectation.

---

*(End of problems as of 2026-08-27 ~13:00. Channel B intermittent still open; pod B
still unconfirmed; conformal coating pending the final test.)*

---

*Addendum, 14:46 — B7/B8 resolved on the bench: the "intermittent" was never a moving
joint. The first repair jumper healed only half the torn ground island; the bulk cap
stayed floating for a further day, so every sharp switching transient hit the USB rail
unbuffered and reset the chip. Both problems were one problem, and it was invisible to
every static measurement taken. The tell, when it finally came, was a resistance reading
that climbed slowly — a capacitor charging through the meter. B6's second half also
closed: pod B's crossing is still unconfirmed as of this line.*

*Addendum 2, 15:35 — the LEDC confound (see addendum 1) closed by measurement: the
peripheral was innocent; the original firmware was correct; the fault was the repair
bridge breaking. En route, a new problem class for the list: **C8. The probe broke the
signal it measured.** A pin-readback diagnostic used `gpio_set_direction`, which
silently reconnects plain-GPIO output in the matrix and severs LEDC routing — the first
run returned a clean table of zeros on a working peripheral, and was one step from
convicting it. Second run, touching only the IOMUX input-enable bit, read perfect duty
on both channels.*

*Addendum 3, 16:10 — C9 for the list: **the bench state lied about the system state,
three ways at once.** A soak "found" a dead system that was fully alive: the logging
tool buffered everything to the end (so its log read empty), the motor was parked by
design (so "not running" read as fault), and bench clutter sat in both sensors' bands
(so gating read as stuck). Separately, LEDC-in-artwork-context ships unresolved: perfect
duty in an isolated sketch, reported dark in the full firmware, confounded three ways,
and the show shipped digitalWrite because that was the only path ever confirmed by eye.*
