# raio · USB tap (parked 2026-10-21)

**Status: parked, no code built.** ComMarker Studio 1.0.42 only opens USB IDs 04B4:1004 and 7580:0101 (BSL controllers for the Omni X). It never opens our BJJCZ 9588:9899 and fails with "Device is invalid [0x10000021]" before any transfer, so there is nothing to capture. The design below is ready if a host app that does talk to 9588 turns up, for example EZCAD in a Windows VM or a future ComMarker build.

## What we found in the app
- The app is **x86_64 and runs under Rosetta** on the M4 Max. Frida does not inject well into Rosetta processes. `sudo` also needs a password and Developer Mode is off, so a debugger attach is not possible either.
- `Contents/Frameworks/libtransfer.dylib` has **libusb (darwin backend) statically linked** and exported (`_libusb_bulk_transfer`, `_libusb_submit_transfer`, ...). The only IOKit imports are `IOCreatePlugInInterfaceForService`, `IOServiceGetMatchingServices`, `IOServiceAddMatchingNotification`, `IORegistryEntryCreateCFProperty`, `IOServiceAuthorize`, and similar.
- I/O path: `UsbTransfer::writePortCore` / `readPortCore` call `_libusb_bulk_transfer` **directly inside the image** (a `callq`, not through a stub). DYLD interposing therefore cannot catch libusb calls.
- The framing is the vendor's own, not Balor's: `TransferPackage` (header, seq, checksum, msg channel, `BOARD_PROTOCOL`) and `Transfer::writeCmd/writeData/readPort/writeAndReadCmd`. Commands are built by `libexecutor.dylib` (`LcsCmd(u16 opcode)` with `setParam0..4`, `LcsCmdList`, `Executor::*` such as `gotoPositionAbs`, `sendMarkPara`, `sendSpiPower`, `getDevInfo`). Consumers of libtransfer are libexecutor, libmark, liblcsDI, libBSL3DMark, libfpgaUpdate, and the main binary.
- `Transfer::m_bLogData` (exported data symbol) and `TransLogHandler::write/read` show that the app has its own data logger. Setting the flag via `dlsym` would make it log the payloads itself.

## Tap design (ready to build if ever needed)
Build an x86_64 `DYLD_INSERT_LIBRARIES` dylib. The app is unsigned with no hardened runtime, so no sudo is needed.
1. Interpose `IOCreatePlugInInterfaceForService`. This works because it is a real import.
2. Copy the returned plugin's vtable to malloc'd memory, keep a pointer to the original vtable at `[-1]`, and wrap `QueryInterface`. Never mprotect the original vtable.
3. When QueryInterface returns an IOUSBInterfaceInterface (match the UUID against IDs 100 through 942 and copy `sizeof` of that version), wrap `WritePipe(TO|Async|AsyncTO)` and `ReadPipe(...)`. Log OUT payloads at submit. For IN, swap the callback and refcon and log `buf[0..arg0]` when the transfer completes. Wrap `ControlRequest*` and the device's `DeviceRequest*` the same way.
4. Map pipeRef to endpoint by wrapping `GetPipeProperties(V2/V3)` as libusb itself calls them. Never call them ourselves.
5. Logging must be lock-light and use a writer thread. Each line is `seq ts_ms DIR ep len hex(<=64, else first 64 + len)`, plus a binary sidecar with full payloads.

Launch with `DYLD_INSERT_LIBRARIES=<dylib> "<App>.app/Contents/MacOS/<binary>"`, not with `open`. Build with `clang -arch x86_64 -dynamiclib -framework IOKit -framework CoreFoundation`.

## Device facts (read from descriptors with pyusb, no writes)
USBLMCV4 9588:9899 has interface 0, class 0xFF. Its bulk endpoints in descriptor order are 0x01, 0x81, 0x02 and 0x88, all with 512-byte max packets, so pipeRef 1..4 map to those endpoints. Chrome (pid 70636) also held a device-level user client on it on 2026-10-21, probably from WebUSB enumeration.

## Balor reference (for a decoder)
The source is meerk40t `meerk40t/balormk/controller.py` (commit d511944, 2026-09-25), with constants at lines 26-112. `usb_connection.py` sends **both commands and lists to OUT 0x02** and reads status from **IN 0x88**. A command is 12 bytes: u16 opcode LE followed by 5 u16 args. A list packet is 0xC00 = 3072 bytes, made of 256 × 12-byte entries. Status bits are BUSY 0x04, READY 0x20 and AXIS 0x40.
Command opcodes include 0x0007 GetVersion, 0x0009 GetSerialNo, 0x000A GetListStatus, 0x000C GetPositionXY, 0x000D GotoXY, 0x0012 ResetList, 0x0005 ExecuteList, 0x0021 WritePort, 0x0025 ReadPort and 0x0040 Reset.
List opcodes include 0x8001 JumpTo, 0x8002 EndOfList, 0x8005 MarkTo, 0x8006 JumpSpeed, 0x800C MarkSpeed, 0x800B MarkPowerRatio, 0x800A MarkFreq and 0x8051 ReadyMark. The full table is in that file.
