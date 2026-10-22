# Raio · 02 · The protocol: talking to the B6 MOPA's BJJCZ board

*Research note, 2026-10-21. Scope: everything Raio (Python, macOS) needs in order to drive the ComMarker B6 MOPA 60 W directly over USB, replacing LightBurn.*

**Confidence tags used on every claim**

| Tag | Meaning |
|---|---|
| **VERIFIED** | Read directly from a local file on this Mac: config, binary strings, the disassembled vendor DLL, or the parsed .cor file |
| **DOCUMENTED** | Stated in an open-source implementation (meerk40t `balormk`, galvoplotter, Balor) or in a public write-up or doc, but not checked on this machine |
| **INFERRED** | Our reasoning from indirect evidence. Each one says how to verify it |

**Abbreviations:** `B6/` = `studio/B6-Mopa/files/install/B6 MOPA/` · `EZ/` = `B6/EZCAD for ComMarker B6 MOPA/` · `mk/` = meerk40t `meerk40t/balormk/` (commit d511944, 2026-09-25) · `gp/` = galvoplotter · `bal/` = Balor on GitLab (commit dfc7faf, 2022-11-06). Clones are in `/private/tmp/claude-501/raio-proto/` (`src/meerk40t`, `src/galvoplotter`, `balor-gitlab`). The vendor-DLL disassembly is in the same folder (`lmc1.asm`, `lmcmio.asm`).

---

## 0. The answer in six lines

1. **Board:** a BJJCZ **LMC V4** USB galvo card from the EZCAD2 family. It enumerates as **"USBLMCV4"**, vendor BJJCZ, **9588:9899**, bcdDevice 0x0005, serial "20200507". The Windows driver is `Lmcv2u.sys`, which serves both V2 and V4. **VERIFIED** (live USB descriptors read on this Mac on 2026-10-21, plus the INF).
2. **Protocol:** fully reverse-engineered and open. Each command is 12 bytes (`<6H`). Single commands go out one at a time with an 8-byte reply. Job lists go out in 3072-byte packets (256 commands) on the same bulk endpoint. The meerk40t code is **MIT** and can be reused. **DOCUMENTED + VERIFIED** against the vendor DLL.
3. **Field:** **157.5 mm**, not 150. Three sources agree: markcfg7, LightBurn, and the .cor header. **Galvo 2 is X.** **VERIFIED**
4. **Z:** the board has an extended-axis motor channel (opcodes 0x26–0x2A). We decoded its exact wire format from EZCAD's own DLL. **But the B6's Z column almost certainly has its own controller** (the touch panel showing "Real focal length"), and nothing here proves the column is wired to the board. **Moving Z from Raio is UNPROVEN.** Section 5 gives the test, and the fallbacks if it fails.
5. **ComMarker Studio** (`/Applications/ComMarker_Studio.app`) **cannot drive this board.** It only opens USB devices 04B4:1004 and 7580:0101, which are BSL-family controllers. Its Z and autofocus code belongs to other ComMarker machines (Omni X). **VERIFIED** (disassembly)
6. **Top risk:** LightBurn's forum already reports this exact machine (B6 60 W JPT MOPA on macOS) with an *"Unrecognized board signature 0000238409002002"*, and its red-light framing draws only a straight line. This is a newer board revision. Every opcode must be confirmed read-only first, then with the red light, then with the laser on scrap.

---

## 1. The board

### 1.1 Identity

| Fact | Value | Source | Confidence |
|---|---|---|---|
| USB vendor:product (running board) | **0x9588 : 0x9899** — "Laser Mark Control Board V2 [USB]" | `B6/driver/win_10/Lmcv2u.inf`, `win11/X64AMD_LmcV2u/Lmcv2u.inf` | VERIFIED |
| USB 9588:9980 | "JCZ USB Loader": the Cypress FX2 before firmware is loaded. Genuine boards boot from EEPROM straight to 9899. Clone boards sit at 9980 until the host uploads firmware (`mk/clone_loader.py`). | INF; `mk/clone_loader.py:16-17` | VERIFIED (INF) / DOCUMENTED (loader) |
| Older IDs in the Win7-32 INF | 9588:9990 and 9588:9999 (USBLMC V1) | `B6/driver/win_7 32/JCZLMC.inf` | VERIFIED |
| Windows driver | `Lmcv2u.sys`, KMDF 1.9, BJJCZ, class GUID `{9894E04E-1D84-4501-A00F-01519CCD26FE}`, DriverVer 06/10/2011 5.0.1636.1 | INF | VERIFIED |
| Hardware | Altera FPGA + Cypress FX2 (8051) USB µC, RAM buffer, EEPROM. XY2-100 output to the galvo. A stepper "rotary" axis output. | bryce.pw/engraver.html; `bal/readme.html` | DOCUMENTED (on Bryce's LMCV4-FIBER-M rev 20171014) |
| Model on the B6 | **USBLMCV4** (USB product string). The studio's R5 note says LMCV4-FIBER-M. The manual mentions both "USBLMCV2" and "USBLMCV4". | Live descriptors (coordinator, 2026-10-21); `studio/B6-Mopa/R5-ROTARY.md`; manual p.7 | VERIFIED (V4). The exact sub-model (FIBER-M or Digital) is still to be read: photograph the board |
| Variants LightBurn tells apart | LMC2-Lite, LMC2-Lite-Digital, USB-Lite, USB-Lite dual-source, LMC-Dynamic, LMC4, LMC4 Digital. Each has its own "startup sequence". Unknown boards produce "Unrecognized board signature: …". | `strings` on `/Applications/LightBurn.app/Contents/MacOS/LightBurn` (around line 200040) | VERIFIED (strings) |
| Board signature on a B6 60 W MOPA | `0000238409002002`. LightBurn 2.0.05 and 2.1.00-RC-11 did not recognise it, and framing broke. **It is very likely the raw 8-byte `GetVersion` (0x0007) reply as hex.** Balor's captured EZCAD session on an LMCV4-FIBER-M answers GetVersion with `0000024c09002002`: same bytes 0–1 and 4–7, only w1 differs (0x4C02 there, 0x8423 on the B6). | [forum 189558](https://forum.lightburnsoftware.com/t/czfiber-unrecognized-board-signature-0000238409002002-framing-broken-on-commarker-b6-60w-mopa/189558); `balor-gitlab/balor/BJJCZ_LMCV4_FIBER_M_blobs.py` (`init`) | DOCUMENTED (report) / INFERRED, high (that it is the GetVersion reply). Step 1 of the test plan settles it |
| Laser source | JPT MOPA 60 W, 1–4000 kHz, 2–500 ns, 2 mJ max | B6 manual p.3 | VERIFIED (manual) |

### 1.2 USB descriptors on this Mac

The first pass of this research found no laser on USB. Later the coordinator connected it and read the descriptors. **Nothing was sent to the board.** **VERIFIED:**

- product "USBLMCV4", vendor "BJJCZ";
- idVendor 0x9588, idProduct 0x9899, bcdDevice 0x0005, serial "20200507";
- USB 2.0 high speed, bDeviceClass 0, one configuration, 10 mA;
- interface 0, class 0xFF (vendor), **four bulk endpoints, all wMaxPacketSize 512**;
- no kernel driver claims it (only `AppleUSBHostCompositeDevice`);
- pyusb (`~/.venvs/raio/bin/python`, Homebrew libusb) finds it, with `is_kernel_driver_active` False.

How Balor's endpoint names map onto these four:

| EP | Direction / type | Balor name | Carries | Source | Confidence |
|---|---|---|---|---|---|
| **0x02** | OUT bulk | `ep_homi` (host out, machine in) | **Commands and the list.** Every 12-byte single command, and every 3072-byte list packet, go out here. There is no separate list endpoint. | `mk/usb_connection.py:15`; `bal/balor/BJJCZ_LMCV4_FIBER_M.py`; every write in Balor's EZCAD capture is to EP 0x02 | VERIFIED (endpoint exists) / DOCUMENTED (use) |
| **0x88** | IN bulk | `ep_himo` (host in, machine out) | **Status.** An 8-byte reply that is read after each single command. Nothing is read after a list packet. | `mk/usb_connection.py:16`; the capture reads 0x88 after each command | VERIFIED (exists) / DOCUMENTED (use) |
| 0x01 | OUT bulk | `ep_hodi` | **Licence dongle** (EZCAD anti-clone check). The board works without it. **Raio never touches it.** | `bal/…FIBER_M.py`; bryce.pw | VERIFIED (exists) / DOCUMENTED (use) |
| 0x81 | IN bulk | `ep_hido` | Dongle reply | same | same |

No kext, entitlement, or kernel-driver detach is needed on macOS.

### 1.3 V2 vs V4, and "Lite"

- The `Lmcv2u` driver and PID 9899 cover the "V2" generation of USB LMC boards. The LMCV4-FIBER-M also reports 9899 (Balor's class `BJJCZ_LMCV4_FIBER_M` uses PID 0x9899). **DOCUMENTED.**
- Board types differ in their startup parameters and in some features, which LightBurn handles case by case. The vendor DLL gates the newer pulse-width modes (picoseconds, index) behind `IsBoardSupportFun(0x12)`. **VERIFIED** (Lmc1.dll disassembly at 0x10057d35 and 0x10057f6e).
- EZCAD "Lite": Balor names opcode 0x0040 `IS_LITE_VERSION` ("tell laser to nerf itself"). meerk40t calls it `Reset`. The vendor DLL export is `MIO_Reset`, and EZCAD sends it to **abort an axis move** (section 5.3). **VERIFIED** (that the vendor name is Reset) / DOCUMENTED (the opcode value 0x40).

---

## 2. Transport

### 2.1 Library on macOS

- **LightBurn 2.1.00** (bundle version 2.1.00; the README says "2.1.04", so check which one runs) drives the board with **libusb**. libusb is statically linked into the main binary (`libusb_*` strings, `LibUSB_Init`), and the bundle also ships `MacOS/libusb-1.0.0.dylib`. The device type in prefs is `"Type": "LibUSB"`, protocol `JCZFiber`. **No kext and no driver install.** The board is a vendor-class device that macOS does not claim. **VERIFIED** (`otool -L`, strings, `~/Library/Preferences/LightBurn/prefs.ini`)
- LightBurn is signed with hardened runtime (`flags=0x10000(runtime)`), and its only entitlement is the camera. DYLD interposition to log its USB traffic is therefore **blocked**: you would have to re-sign a copy. **VERIFIED** (`codesign -d`)
- **Raio:** use `pyusb` with the libusb-1.0 backend, in a venv, with `libusb` from Homebrew. No entitlement or root is needed for a vendor-class device. **Only one process can claim the interface**, so LightBurn (or EZCAD in a VM) must be closed or disconnected before Raio opens the board. Raio should report `USBError: Resource busy` as "LightBurn has the laser". **DOCUMENTED** (pyusb/libusb behaviour, `mk/usb_connection.py` claim/retry logic) / INFERRED for this Mac. Test it.

### 2.2 Packet shapes

| What | Bytes | Layout | Reply | Source | Confidence |
|---|---|---|---|---|---|
| Single command | 12 | `struct.pack("<6H", op, v1, v2, v3, v4, v5)`, op < 0x8000 | Read 8 B from 0x88 → `<4H` (w0..w3) | `mk/controller.py:619-623, 421-441`; vendor `AddCmd` / `MIO_Cmd(E,G,G,G,G,G,G)` | VERIFIED (vendor signature: one opcode plus up to 5 words) |
| List packet | 3072 = 256 × 12 | `<6H` commands with op ≥ 0x8000, **padded with 0x8002 (EndOfList/NOP)** | none | `mk/controller.py:23-24, 594-617`; `bal/balor/sender.py` `_abort_list_chunk`; bryce.pw | DOCUMENTED |
| Correction-line write | 12 | `[0x0010, dx, dy, first?0:1, 0, 0]` | **no read** (meerk40t sends with `read=False`) | `mk/controller.py:1530` | DOCUMENTED |

`mk/usb_connection.py:write` asserts that every write is exactly 12 or 3072 bytes. The USB timeout there is 100 ms.

### 2.3 Status word

The single-command reply is four LE uint16. The status flags live in **w3**:

| Bit (w3) | Meaning | Source | Confidence |
|---|---|---|---|
| 0x20 | READY: the board accepts another list packet | `mk/controller.py:206`; `bal/…FIBER_M.py` (`report[6]&0x20`) | DOCUMENTED |
| 0x04 | BUSY: a list is executing (red-light loops count as busy) | same | DOCUMENTED |
| 0x40 | AXIS: an extended-axis move is in progress | `mk/controller.py:208`. EZCAD's own `MIO_MoveAxisTo` keeps polling `MIO_GetState` until bit 0x40 of the state word clears. | VERIFIED that EZCAD waits on bit 0x40 (LMCMIO.dll 0x10001ab9). DOCUMENTED that this bit sits in USB reply w3 (meerk40t) |
| 0x08 (from `GetListStatus` 0x0A) | Paused | `mk/controller.py:1499-1514` | DOCUMENTED |

meerk40t gets its status by sending `GetVersion` (0x0007) and reading w3. Balor polls with `ReadPort` (0x0025) and `GetVersion`.

In Balor's capture of EZCAD (`balor-gitlab/balor/BJJCZ_LMCV4_FIBER_M_blobs.py`):

- Idle polling is `0x0007` with v1 = 0. Init sends `0x0007` with v1 = 1. Before lighting, EZCAD sends `0x0007 0x0100` (Balor's helper copies that).
- The replies end in bytes `20 02`. That makes w3 = 0x0220 when idle and READY, and 0x0224 or 0x0204 while busy. Those values are consistent with the bit table above. **DOCUMENTED** (capture).

**Correction to an earlier draft:** the `0x0100`/`0x0104` constants inside `MIO_GetVersion` belong to the DLL's *no-device simulation branch*. They are not proof of what is sent on the wire.

### 2.4 The two channels (command vs list)

- **Immediate commands** (op < 0x8000) run now: setup, port write, goto, axis moves, status reads.
- **List commands** (op ≥ 0x8000) are buffered by the FPGA and run in real time: jump, mark, speeds, delays, power, frequency, pulse width, port writes during the job.

**Streaming a job** (meerk40t `_list_end`, Balor `execute`):

1. Reset the list with `ResetList` (0x12).
2. Start the first packet with `listReadyMark` (0x8051). Balor calls this "new job".
3. Before sending each 3072-byte packet, wait for READY, then send it.
4. After each packet, send `SetEndOfList`. meerk40t sends 0. Balor sends `(0x8001, 0x8001)`.
5. Send `ExecuteList` (0x05):
   - meerk40t sends it once, after the 3rd packet.
   - Balor sends it after every packet.
6. At the end, append `listEndOfList`, flush, and wait until BUSY clears.
7. Read `GetMarkTime` (0x41, param 3), which returns the time taken.

**The two projects differ on step 4/5.** EZCAD's own behaviour, decoded from Balor's capture (`blobs.py`, sequences `start` / `run` / `mark_packet_separator` / `mark_data_end`), DOCUMENTED:

```
0x0012 ResetList; 0x000C GetPositionXY; 0x000D GotoXY(start)
packet 1 (starts 0x8051)  -> 0x0019 SetEndOfList
packet 2                  -> 0x0019 SetEndOfList; 0x0005 ExecuteList     # execution starts after the 2nd packet
packet n                  -> 0x0019 SetEndOfList                          # wait for READY (poll 0x0025/0x0007) between packets
last                      -> 0x0019 SetEndOfList(0); 0x0016 SetControlMode(1); poll 0x0007 until !BUSY
after a mark job          -> 0x0021 WritePort(0); 0x0033 Fiber_SetMo(0); 0x0041 GetMarkTime(3) x2; 0x0022 WriteAnalogPort1(0x7FF)
```

EZCAD's `SetEndOfList` arguments are *stale words left over from the previous command*: `8001 8001` after `GotoXY(8001,8001)`, and `9B9C 6617` after `GotoXY(9B9C,6617)`. So the firmware ignores them. Balor copied `0x8001, 0x8001` from this capture; meerk40t sends 0. **Either works. Send 0.** INFERRED (high).

On ExecuteList timing:
- meerk40t sends it once, after the 3rd packet.
- EZCAD sends it after the 2nd.
- Balor sends it after every packet.

Raio follows EZCAD, and sends it at the end if the job has fewer packets.

**Abort** (`mk/controller.py:821-839`; `bal/sender.py abort`): DOCUMENTED.

1. Stop the list: `StopExecute` (0x1F).
2. Close the fiber MO: `Fiber_SetMo(0)` (0x33).
3. Reset the list: `ResetList` (0x12).
4. Send one dummy packet, `[0x8051] + 255×0x8002`.
5. Send `SetEndOfList`, then `ExecuteList`.
6. Wait until BUSY clears.
7. Drop the port bits (laser-enable bit 0 off) and center the galvo with `GotoXY(0x8000, 0x8000)`.

**Pause / resume:** `StopList` (0x20) / `RestartList` (0x13). DOCUMENTED. **MEASURED on the B6, 2026-10-22 01:21–01:22 (`lmc/pause_test.py`, logs `pause-2026-10-22_01-2*.json`):** after `StopList` the status word goes `0x228` (bit 0x08 = paused, BUSY 0x04 off), so a host that waits for BUSY low takes a pause for the end of the job; after `RestartList` it goes `0x224` (BUSY again, 0x08 off) and marking continues; idle is `0x220`. `GetListStatus` word 2 read 9 in every state: not a pause flag. Laser-enable bit low + MO closed during the hold, then restored before `RestartList`: the board resumed (whether in place: Edson's look at the paused line).

### 2.5 Init sequence

**EZCAD's real init**, decoded from Balor's capture on an LMCV4-FIBER-M with a Raycus 20 W source (`blobs.py`, sequence `init`, 4331 transfers). DOCUMENTED (capture), with replies read from EP 0x88 after each command:

```
0009 GetSerialNo        -> 0000 0700 0600 2002
0007 GetVersion(1)      -> 0000 024c 0900 2002
0034 Fiber_GetStMO_AP   -> 0000 4102 0000 2002        (the three above repeated twice)
0003 (unknown — EZCAD sends 0x0003 here; meerk40t/Balor send 0x0040 "Reset")
0015 WriteCorTable(1) ; 4225 x 0010 WriteCorLine
0004 EnableLaser ; 0016(0) ; 001B(1) ; 0017(1) ; 001C(1) ; 001D(0x7D0, 0x14) ; 001A(0xC8) ; 001E(0x7D) ; 0006(0x7D)
0033 Fiber_SetMo(0) ; 0007(0)
002E(0xFFB, 1, 0x199, 0x64) ; 0032(0, 0x63, 0x3E8, 0x19)
0021 WritePort(0, 0)
003A ; 0022 WriteAnalogPort1(0x7FF) ; 003A
then idle polling: 0025 ReadPort -> 0000 faff 0000 2002 (w1 = 0xFFFA: inputs idle-high?) and 0007(0)
```

The meerk40t/Balor defaults listed below are **this capture's values**, so they come from EZCAD on a Raycus machine, not from the B6. The B6's EZCAD would send values derived from its own markcfg7. Until we capture the B6, use the capture values. The **`003A, 0022(0x7FF), 003A` tail is mandatory**: copy it exactly. Balor guesses that it releases the outputs from high impedance. Whatever it does, every working implementation sends it.

Order from `mk/controller.py:init_laser` (which agrees with `bal/sender.py _init_machine`). Values in brackets are meerk40t/Balor defaults. Where this machine's markcfg7 gives a related value, it is shown with ⟶.

1. `GetSerialNo` (0x09) and `GetVersion` (0x07). **Log the raw words.** They identify the board revision.
2. Balor only: `Fiber_GetStMO_AP` (0x34).
3. `Reset` (0x40).
4. **Correction table:** `WriteCorTable(1)` (0x15), then 65 × 65 = 4225 × `WriteCorLine` (0x10) (section 4.5). Send `WriteCorTable(0)` (or an all-zero table) to run uncorrected.
5. `EnableLaser` (0x04).
6. `SetControlMode` (0x16) [0].
7. `SetLaserMode` (0x1B) [1].
8. `SetDelayMode` (0x17) [1].
9. `SetTiming` (0x1C) [1].
10. `SetStandby` (0x1D) [2000, 20]. ⟶ markcfg `PWMTICKPERIOD=5000`, `PWMTICKPULSEWIDTH=1`, `ENPWMTICK=1`. LightBurn: `Laser_TickleEnable` true, freq 5, pulse 1.
11. `SetFirstPulseKiller` (0x1A) [200]. ⟶ markcfg `ENFPK=1, FPK=40`. Balor: "my ezcad lists 40 µs".
12. `SetPwmHalfPeriod` (0x1E) [125].
13. `SetPwmPulseWidth` (0x06) [125].
14. `Fiber_SetMo(0)` (0x33): MO closed.
15. `SetFpkParam2` (0x2E) [0xFFB, 1, 409, 100]. meerk40t bug: it sends p3 twice (`fpk2_p4 = self.service.fpk2_p3`).
16. `SetFlyRes` (0x32) [0, 99, 1000, 25].
17. meerk40t sends `0x3A`, then `WriteAnalogPort1(0x7FF)` (0x22), then `0x3A` again. Balor sends `WritePort(bits)` first. **See 3.3 on what 0x39/0x3A really are.**

The mapping from markcfg7 fields (FPK=40, tick 5000/1, `MAXPWMFREQ=4000000`, `MINPWMFREQ=1000`) to these arguments is **INFERRED**. To get the exact values, import the markcfg into meerk40t, or compare LightBurn's "Sending startup params (LMC4)" with a USB capture.

The meerk40t defaults are the ones the community runs on many JCZ fiber machines. **Use them first.**

---

## 3. Command reference

Every row comes from three places: `mk/controller.py` (names and opcodes); `bal/balor/sender.py` and `command_list.py` (Balor names and notes); and the **vendor DLL exports** in `EZ/LMCMIO.dll` and `EZ/Lmc1.dll`. We extracted the vendor exports with a PE export parser (`raio-proto/scripts/pe_exports.py`). The vendor opcode for each `MIO_*` function was read from its `push imm` before `MIO_Cmd`.

**VERIFIED** in the table means the vendor DLL emits that opcode.

**Word types in vendor signatures:** E = card index (u8, not sent), G = u16, K = u32, H = int.

### 3.1 Immediate commands (op < 0x8000)

| Op | meerk40t name | Vendor (LMCMIO) | Args (words v1..v5) | Meaning / notes | Conf. |
|---|---|---|---|---|---|
| 0x02 | DisableLaser | MIO_DisableLaser | – | | VERIFIED |
| 0x04 | EnableLaser | MIO_EnableLaser | – | Init | VERIFIED |
| 0x05 | ExecuteList | MIO_ExecuteList | – | Start running the buffered list | VERIFIED |
| 0x06 | SetPwmPulseWidth | MIO_SetPwmPulseWidth (E,G) | pw | Init | VERIFIED |
| 0x07 | GetVersion | MIO_GetVersion (E,G) | 0 (poll), 1 (init), 0x0100 (before lighting) | Reply w3 = status; the whole reply is probably LightBurn's "board signature" | DOCUMENTED (EZCAD capture in Balor; the opcode is from Balor and meerk40t) |
| 0x09 | GetSerialNo | MIO_GetSerialNo | – | 4 words. Likely the "board signature". | VERIFIED |
| 0x0A | GetListStatus | MIO_GetListStatus | – | w3 0x04 running, 0x08 paused | DOCUMENTED |
| 0x0C | GetPositionXY | MIO_GetPositionXY | – | Galvo position | VERIFIED |
| 0x0D | GotoXY | MIO_GotoXY (E,G,G) | x, y (meerk40t adds angle, distance) | Immediate galvo move. Aborts a running job (Balor). | VERIFIED |
| 0x0E / 0x0F | LaserSignalOff / On | MIO_LaserSignal* | – | Direct laser gate. **Never use outside a test with an interlock.** | VERIFIED |
| 0x10 | WriteCorLine | (inside MIO_WriteCorTable) | dx, dy, nonfirst | One correction point | DOCUMENTED |
| 0x12 | ResetList | MIO_ResetList | – | | VERIFIED |
| 0x13 | RestartList | MIO_RestartList | – | Resume after StopList | VERIFIED |
| 0x15 | WriteCorTable | MIO_WriteCorTable (E,H,table[65][65][2],G) | 1 = table follows, 0 = none | | VERIFIED |
| 0x16 | SetControlMode | MIO_SetControlMode | mode | Init [0]. Balor sends 1 at the end of a job. | VERIFIED |
| 0x17 | SetDelayMode | MIO_SetDelayMode | mode | [1] | VERIFIED |
| 0x18 | SetMaxPolyDelay | MIO_SetMaxPolyDelay | delay, sign 0x8000 | | VERIFIED |
| 0x19 | SetEndOfList | (Lmc1) | 0 or (0x8001, 0x8001) | See 2.4 | DOCUMENTED |
| 0x1A | SetFirstPulseKiller | MIO_SetFirstPulseKiller | fpk | | VERIFIED |
| 0x1B | SetLaserMode | MIO_SetLaserMode | mode | [1] | VERIFIED |
| 0x1C | SetTiming | MIO_SetTiming | mode | [1] | VERIFIED |
| 0x1D | SetStandby | MIO_SetStandby (E,G,G,H) | p1, p2 | Tickle / standby pulse | VERIFIED |
| 0x1E | SetPwmHalfPeriod | MIO_SetPwmHalfPeriod | p | | VERIFIED |
| 0x1F | StopExecute | MIO_StopExecute | – | Abort | VERIFIED |
| 0x20 | StopList | MIO_StopList | – | Pause | VERIFIED |
| 0x21 | WritePort | MIO_WritePort (E,G,G) | **bits, second word** | Output port. The vendor sends a 2nd word, read from CLmcDev+0xE2, meaning unknown; meerk40t sends 0. | VERIFIED (2 words) / INFERRED (meaning of word 2) |
| 0x22 / 0x23 / 0x24 | WriteAnalogPort1 / 2 / X | MIO_WriteAnalogPort* | value (0x7FF at init) | Analog outputs (unused on fiber) | VERIFIED |
| 0x25 | ReadPort | MIO_ReadPort | – | Input port. Balor treats `w0 & 0x8000` as the footswitch. | VERIFIED (opcode) / DOCUMENTED (bit) |
| 0x26 | SetAxisMotionParam | MIO_SetAxisMotionParam (E,G,G) | **min_speed, max_speed** (pulses/s) | Before every axis move. EZCAD clamps min ≥ 1 and max ≥ min. | **VERIFIED** (Lmc1 0x1004cb91-cbc9) |
| 0x27 | SetAxisOriginParam | MIO_SetAxisOriginParam (E,G,G) | **acc_time_ms, flags** | Flags word: bits 0x01/0x04 come from axis-0 config fields, 0x10/0x40 from axis 1. Probably home-input-low-valid, home-dir, limit-enable, limit-low-valid. For this config the flags are 0. | VERIFIED (layout; Lmc1 `SetAxisAccTime` 0x1004c759) / INFERRED (flag meanings) |
| 0x28 | AxisGoOrigin | MIO_AxisGoOrigin (E,G,H,CWnd) | axis | Homing. Needs a home switch. | VERIFIED (opcode, arg) |
| 0x29 | MoveAxisTo | MIO_MoveAxisTo (E,G axis,K pos,CWnd) | **pos_lo, pos_hi \| (0x4000 if axis≠0)** | Absolute move in pulses. Section 5. | **VERIFIED** (LMCMIO 0x10001a30, Lmc1 0x10063fef) |
| 0x2A | GetAxisPos | MIO_GetAxisPos (E,G) | axis | Reply: pos = w1 \| w2<<16 (sign-magnitude) | VERIFIED (opcode, arg) / DOCUMENTED (reply) |
| 0x2B | GetFlyWaitCount | MIO_GetFlyWaitCount | – | On-the-fly (unused) | VERIFIED |
| 0x2D | GetMarkCount | MIO_GetMarkCount | – | | VERIFIED |
| 0x2E | SetFpkParam2 | MIO_SetFpkParam2 (E,G,G,G,G) | 4 words | | VERIFIED |
| 0x2F / 0x30 | FiberPulseWidth / FiberGetConfigExtend | (Lmc1 `IPGGet*`) | – | Read source configuration | DOCUMENTED |
| 0x31 | InputPort (lock) | – | 0x04 clear, 0x02 enable-lock, 0x01 disable | Latched inputs | DOCUMENTED |
| 0x32 | SetFlyRes | MIO_SetFlyRes (E,G×5) | 4 words | | VERIFIED |
| 0x33 | Fiber_SetMo | MIO_IPG_OpenMO (E,H) | 1 open / 0 close | Master-oscillator enable. Open while marking, closed otherwise. EZCAD closes it before an axis move. | VERIFIED |
| 0x34 | Fiber_GetStMO_AP | MIO_IPG_GetStMO_AP | – | Source status | VERIFIED |
| 0x36 | GetUserData | – | – | | DOCUMENTED |
| 0x38 | GetFlySpeed | – | – | | DOCUMENTED |
| **0x39** | meerk40t: "DisableZ" | **MIO_ENABLEZ(card, 1)**, called by Lmc1 `SetEnableZ` | – | Vendor *Enable*Z, so meerk40t has the two names swapped. It is probably the DA-Z dynamic-focus output, not a stepper. | VERIFIED (vendor mapping: Lmc1 0x10058b7a pushes 1; LMCMIO maps 1 → 0x39) / INFERRED (that it is DA-Z) |
| **0x3A** | meerk40t: "EnableZ" | MIO_ENABLEZ(card, 0), called by `SetDisableZ` | – | Vendor *Disable*Z. **EZCAD itself sends 0x3A, 0x22(0x7FF), 0x3A at the end of init** (capture), and meerk40t copies that. Send it. | VERIFIED (mapping) / DOCUMENTED (init use) |
| 0x3B | SetZData | MIO_SETZDATA (E,E,E,G) | | DA-Z data (3-axis galvo `DYNAMIC_Z_*`) | VERIFIED (name) |
| 0x3C | SetSPISimmerCurrent | MIO_SetSPISimmerCurrent | | SPI lasers only | VERIFIED |
| 0x40 | Reset | MIO_Reset (Balor: IS_LITE_VERSION) | – | Init. Also used by EZCAD to abort an axis move (ESC/space). | VERIFIED (vendor name) / DOCUMENTED (value) |
| 0x41 | GetMarkTime | – | 3 | Time taken by the last job | DOCUMENTED |
| 0x62 | SetFpkParam | MIO_SetFpkParam (E,G×4) | | | VERIFIED |

### 3.2 List commands (op ≥ 0x8000, inside 3072-byte packets)

Lmc1 opcodes were read from `push 0x80xx` inside each exported `CLmcDev::list*` method (`raio-proto/lmc1_list.txt`).

| Op | meerk40t | Vendor `CLmcDev::` | Args | Units / conversion | Conf. |
|---|---|---|---|---|---|
| 0x8001 | listJumpTo | listJumpTo | x, y, angle, distance | Galvo units 0..65535, centre 0x8000. distance = min(0xFFFF, euclid). | DOCUMENTED |
| 0x8002 | listEndOfList | listEndOfList | – | Also used as the NOP padding | VERIFIED |
| 0x8003 | listLaserOnPoint | listLaserOnPoint | dwell | Fire in place (dot/drill) | VERIFIED |
| 0x8004 | listDelayTime | listDelayTime / listDelayTimeUs / listMarkEndDelay | t | **10 µs units** (meerk40t). Used for the open-MO delay (8 ms → 800) and end delay. | VERIFIED (op) / DOCUMENTED (units) |
| 0x8005 | listMarkTo | listMarkTo / listDirectMarkTo | x, y, angle, distance | Mark (laser on) to x,y | VERIFIED |
| 0x8006 | listJumpSpeed | listJumpSpeed | v | `v = mm_s × galvo_per_mm / 1000` (galvo units per ms), clamp 0xFFFF | VERIFIED (op) / DOCUMENTED (units) |
| 0x8007 | listLaserOnDelay | listLaserOnDelay | abs(µs), 0x8000 if negative | | VERIFIED (op) |
| 0x8008 | listLaserOffDelay | listLaserOffDelay | abs(µs), sign | | VERIFIED (op) |
| 0x800A | listMarkFreq (CO2) | – | | Not used on fiber | DOCUMENTED |
| 0x800B | listMarkPowerRatio (CO2/UV) | listMarkPulseWidth | | Not used on fiber | VERIFIED (op) |
| 0x800C | listMarkSpeed | listMarkSpeed | v | Same units as 0x8006 | VERIFIED |
| 0x800D | listJumpDelay | – | abs(µs), sign | | DOCUMENTED |
| 0x800F | listPolygonDelay | listPolygonDelay | µs/10 | | VERIFIED (op) |
| 0x8011 | listWritePort | listWritrPort (sic) | bits | Port change inside the job (red light, laser-enable bit 0) | VERIFIED |
| **0x8012** | listMarkCurrent | **listMarkCurrent and listMarkPowerRatio** | p | **Fiber power: `round(pct × 0xFFF / 100)`** | VERIFIED (op) / DOCUMENTED (scale) |
| 0x801A | listFlyEnable | listFlyEnable | | Unused | VERIFIED |
| **0x801B** | listQSwitchPeriod | **listMarkFreq** (vendor uses this for fiber frequency) | period | **`round(20000 / f_kHz)`**, i.e. the period in 50 ns ticks: 20 kHz → 1000, 4000 kHz → 5 | VERIFIED (op) / DOCUMENTED (formula) |
| 0x801C | listDirectLaserSwitch | listDirectLaserSwitch | | | VERIFIED |
| 0x801D | listFlyDelay | listFlyDelay | | | VERIFIED |
| 0x801E | listSetCo2FPK | – | | CO2 only | DOCUMENTED |
| 0x8021 | listFiberOpenMO | listIPGOpenMO | 1/0 | MO inside a list | VERIFIED |
| 0x8022 | listWaitForInput | listWaitForInput (G mask, G level) | mask, level | Pause the list until input bits match. Useful as a hardware interlock gate. | VERIFIED |
| 0x8023 | listChangeMarkCount | listChangeMarkCount | | | VERIFIED |
| 0x8025 | listEnableWeldPowerWave | listEnableWeldPowerWave | | | VERIFIED |
| **0x8026** | listFiberYLPMPulseWidth | **listIPGYLPMPulseWidth → `AddCmd(0x8026, 0, pw_ns, 0, 0, 0)`**. Generic form: `listIPGSetConfigExtend(sub, val)` → `[0x8026, sub, val, val_hi]` | see the note below | **MOPA pulse width** | **VERIFIED** (Lmc1 0x10050d4d, 0x10057bd7) |
| 0x8028 | listFlyEncoderCount | listFlyEncoderCount | | | VERIFIED |
| 0x8029 | listSetDaZWord | listSetDaZWord | | DA-Z | VERIFIED |
| 0x8050 | listJptSetParam | listJptSetParam (double, int, double) | | JPT-specific parameter. Not needed so far. | VERIFIED (op) |
| 0x8051 | listReadyMark | – | – | First command of every new list | DOCUMENTED |

**Bryce's own protocol notes** (`balor-gitlab/Documentation/notes.odt`, plus raw EZCAD list dumps in `scratch 1.odt`) add these facts. DOCUMENTED.

- **0x8001 / 0x8005 coordinates:**
  - Bryce lists param0 as **y** and param1 as **x**. meerk40t calls them (x, y). The board just has galvo 1 and galvo 2, and on the B6 galvo 2 is X. So the step-3 red-light test decides the mapping.
  - param3 = distance, which *must* be computed or the move fails.
  - **0x8005 param2** is 0x0000 for straight / first moves, 0x8000 for a sharp turn, 0x4000 for a gentle turn, and small values on ovals. It is probably corner/ringing compensation (meerk40t calls it "angle" and sends 0).
- **0x8004** wait is in 10 µs units.
- **0x8006 / 0x800C** speed: "~1.9656 mm/s per unit" on Bryce's lens. That is the meerk40t galvo-units-per-ms formula for his field size.
- **0x8007 / 0x8008** delays are in µs, 1:1.
- **0x8012** power: 90 % = 3685, 50 % = 2047, 33 % = 1351, i.e. ×4095. This confirms meerk40t's scale.
- **0x801B** period is in 50 ns units, which confirms `20000 / kHz`.
- **0x8021** laser on/off (MO) inside the list.
- **0x8051** begins a job.

EZCAD's real mark list, from the scratch dump:

```
8051 | 801B 1000 | 8012 0x7FF | 8006 0x7F3 | 800C 0xFE | 8007 100,0x8000 | 8008 100 | 800F 10 | 800D 8
8001 x,y,0,d | 8021 1 | 8004 800 | 8005 … ×4 | 8004 30 | 8021 0 | 8001 back to centre
```

So in EZCAD, **MO (0x8021) is switched inside the list around each shape**, with an 8 ms wait (0x8004 800) after opening. meerk40t instead opens MO with the immediate 0x33 command for the whole job. Repeats (continuous marking) are separated by `8023 1,1` (ChangeMarkCount). The red-light list is only `8001` jumps at a fixed speed (`8006` = `800C` = 0x5F6), and the red pointer is switched on by the immediate `WritePort(0x100)`, i.e. **bit 8**. DOCUMENTED (capture `start` sequence).

> ⚠️ **Pulse-width packing conflict (0x8026).**
>
> - **EZCAD's own DLL** puts a *sub-type* in word 1 and the value in word 2. Sub-type 0 = pulse width in ns; 3 = pulse width in ps; 6 = pulse-width index. The last two are gated by `IsBoardSupportFun(0x12)`. So EZCAD sends `[0x8026, 0, 200, 0, 0, 0]` for 200 ns.
> - **meerk40t** sends `[0x8026, 200, 0, 0, 0, 0]`.
> - Both cannot be right for the same firmware. **Raio should default to the vendor layout** and run the discrimination test in section 9, step 6: two squares at 4 ns and 200 ns. The difference in colour and texture on steel is obvious.
> - Before sending 0x8026, EZCAD also sends `listIPGOpenMO(0)` when a config flag is set and the fiber sub-type is not 7 or 13.

### 3.3 What "Z" means in this command set

The 0x39 / 0x3A / 0x3B commands and the list commands 0x8029 (`SetDaZWord`) / `listSetDaZ` drive the **DA-Z output**. That output feeds a third, focus-shifting galvo or analog Z used for "dynamic focus" (markcfg `DYNAMIC_Z_0..9=32768`, `ENABLE_DYNAMIC=0`, `m_bEnableOutputDaZ=0`). **They do not move a stepper.**

The stepper/extended axes are **0x26–0x2A only**. That axis use is VERIFIED from the `AxisMoveTo` disassembly. That 0x39–0x3B are DA-Z rather than a stepper is INFERRED, from how Lmc1 groups the names (`InitZData`, `SetEnableZ`, `listSetDaZ`) and from the markcfg `DYNAMIC_Z` keys.

There is **no flat `Lmc1_*` SDK** in `Lmc1.dll`. Its 235 exports are mangled C++ `CLmcDev` methods, e.g. `?AxisMoveTo@CLmcDev@@QAEHHNHH@Z` = `int CLmcDev::AxisMoveTo(int axis, double dist, int, int)`, plus `ExtAxisMoveToPos`, `AxisGotoOrigin`, `ExtAxisGotoOrigin`, `IsAxisInOrigin`. There is **no `Lmc1_SetZAxis`**. The 79 `LMCMIO.dll` exports are the thin USB layer. The flat `lmc1_*` "SDK" names belong to the separate MarkEzd.dll SDK, which is not in this install. **VERIFIED.**

---

## 4. Job model

### 4.1 Coordinates

- Galvo units are **0..65535 per axis, centre 0x8000**. The board takes integers. Moves outside the range must be dropped, as meerk40t does. DOCUMENTED.
- **Field = 157.5 mm.** The evidence:
  - `EZ/plug/markcfg7`: `FIELDSIZE=1.575000e+002`.
  - LightBurn prefs: device "B6 Mopa", `Width/Height = 157.5`.
  - `jcz15.cor` header double at 0x1C = **416.0952 = 65535 / 157.5** galvo units per mm.

  So **1 galvo unit = 2.403 µm** and **mm → unit = 416.095**. **VERIFIED.**
- **Axis orientation:**
  - LightBurn has `Galvo_1_is_X: false`, i.e. **Galvo 2 is X**. The manual also says "Switch on Galvo 2".
  - The Galvo scale, bulge, skew and trapezoid parameters are all 1. Sign is +1. Field offset 0, angle 0.
  - markcfg has `GALVOX=1`, and all `GALVO*0/1` are 1 / 100 %.

  **VERIFIED.** The exact X/Y swap and sign Raio must apply needs one red-light test (section 9, step 3).
- **Speed conversion:** galvo units per ms. 1000 mm/s → 416 units per ms. Maximum 0xFFFF ≈ 157 m/s. DOCUMENTED (`mk/controller.py:1020-1032`).

### 4.2 A vector job

Settings are emitted only when they change; meerk40t caches the last value. DOCUMENTED (`mk/controller.py:486-532, 643-708`).

```
(immediate) ResetList; WritePort(bit0=1); Fiber_SetMo(1)              # laser enable, MO open
(list) 0x8051 ReadyMark
       0x8004 DelayTime(800)            # open-MO delay 8 ms (markcfg m_nIPGOpenMoDelayTimeMs=8; LightBurn Laser_OpenMODelay 8000)
       0x8011 WritePort(bits)
       0x8006 JumpSpeed(v_jump)         # LightBurn default jump 4000 mm/s
       0x8026 PulseWidth(0, ns)         # MOPA — see packing conflict
       0x801B QSwitchPeriod(20000/kHz)
       0x8012 MarkCurrent(pct*4095/100)
       0x800C MarkSpeed(v_mark)
       0x8007 LaserOnDelay(...)  0x8008 LaserOffDelay(...)  0x800F PolygonDelay(...)
       0x8001 JumpTo(x0,y0)  0x8005 MarkTo(x1,y1) ... 
       0x8004 DelayTime(end/10)
       0x8002 EndOfList (+ padding)
(immediate) SetEndOfList; ExecuteList; poll until !BUSY; Fiber_SetMo(0); WritePort(bit0=0)
```

**Timing values LightBurn uses today** (prefs, device "B6 Mopa"): **VERIFIED**

| Setting | Value |
|---|---|
| Laser-on TC | **−300 µs** (negative: laser fires before the mirrors arrive) |
| Laser-off TC | 100 µs |
| End TC | 300 µs |
| Polygon TC | 100 µs |
| Jump delay min / max | 500 / 500 µs |
| Frame speed | 3000 mm/s |
| Max speed | 7000 mm/s |

### 4.3 What the board does NOT do (Raio does it in software)

All of these are DOCUMENTED (meerk40t does them in `core/` before calling the controller). The board only knows jump, mark and timing.

- **Wobble:** converted to a dense zig-zag or circle polyline of MarkTo points. Example: the studio's 0.30 mm size, 0.03 mm step.
- **Fill / hatch:** line generation, angle, interval, bidirectional, cross-hatch.
- **Passes and "Global Passes":** repeat the list, either inside one list or as separate list executions. **For Z-per-pass, use separate executions** (section 5.5).
- **Optimisation:** ordering and direction.
- **Raster:** pixels become MarkTo segments with per-segment power, or LaserOnPoint dots.
- **Arc tessellation:** markcfg `ARCTOL=0.01`, `MINLINELEN=0.01`.

### 4.4 Power, frequency, pulse width on the JPT M7 60 W

- Power is 12 bit on 0x8012. Frequency is a 16-bit period on 0x801B. 1–4000 kHz is within range, but resolution is coarse at the top: 4000 kHz = 5 ticks, 3333 kHz = 6 ticks. DOCUMENTED / derived.
- LightBurn fiber settings (prefs): `Laser_Type 1`, `Laser_FiberType 1`, `Laser_QPulseWidthEnabled true`, `Laser_PWMEnabled true`, freq min 1 / max 4000. EZCAD: `LASERTYPE=3`. Lmc1 runs IPG-MO logic when its laser type is 3, so **3 = Fiber** in EZCAD's numbering. Also `m_bEnableIPGSetPulseWidth=1`. **VERIFIED.** The manual says Fiber Type must be "IPG_YLP" or "JPT" for MOPA.
- Pulse widths the studio actually uses: 6, 200, 500 ns (`MATERIAL-SETTINGS.md`; LightBurn CutList `QPulseWidth` 100/200/500). **VERIFIED.**
- The JPT M7 pulse-width table: **not found in any local file.** meerk40t's combo offers 1, 2, 4, 6, 9, 13, 20, 30, 45, 55, 60, 80, 100, 150, 200, 250 (`mk/device.py:618-640`). The list in the brief (…350, 500) is unconfirmed. The source accepts only its own discrete set. Lmc1 has `IPGGetPulseWidthMaxIndex` and `IPGGetPulseWidth`, so the table may be readable from the source via 0x2F / 0x30. **INFERRED.** Test in section 9, step 6.

### 4.5 The correction file (`jcz15.cor`)

The .cor file corrects the galvo's geometric distortion; the board applies it in hardware.

- **Format (VERIFIED by parsing the file):**
  - 33840 bytes, magic `"JCZ_COR_2_1"` at offset 0.
  - **Scale double at 0x1C = 416.0952** (units per mm).
  - **Table at 0x24:** 65 × 65 pairs of little-endian **int32 (dx, dy)**, row-major.
  - Trailer: one int32 = 7.
  - Ranges: dx −1753..+2014, dy −1007..+1008. The centre point is 0,0.
  - LightBurn also knows `JCZ_COR_3_1` and `LMC1COR_1.0` (doubles), and so does meerk40t.
- **Upload (DOCUMENTED, identical in meerk40t and Balor):**
  1. `WriteCorTable(1)`.
  2. For each of the 4225 points: `WriteCorLine(dx', dy', 0 for first else 1)`, sent **without** reading a reply.
  3. Sign encoding: **sign-magnitude in 16 bits**, `v' = v if v ≥ 0 else (−v + 0x8000)`.

  Balor seeks to 0x24, and meerk40t reads 0x16 + 0xE = 0x24, so the two agree. The vendor `MIO_WriteCorTable(E, H, short[65][65][2], G)` confirms the 65×65×2 shape. **VERIFIED.**
- **⚠️ Local finding:** LightBurn's `CorrectionFile` setting points to an old Dropbox folder (`…/B6 MOPA/EZCAD for ComMarker B6 MOPA 2/jcz15.cor`), and **that path no longer exists** (the Dropbox moved to `~/Library/CloudStorage`). LightBurn may be running the B6 **uncorrected** today, or from a cached copy. Raio should load `EZ/jcz15.cor` (md5 `be209d694f845bfbf47aa92c2bd8b4fd`). **VERIFIED** (that the path is missing).
- Balor adds an optional second calibration: a measured-grid RBF ("calfile") on top of the .cor. Raio doesn't need it now; it's a future accuracy upgrade. DOCUMENTED (bryce.pw).

---

## 5. Extended axes and Z (the critical part)

### 5.1 What the board can do: proven from EZCAD's own code

Disassembly of `EZ/LMCMIO.dll` and `EZ/Lmc1.dll` (`CLmcDev::AxisMoveToGoal`, `New_MIO_MoveAxisTo`, `SetAxisAccTime`). **VERIFIED.**

1. **Speed** goes first: `0x26 SetAxisMotionParam(min_pps, max_pps)`. Both are u16 pulses per second; min is clamped ≥ 1 and max ≥ min.
2. **Acceleration and flags:** `0x27 SetAxisOriginParam(acc_ms, flags)`. acc_ms is clamped 1..65535 from `AXISACCTIME`. The flags are built from per-axis config bits (section 3.1).
3. **Close the MO first.** If the laser is fiber (type 3) and a flag is set, EZCAD sends `IPG_OpenMO(0)` before moving.
4. **Move:** `0x29 MoveAxisTo`.
   - v1 = pos & 0xFFFF.
   - v2 = (pos >> 16) | **0x4000 if axis ≠ 0**.
   - **pos is in pulses, absolute, sign-magnitude:** bit 31 = negative, |pos| ≤ 0x7FFFFF (8 388 607). Beyond that EZCAD returns error 0x78.
   - If a per-axis config flag (CLmcDev+0x10C54+4·axis) is set, EZCAD flips bit 31. The flip itself is VERIFIED. That the flag is "reverse direction" is INFERRED.
5. **Wait:** poll status until **0x40 (AXIS)** clears.
6. **Abort:** on ESC or space EZCAD sends `Reset` (0x40).
7. **Read position:** `0x2A GetAxisPos(axis)` → w1 | w2<<16 (sign-magnitude), per meerk40t. **Homing:** `0x28 AxisGoOrigin(axis)`.

meerk40t's `rotary_to` / `rotary_relative` console commands (`mk/galvo_commands.py:672-737`) implement steps 1, 2, 4 and 5 for axis 0, with defaults min 100, max 5000, acc 100. That matches the vendor format exactly, with flags = 0. **DOCUMENTED, and consistent with VERIFIED.**

> ⚠️ **galvoplotter bug:** `rotary_position` computes `pos[1] << 16 & pos[2]`, which is wrong. Use meerk40t's `pos[1] | pos[2] << 16`.

**This machine's axis settings** (`EZ/plug/markcfg7`): **VERIFIED**

| Setting | Axis 0 | Axis 1 |
|---|---|---|
| Active | **1** | 0 |
| Pulses per rev | 200 | 200 |
| Distance per rev | 5 mm (40 pulses/mm) | 5 mm |
| Min / max position | −1000 / +1000 | same |
| Min speed / max speed / max G00 speed | 100 / 5000 / 5000 | same |
| Zero (home) speed | 100 | same |
| Acc time | 100 ms | same |
| Home | `AXISZEROFLAG=0` (no homing), `AXISZERODIR=−1` | same |
| Rotate | `AXISROTATE=0` | same |
| Timeout | 10 s | same |

`EZCAD.CFG` move dialog defaults: 200 pulses per unit, 5 mm, speed 10000.

These look like **EZCAD's generic defaults**. The same markcfg7 was copied through ComMarker's B4 110 mm and other folders (`EZ/cfglog.txt`, UTF-16). They are **not** measured values for any Z column.

### 5.2 What LightBurn does with Z on this board

- **LightBurn 2.1.00 contains the full UI** for galvo Z: "Enable Z Axis Control", "Motor 1 / Motor 2", "Steps per unit count", "Accel time", "Min/Max steps per sec", "Homing…", "Galvo Z Control" toolbar. It also has an "External Axis Setup" with home-low-valid, home-dir-positive, limit-enable and limit-low-valid flags, plus `external0_*` and `external1_*` (two axes). The strings are the evidence. **VERIFIED.**
- **But "EZCad2 Galvo Z Control" was pulled from the 2.1.00 release:** "we decided this feature was not yet ready to go live… will return soon™". In 2.1, Z jogging ships **only for EZCad3** boards, and per-pass Z is promised "in a future update". As of July 2026 staff said "month(s)". **DOCUMENTED** ([New in 2.1](https://docs.lightburnsoftware.com/2.1/NewFeatures/NewIn2.1), [forum 190767](https://forum.lightburnsoftware.com/t/galvo-z-axis-control-addition-timeline/190767), [forum 161991 p.9](https://forum.lightburnsoftware.com/t/z-control-for-galvo/161991?page=9)).
- Edson's LightBurn prefs contain **no Z settings** for the B6 (`SaveRotaryConfig false`). **VERIFIED.**
- B6-specific thread: "Dropping Z per pass on Commarker B6" got the answer "At this current time, no" ([forum 169851](https://forum.lightburnsoftware.com/t/dropping-z-per-pass-on-commarker-b6/169851)). DOCUMENTED.

**So today nothing on this Mac moves the B6's Z by software.** Edson moves focus by hand on the column panel. `MATERIAL-SETTINGS.md` mentions "~200 passes split across focus drops" and the panel reading "Real focal length 255.15 mm". **VERIFIED.**

### 5.3 Is the B6 Z column wired to the board's axis output? Probably not

Evidence:

- **The column has its own controller.** The B6 manual (pp. 11–12) describes a "Controlling Page" (Lift up / Auto focus / Lift down / Stop) and a "Setting Page":
  - speed **12.5 mm/s**, screw pitch **8 mm**, **200 pulses per revolution**;
  - focal length, and "Real focal length" read from an **inner distance sensor (range 120–280 mm)**;
  - "parameters will be stored **by the control board** by clicking OK".

  That is a stand-alone motion controller with a rangefinder. **VERIFIED** (manual).
- **The column connects to "the back of the machine" with a Type-C cable** (manual p.7). We don't know whether that cable carries only power and button signals, or step/dir from the LMC board. **UNKNOWN.**
- The LMC board's axis pulse/dir goes to the rear **"Rotary" aviation port** (R5 note, Peter Verdone's LMCV4 CON4 pin 14/15). **DOCUMENTED.**
- The column's 8 mm pitch does not match markcfg's 5 mm/rev, and EZCAD has no "Z axis" setting, only the generic axis 0. **VERIFIED.**

**Conclusion (INFERRED, high confidence):** the column is driven by its own panel controller, and the LMC axis output goes to the Rotary port. **Raio sending 0x29 will most likely turn a rotary, not lift the head.**

### 5.4 How to settle it on the machine

Do this with the laser disabled (MO closed, port bit 0 off), nothing on the bed, and the R5 rotary unplugged.

1. Read `GetAxisPos(0)` and `GetAxisPos(1)`. Record them.
2. `SetAxisMotionParam(100, 500)`, `SetAxisOriginParam(100, 0)`, then `MoveAxisTo(axis 0, +200 pulses)`. Watch the **column** and the **Rotary port** (a scope, LED or multimeter on PUL). Poll until the AXIS bit clears. If nothing moved, repeat for axis 1 (v2 |= 0x4000).
3. Trace the column's Type-C: does it go to the LMC board or to a separate PCB? Photograph it.
4. Check whether the column panel has a USB or serial service port. Some of these focus controllers expose a UART.

### 5.5 Raio's Z plan

**If the column follows 0x29 (case A):**
- Raio runs each pass as its own list execution.
- Between passes: wait until !BUSY → `Fiber_SetMo(0)` → 0x26 → 0x27 → 0x29 to the new absolute pulse count → poll the AXIS bit (timeout 10 s) → next pass.
- Pulses per mm must be measured. The panel's 200 pulses per rev and 8 mm pitch suggest 25 pulses/mm *if* the board drives the same driver without microstepping. INFERRED; measure with a dial gauge.

**If the column is independent (case B, expected), options in order of cleanliness:**

1. **Talk to the column controller directly**, if its Type-C or panel exposes serial. That needs one more reverse-engineering session: sniff the panel bus.
2. **Drive the column from the board's Rotary port.** Put a step/dir driver on the column stepper (an MKS driver is on hand, see R5 note), switched in place of the panel controller. Raio then uses 0x26–0x29 as in case A. You lose the panel's autofocus sensor, but you can keep it as a separate reference.
3. **Separate Z controller.** An ESP32 or Arduino with its own driver on the column motor, sequenced by Raio between passes. This doesn't depend on the LMC protocol at all. The forum users who got per-pass Z with LightBurn galvos did exactly this (GRBL Arduino).
4. **Button emulation:** an LMC output port bit drives an optocoupler across "Lift down" for a timed pulse. Cheap, but open-loop and imprecise (12.5 mm/s). Last resort.

### 5.6 What ComMarker Studio does

`/Applications/ComMarker_Studio.app` v1.0.42 (Qt, x86_64, unsigned, `com.yourcompany.ComMarker_Studio`; was running as pid 75977, untouched).

- **USB transport:** `Frameworks/libtransfer.dylib`. It links IOKit directly, and it also contains libusb code compiled in: the `LIBUSB_ERROR_*` strings, and symbols such as `libusbLogCallback(libusb_context*, …)` and `print_endpoint_info(libusb_device_handle*, libusb_device*)`, which come from libusb's own darwin backend over IOKit. It also has UDP/TCP transports. The class is `UsbTransfer(UsbControlParam*)`, with `openDev`, `getDeviceList`, `readPortCore`, `writePortCore` and `initHotplugSock`. `UsbTransfer::getDeviceList` and `openDev` accept only **VID 0x04B4 / PID 0x1004** or **VID 0x7580 / PID 0x0101** (disassembly 0xcf4d–0xcf6c, 0xd736–0xd759). **No 0x9588 anywhere** in the main binary or any dylib. **VERIFIED.**
- The SDK is BSL's **"LCS"** (`SDK Version LCS2.1.8595`, log `Resources/Data/logs/20261021.txt`). Its components are `libexecutor` (`Executor5`/`Executor7`, FPGA version, card registration and trial), `liblcsDI` (`LcsLmcParam` — "Lmc" here is BSL's own naming), `libBslCal`, `libBSL3DMark`, and `libfpgaUpdate`. Its default .cor paths mention `ComMarker_Studio_omnix_win_v1.0.21`, and the updater points to `bsl-autoupdate…/KMK/mac` with an OEM/Mecpow icon. **VERIFIED.**
- Its Z and focus code shows how ComMarker's *BSL* machines (Omni X and similar) do it:
  - `LcsClientProcess::doMoveAxisPulse(LcsDev, ExtAxisPar, int, bool)` and `Section3DControl::doMoveAxisPulse` move an external axis by pulses;
  - `ExtAxisDriverPar`, `LcsAxisExtParam`;
  - `LcsClientProcess::doRedFocus` and `setFocusState`;
  - UI: "Adjust Z-axis", "Z axis descending distance" (Z per pass), "AutoFocus", `autoFocusGpi`, `cmbautoFocusInput/Output` (autofocus wired through a GPIO input and output on the controller), "Conflict with focus output port", `FocusDistanceRange`, `MarkSet::Vision_AutoFocus` (camera), and `m_LmcPara.IsGALVO_B`.

  **VERIFIED** (strings and `nm`).
- **Relevance to Raio:** it is not a template for the BJJCZ protocol. It does confirm that ComMarker's own design pattern for "Z per pass" is **an external stepper axis pulsed by the galvo controller, plus an autofocus sensor on a GPIO**. That is option 2 in section 5.5. It also suggests why LightBurn's LibUSB device for the B6 may someday expose the same feature.
- Its config (`Resources/Data/config/lcsparam*.cfg`, `lcsdefparam.cfg`) is **obfuscated binary**, not readable. No ComMarker Studio files exist in `~/Library/Preferences` or `~/Library/Application Support`. Logs and config are written inside the app bundle. **VERIFIED.**

---

## 6. IO

### 6.1 This machine's port configuration

From `EZ/plug/markcfg7`, cross-checked against LightBurn prefs. **VERIFIED.**

| Function | EZCAD markcfg7 | LightBurn | Meaning |
|---|---|---|---|
| Start-mark (foot switch) input | `STARTMARKPORT=14`, `STARTSIGNALPULSEMODE=1` (pulse = press and release), high-valid | `StartMarkPortBit 14`, `StartMarkPulseMode true` | **The foot pedal is input bit 14** (meerk40t's default is 15; change it) |
| Red light output | `REDLIGHTOUTPORT=-1` (not a GPIO) | `RedLightPortBit -1` | The red pointer uses the board's default red-light line. Balor and meerk40t toggle **output bit 8 (0x100)** for it. DOCUMENTED |
| Laser enable | (internal) | – | Output **bit 0** on during marking (meerk40t `port_on(bit=0)`). DOCUMENTED |
| Door interlock input | `DOORINPORT=-1` (`m_nDoorInportLowValid=1`) | `DoorProtectPortBit -1` | **No door interlock wired or configured.** The B6 is an open frame |
| Red-light input switch | `REDLIGHTINPORT=-1` | – | none |
| Mark busy / finish outputs | `MARKOUTPORT=-1`, `MARKFINISHOUTPORT=-1` | `BusyPortBit -1`, `DoneMarkPortBit -1` | none |
| Laser-ready in/out, alarm out | all −1 | `ReadyPortBit -1` | none |
| Stop input | `STOPIOHIGH=0`, `STOPIOLOW=0` | `StopMarkPortBit -1` | none |
| Fly start input | `FLY_STARTINPORT=8` (fly marking disabled) | – | unused |
| IO masks | `INPUTIOMASK=255`, `OUTPUTIOMASK=255` (EZCAD.CFG) | – | |
| **Air assist** | no port | no port | **The board does not control air assist on this setup.** The pump is switched by hand. To automate it, wire a relay to a spare output bit (e.g. 1–7) and drive it with WritePort / 0x8011. INFERRED |
| Emergency stop | Hardware button on the machine (manual p.7, "keep the emergency button not pressed") | – | Hardware cut, outside the protocol |

### 6.2 Reading inputs

- `ReadPort` (0x25) returns 4 words. Balor treats **w0 bit 15 (0x8000)** as the footswitch (`bal/sender.py read_port`). meerk40t's `wait_for_input` matches a pattern against all four words. Which word and bit carry input 14 on this board is **INFERRED** (probably w0 bit 14). To verify, poll ReadPort at 10 Hz while pressing the pedal.
- The `InputPort` (0x31) lock modes latch short presses. EZCAD sets `m_bEnableLockInputport=1`. DOCUMENTED.
- `listWaitForInput` (0x8022, mask, level) can pause a list on an input. That is a possible hardware hold-to-run gate. VERIFIED (opcode).
- **Safety:** with no door input and no interlock, **Raio must provide the safety logic in software**:
  - an arm step before the laser can fire;
  - a big STOP that sends the abort sequence;
  - MO closed and bit 0 low whenever idle;
  - a refusal to fire unless the red-light frame ran first (LightBurn has `RequireFrameBeforeStart: true`).

### 6.3 Red-light preview

- **Mechanism:** a list with port bit 8 on and laser bit 0 off, MO closed, made of only `JumpTo`s at the red-light speed. LightBurn `FrameSpeed 3000`; markcfg `REDLIGHTSPEED=3000`. The list is looped: re-sent whenever READY && !BUSY (Balor `LightingHelper`, meerk40t `light_mode`). DOCUMENTED.
- The red offset and scale are all 0 / 1 (markcfg `REDLIGHTOFFSET*`, LightBurn `RedDot*`). **VERIFIED.**
- **Known B6 issue:** LightBurn 2.1-RC framing on this board drew only a straight line (section 1.1). Raio's first red-light rectangle is the test that this board accepts the jump list (section 9, step 3).

---

## 7. What LightBurn actually does, and what Raio needs

**What LightBurn does with this device** (all VERIFIED from prefs and strings):

- **Device:** "B6 Mopa" (plus a "B6 Mopa 2.0" duplicate), protocol `JCZFiber`, transport LibUSB.
- **Config source:** markcfg7 imported ("Import EZCad2 Config" → `markcfg7`). The manual (pp. 13–15) gives the steps, ending with Freq min 1 / max 4000, Galvo 2 on, and Q-Pulse Width on.
- **Startup:** detects the board type through its signature, then runs "Running startup sequence (LMC4)" etc.
- **Correction file:** the .cor upload (the path is now broken, see 4.5).
- **Timing:** delays from `Default_*_TC`, jump speed 4000, `Galvo_*` geometry 1.0.
- **Laser settings:** cut settings with speed, power, frequency, QPulseWidth, passes, global repeat, wobble (size/step), interval (hatch).
- **Framing:** required before Start.
- **Foot pedal:** input 14.

**Raio must replicate:**

- connect;
- the init sequence;
- the .cor upload;
- red-light frame;
- vector mark with speed, power, frequency and pulse width;
- passes;
- wobble and hatch in software;
- abort and pause;
- status polling;
- optional foot-pedal start;
- **Z between passes** (once 5.4 is settled).

**Raio can skip:**

- the dongle;
- fly marking and encoder;
- DA-Z / dynamic focus (0x39–0x3B, 0x8029);
- CO2 and UV paths (0x800A, 0x800B, 0x801E);
- SPI simmer;
- weld waves;
- the camera;
- split marking;
- the 2nd laser source;
- analog outputs;
- the clone FPGA loader (not needed on a genuine 9899 board);
- rotary, until the R5 is used.

---

## 8. Reusable code

### 8.1 Licences

| Source | Licence | Use in Raio |
|---|---|---|
| meerk40t `balormk/` (`controller.py`, `usb_connection.py`) | **MIT** (`LICENSE`, © 2021 meerk40t) | **Vendor** these two files, adapted: strip the kernel `service`/`channel` plumbing, keep the opcode tables, list packing, unit conversions, cor reader and init order. Keep the MIT notice. |
| galvoplotter (`galvo/controller.py`, `usb_connection.py`, `consts.py`) | **MIT** (© 2023 MeerK40t) | Cleaner stand-alone version of the same controller, already free of meerk40t: **the best starting point.** Fix the `rotary_position` bug. `pip install galvoplotter` exists, but vendor it instead. |
| Balor (`gitlab.com/bryce15/balor`, `balor/sender.py`, `command_list.py`, `BJJCZ_LMCV4_FIBER_M*.py`, `Documentation/ThreeOvals.pcap`) | **GPL-3.0-or-later**, © 2021 Gnostic Instruments; commercial licence by contact | **Reference only.** Do not copy code unless Raio is GPL. The pcap is useful to compare traffic. |
| EZCAD `Lmc1.dll` / `LMCMIO.dll` | Proprietary (BJJCZ) | Read-only reference: opcode and argument layouts, as done here. Never redistribute. |

### 8.2 Minimal skeleton (pseudo-Python; opcodes as in section 3)

```python
import struct, time, usb.core, usb.util
VID, PID, EP_OUT, EP_IN = 0x9588, 0x9899, 0x02, 0x88
FIELD_MM = 157.5; U_PER_MM = 65535 / FIELD_MM          # 416.095
NOP = struct.pack("<6H", 0x8002, 0, 0, 0, 0, 0)
LASER_BIT, RED_BIT = 0, 8                                # DOCUMENTED (balor/meerk40t)
BUSY, READY, AXIS = 0x04, 0x20, 0x40

class LMC:
    def connect(self):
        self.d = usb.core.find(idVendor=VID, idProduct=PID)
        if self.d is None: raise IOError("B6 not on USB")
        self.d.set_configuration()                       # fails 'busy' if LightBurn holds it
        usb.util.claim_interface(self.d, 0)
        self.ports = 0
    def cmd(self, op, *a, read=True):
        a = list(a) + [0] * (5 - len(a))
        self.d.write(EP_OUT, struct.pack("<6H", op, *a), 100)
        return struct.unpack("<4H", bytes(self.d.read(EP_IN, 8, 100))) if read else None
    def status(self): return self.cmd(0x0007, 0x0100)[3]
    def wait(self, bit, want=False, timeout=30):
        t = time.time()
        while bool(self.status() & bit) != want:
            if time.time() - t > timeout: self.abort(); raise TimeoutError
            time.sleep(0.01)

    # ---- init + correction ----
    def init(self, cor_path):
        print("serial", self.cmd(0x0009), "version", self.cmd(0x0007, 0x0100))
        self.cmd(0x0034)                                 # Fiber_GetStMO_AP (EZCAD does)
        self.cmd(0x0040)                                 # Reset (meerk40t/Balor); EZCAD capture sends 0x0003 here
        self.upload_cor(cor_path)
        self.cmd(0x0004)                                 # EnableLaser
        for op, *a in [(0x16, 0), (0x1B, 1), (0x17, 1), (0x1C, 1), (0x1D, 2000, 20),
                       (0x1A, 200), (0x1E, 125), (0x06, 125), (0x33, 0),
                       (0x2E, 0xFFB, 1, 409, 100), (0x32, 0, 99, 1000, 25)]:
            self.cmd(op, *a)                             # values from Balor's EZCAD capture (Raycus); tune vs markcfg7
        self.write_port()                                # 0x21 (0, 0)
        self.cmd(0x003A); self.cmd(0x0022, 0x7FF); self.cmd(0x003A)   # EZCAD's exact init tail — keep
    def upload_cor(self, path):
        b = open(path, "rb").read(); assert b[:11] == b"JCZ_COR_2_1"
        vals = struct.unpack_from("<8450i", b, 0x24)
        sm = lambda v: (v if v >= 0 else -v + 0x8000) & 0xFFFF
        self.cmd(0x0015, 1)
        for i in range(4225):
            self.cmd(0x0010, sm(vals[2*i]), sm(vals[2*i+1]), 0 if i == 0 else 1, read=False)

    # ---- ports ----
    def write_port(self): self.cmd(0x0021, self.ports, 0)
    def bit(self, n, on): self.ports = self.ports | (1 << n) if on else self.ports & ~(1 << n)

    # ---- lists ----
    def run_list(self, cmds):                            # cmds: list of (op, v1..v5)
        self.wait(BUSY, False); self.cmd(0x0012)         # ResetList
        cmds = [(0x8051,)] + cmds + [(0x8002,)]
        started = False
        for n, k in enumerate(range(0, len(cmds), 256)):
            chunk = b"".join(struct.pack("<6H", *(list(c) + [0] * (6 - len(c)))) for c in cmds[k:k+256])
            chunk += NOP * (256 - len(cmds[k:k+256]))
            self.wait(READY, True); self.d.write(EP_OUT, chunk, 1000)
            self.cmd(0x0019, 0)                          # SetEndOfList (args ignored: EZCAD sends stale words)
            if n == 1:                                   # EZCAD: ExecuteList after the 2nd packet
                self.cmd(0x0005); started = True         # (meerk40t: after 3rd; Balor: after every packet)
        if not started: self.cmd(0x0005)
        self.cmd(0x0016, 1)                              # SetControlMode(1) at end, as EZCAD
        self.wait(BUSY, False)

    def mm(self, x, y):                                  # field centre = (0,0); swap/sign per §9 step 3
        return int(0x8000 + x * U_PER_MM), int(0x8000 + y * U_PER_MM)
    spd = lambda self, mm_s: min(0xFFFF, int(mm_s * U_PER_MM / 1000))

    # ---- red light outline of a rectangle ----
    def red_rect(self, x0, y0, x1, y1, loops=20):
        self.cmd(0x0033, 0); self.bit(LASER_BIT, False); self.bit(RED_BIT, True)
        pts = [self.mm(x0, y0), self.mm(x1, y0), self.mm(x1, y1), self.mm(x0, y1), self.mm(x0, y0)]
        self.write_port()                                # EZCAD: immediate WritePort(0x100) before lighting
        L = [(0x8006, self.spd(3000)), (0x800C, self.spd(3000))] + \
            [(0x8001, x, y, 0, min(0xFFFF, int(((x-px)**2 + (y-py)**2) ** 0.5)))
             for (px, py), (x, y) in zip([pts[0]] + pts[:-1], pts)]
        for _ in range(loops): self.run_list(L)
        self.bit(RED_BIT, False); self.write_port()

    # ---- mark one line ----
    def mark_line(self, a, b, speed, power_pct, freq_khz, pulse_ns):
        self.bit(RED_BIT, False); self.bit(LASER_BIT, True); self.write_port()
        dist = lambda p, q: min(0xFFFF, int(((p[0]-q[0])**2 + (p[1]-q[1])**2) ** 0.5))
        A, B, C = self.mm(*a), self.mm(*b), (0x8000, 0x8000)
        L = [(0x8026, 0, pulse_ns),                      # vendor layout — see §3.2 conflict
             (0x801B, round(20000 / freq_khz)),
             (0x8012, round(power_pct * 0xFFF / 100)),
             (0x8006, self.spd(4000)), (0x800C, self.spd(speed)),
             (0x8007, 300, 0x8000), (0x8008, 100), (0x800F, 10),   # LightBurn: on −300, off 100, poly 100 µs
             (0x8001, *A, 0, dist(C, A)),
             (0x8021, 1), (0x8004, 800),                 # MO open + 8 ms (EZCAD does this in-list)
             (0x8005, *B, 0, dist(A, B)),
             (0x8004, 30), (0x8021, 0),                  # end delay 300 µs, MO closed
             (0x8001, *C, 0, dist(B, C))]                # distance word must be filled (Bryce notes)
        try: self.run_list(L)
        finally: self.safe_idle()

    def safe_idle(self):
        self.cmd(0x0033, 0); self.bit(LASER_BIT, False); self.write_port()

    def abort(self):
        self.cmd(0x001F); self.cmd(0x0033, 0); self.cmd(0x0012)
        self.d.write(EP_OUT, struct.pack("<6H", 0x8051, 0, 0, 0, 0, 0) + NOP * 255, 1000)
        self.cmd(0x0019, 0); self.cmd(0x0005); self.safe_idle(); self.cmd(0x000D, 0x8000, 0x8000)

    # ---- extended axis (Z if wired — §5.4) ----
    def axis_pos(self, axis=0):
        w = self.cmd(0x002A, axis); p = w[1] | (w[2] << 16)
        return -(p & 0x7FFFFFFF) if p & 0x80000000 else p
    def axis_move_mm(self, mm, pulses_per_mm, axis=0, vmin=100, vmax=500, acc_ms=100):
        target = self.axis_pos(axis) + round(mm * pulses_per_mm)
        assert abs(target) <= 0x7FFFFF
        p = (abs(target) | (0x80000000 if target < 0 else 0))
        self.cmd(0x0033, 0)                              # MO closed, as EZCAD does
        self.cmd(0x0026, vmin, vmax); self.cmd(0x0027, acc_ms, 0)
        self.cmd(0x0029, p & 0xFFFF, (p >> 16) | (0x4000 if axis else 0))
        self.wait(AXIS, False, timeout=10)               # vendor polls bit 0x40; abort = cmd(0x0040)
```

---

## 9. Risks, unknowns, and the test plan on the real machine

### 9.1 Risks, highest first

1. **Board revision / signature.** The B6 60 W MOPA reports a signature LightBurn didn't know, and red-light framing misbehaved. Opcodes or startup parameters may differ from the LMCV4-FIBER-M that Balor and meerk40t were built on. *Mitigation:* read-only identification first; a red light before any laser.
2. **Z is not on this board** (section 5.3). Per-pass Z may need hardware work (options 5.5 B1–B4). This is the biggest scope risk for Raio.
3. **0x8026 pulse-width layout conflict** (vendor vs meerk40t). With the wrong layout, MOPA settings silently do nothing. Recipes such as copper at 200–500 ns would be wrong.
4. **No interlocks** (door −1, no ready or alarm inputs). A software bug can fire the laser. *Mitigation:* MO closed and bit 0 low by default; every job path in `try/finally: safe_idle()`; abort on exception; a physical E-stop within reach.
5. **Init values:** the meerk40t generic defaults vs this markcfg7 (FPK 40 µs, tickle 5000/1). With the wrong standby/tickle values the source may pre-lase or misbehave. Mitigation: compare against a capture.
6. **List protocol details:** `SetEndOfList` argument, when to send `ExecuteList`, the 0x8051 header. The two projects differ. Under-runs could stall mid-job, leaving the laser parked on a spot.
7. **The .cor path in LightBurn is broken.** Today's recipes may have been made uncorrected. Expect a small geometry difference when Raio applies `jcz15.cor`.
8. **The port bit map is not confirmed on this board:** red bit 8, laser bit 0, input bit 14 → ReadPort word and bit.
9. **USB exclusivity with LightBurn:** only one app at a time. Raio must handle a busy device gracefully.
10. **Ground truth.** Balor's `balor/BJJCZ_LMCV4_FIBER_M_blobs.py` already holds a complete EZCAD capture (init, lighting, mark, end) from an LMCV4-FIBER-M with a Raycus source, decoded in 2.4 and 2.5. `Documentation/ThreeOvals.pcap` is the raw pcap. Neither comes from a JPT MOPA or from this board revision, so MOPA-specific traffic (0x8026, the JPT startup values) is still uncaptured. **Capturing more is hard on macOS.** LightBurn is hardened, so DYLD interposition is blocked. macOS USB capture through Wireshark needs the XHC interface, which recent macOS restricts. The practical route to a capture is **EZCAD2 on a Windows PC or VM with USB passthrough plus Wireshark/USBPcap**. Balor's `Documentation/ThreeOvals.pcap` is a reference trace from an LMCV4-FIBER-M.

### 9.2 Test plan

Safe and incremental: goggles on, scrap only, fume extraction, E-stop in reach, LightBurn closed.

| Step | Laser? | Do | Pass criterion |
|---|---|---|---|
| 0 | off | ✅ **Done 2026-10-21:** USBLMCV4, 9588:9899, four bulk endpoints 0x01/0x81/0x02/0x88 at 512 bytes, no kernel driver, pyusb sees it (section 1.2). | Done |
| 1 | off | Read-only: `GetSerialNo`, `GetVersion(0x0100)`, `GetListStatus`, `ReadPort`, `GetPositionXY`, `GetAxisPos(0/1)`, `Fiber_GetStMO_AP`. Log the raw words. | Replies are 8 bytes; READY set, BUSY clear. Compare the serial words with `0000238409002002`. |
| 2 | off | Press and release the foot pedal while polling ReadPort at 10 Hz. | Find the word and bit for input 14. |
| 3 | red only | `init()` with `jcz15.cor` → `GotoXY` centre → red-light rectangle 0,0 → 50×20 mm, then an L-shape with arms of different length. | A rectangle (not a line); the long arm along the expected axis. Measure on paper: 50.0 mm ±0.2. Fix X/Y swap and sign. |
| 4 | red only | Red frame at the four field corners (±70 mm). | Inside the bed, square. Edges straight (the .cor is working). |
| 5 | **on, low** | Scrap steel, focused. One **1 mm line**: 500 mm/s, **10 %**, 30 kHz, 200 ns. Abort test: start a 20 s pattern and hit STOP. | Faint line, 1.0 mm; abort stops instantly; MO closed afterwards (ReadPort / `Fiber_GetStMO_AP`). |
| 6 | on | **Pulse-width discriminator:** two 5×5 mm squares, everything identical, 4 ns vs 200 ns, vendor layout `[0x8026, 0, ns]`. If they look the same, repeat with the meerk40t layout. Then compare one known recipe against the same recipe from LightBurn. | Visibly different squares. Record which layout works. |
| 7 | on | Passes: 3 passes as one list vs 3 executions; wobble polyline; hatch fill. | Same result as LightBurn at the same settings. |
| 8 | off, rotary unplugged | **Axis test (section 5.4):** `axis_move_mm` of +200 pulses on axis 0, then axis 1. Watch the column and Rotary port PUL. | Settles whether Z is on the board. If not, pick a 5.5 B option. |
| 9 | on | (only if Z works) A 10-pass job with −0.1 mm Z per pass on scrap. | Z steps between passes, never during a mark. |

---

## Sources

**Local** (all under `ROOT/studio/B6-Mopa/files/install/B6 MOPA/` unless noted):

- `driver/{win_10,win11/X64AMD_LmcV2u,win_7 32}/*.inf`
- `EZCAD for ComMarker B6 MOPA/plug/markcfg7` (board config, text)
- `…/EZCAD.CFG`
- `…/jcz15.cor`
- `…/cfglog.txt` (UTF-16)
- `…/Usb.log`
- `…/plug/{home.par,RotaryMark.par}`
- `…/Lmc1.dll` and `…/LMCMIO.dll` (exports and disassembly)
- `Users' manual ComMarker B6.pdf`
- `studio/B6-Mopa/{README.md,R5-ROTARY.md,MATERIAL-SETTINGS.md}`
- `~/Library/Preferences/LightBurn/prefs.ini`
- `/Applications/LightBurn.app` (strings, `otool`, `codesign`)
- `/Applications/ComMarker_Studio.app` (strings, `nm`, disassembly of `libtransfer.dylib`, logs)

**Code:**

- meerk40t `balormk` — https://github.com/meerk40t/meerk40t (MIT)
- galvoplotter — https://github.com/meerk40t/galvoplotter (MIT)
- Balor — https://gitlab.com/bryce15/balor (GPL-3.0+; commit dfc7faf, 2022-11-06; local clone `/private/tmp/claude-501/raio-proto/balor-gitlab`). Files used:
  - `readme.html`
  - `Documentation/notes.odt` (opcode notes)
  - `Documentation/scratch 1.odt` (EZCAD list dumps)
  - `Documentation/ThreeOvals.pcap`
  - `balor/sender.py` (init, execute, abort, cor reader at 0x24)
  - `balor/BJJCZ_LMCV4_FIBER_M.py` (endpoints, status bits)
  - `balor/BJJCZ_LMCV4_FIBER_M_blobs.py` (captured EZCAD traffic, decoded as data with `ast.literal_eval`, never imported)
  - `balor/command_list.py`

  Where Balor and meerk40t differ, both are recorded above:
  - SetEndOfList args;
  - when ExecuteList is sent;
  - opcode 0x40 (Balor `IS_LITE_VERSION` vs meerk40t `Reset`);
  - 0x39/0x3A naming (Balor: `ENABLE_Z_2` / `ENABLE_Z`, "AutoFocus on/off?");
  - footswitch read (Balor `ReadPort w0 & 0x8000`).

**Web:**

- Bryce Schroeder, "Fiber Laser Engravers" — https://www.bryce.pw/engraver.html (same text as `balor/readme.html`)
- LightBurn docs, *New in 2.1* — https://docs.lightburnsoftware.com/2.1/NewFeatures/NewIn2.1
- LightBurn docs, *Ports and Laser Settings (Galvo)* — https://docs.lightburnsoftware.com/2.1/Reference/DeviceSettings/GalvoPorts/
- LightBurn forum threads 189558, 169851, 161991 (p.9), 190767, 179854, 189731 (linked inline)
