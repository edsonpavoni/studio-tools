// iPadTools: the app-bundle stub that launchd starts. It only runs
// ~/Library/Application Support/iPadTools/supervisor.py and waits, so that the
// TCC grant (Full Disk Access / Dropbox) given to this app covers the Python
// servers it spawns, the way Terminal's grant covers what you run in it.
// Nothing here changes when supervisor.py changes: the grant survives updates.
import Foundation

var child: Process? = nil
signal(SIGTERM) { _ in child?.terminate(); child?.waitUntilExit(); exit(0) }
signal(SIGINT)  { _ in child?.terminate(); child?.waitUntilExit(); exit(0) }

let home = FileManager.default.homeDirectoryForCurrentUser.path
let script = home + "/Library/Application Support/iPadTools/supervisor.py"
let p = Process()
p.executableURL = URL(fileURLWithPath: "/usr/bin/env")
p.arguments = ["python3", script]
var env = ProcessInfo.processInfo.environment
env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
env["PYTHONUNBUFFERED"] = "1"
p.environment = env
p.currentDirectoryURL = URL(fileURLWithPath: home + "/Library/Application Support/iPadTools")
child = p
do { try p.run() } catch { FileHandle.standardError.write("iPadTools: cannot run \(script): \(error)\n".data(using: .utf8)!); exit(78) }
p.waitUntilExit()
exit(p.terminationStatus)
