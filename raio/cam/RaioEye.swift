// RaioEye: the app bundle that owns the camera permission for raio (like OracleEars owns the microphone).
// It asks macOS for the camera once, then runs `cam.py serve` (a copy outside Dropbox) and keeps it alive.
// A menu-bar eye shows state: plain = serving · red = laser armed (camera blind) · yellow = server down.
import Foundation
import AVFoundation
import AppKit

let home = NSHomeDirectory()
let support = home + "/Library/Application Support/RaioEye"
let logPath = home + "/Library/Logs/raio-eye.log"
let python = home + "/.venvs/raio/bin/python"
let port = "8878"

func log(_ s: String) {
    let f = DateFormatter(); f.dateFormat = "yyyy-MM-dd HH:mm:ss"
    let line = "\(f.string(from: Date())) \(s)\n"
    if let h = FileHandle(forWritingAtPath: logPath) { h.seekToEndOfFile(); h.write(line.data(using: .utf8)!); h.closeFile() }
    else { FileManager.default.createFile(atPath: logPath, contents: line.data(using: .utf8)) }
}

var server: Process? = nil
var stopping = false

func startServer() {
    let p = Process()
    p.executableURL = URL(fileURLWithPath: python)
    p.arguments = ["-u", support + "/cam.py", "serve", "--port", port]
    p.currentDirectoryURL = URL(fileURLWithPath: support)
    let out = FileHandle(forWritingAtPath: logPath) ?? FileHandle.standardError
    out.seekToEndOfFile()
    p.standardOutput = out; p.standardError = out
    p.terminationHandler = { t in
        log("cam.py serve exited (\(t.terminationStatus))")
        if !stopping { DispatchQueue.main.asyncAfter(deadline: .now() + 3) { startServer() } }
    }
    do { try p.run(); server = p; log("cam.py serve started pid \(p.processIdentifier) on :\(port)") }
    catch { log("could not start cam.py: \(error)"); DispatchQueue.main.asyncAfter(deadline: .now() + 10) { startServer() } }
}

// ---- the eye in the menu bar ----
func eyeImage(size: CGFloat = 18) -> NSImage {
    let img = NSImage(size: NSSize(width: size, height: size), flipped: false) { r in
        let s = size / 18
        let path = NSBezierPath()
        path.move(to: NSPoint(x: 1.5*s, y: 9*s))
        path.curve(to: NSPoint(x: 16.5*s, y: 9*s), controlPoint1: NSPoint(x: 5*s, y: 15*s), controlPoint2: NSPoint(x: 13*s, y: 15*s))
        path.curve(to: NSPoint(x: 1.5*s, y: 9*s), controlPoint1: NSPoint(x: 13*s, y: 3*s), controlPoint2: NSPoint(x: 5*s, y: 3*s))
        path.lineWidth = 1.2*s
        NSColor.black.setStroke(); path.stroke()
        NSColor.black.setFill()
        NSBezierPath(ovalIn: NSRect(x: 6.5*s, y: 6.5*s, width: 5*s, height: 5*s)).fill()
        return true
    }
    img.isTemplate = true
    return img
}

final class StatusBar: NSObject {
    let item = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
    let stateLine = NSMenuItem(title: "", action: nil, keyEquivalent: "")
    var up = false; var armed = false; var cameraOK = false; var cameraName = ""
    override init() {
        super.init()
        item.autosaveName = "RaioEye"
        let m = NSMenu()
        m.addItem(stateLine); m.addItem(.separator())
        for (t, sel) in [("Open the eye (localhost:\(port))", #selector(openPage)), ("Open log", #selector(openLog)),
                         ("Restart server", #selector(restartServer)), ("Quit RaioEye", #selector(quit))] {
            let i = NSMenuItem(title: t, action: sel, keyEquivalent: ""); i.target = self; m.addItem(i)
        }
        item.menu = m
        Timer.scheduledTimer(withTimeInterval: 2, repeats: true) { [weak self] _ in self?.poll() }
        poll(); refresh()
    }
    func poll() {
        var r = URLRequest(url: URL(string: "http://127.0.0.1:\(port)/state.json")!); r.timeoutInterval = 1.5
        URLSession.shared.dataTask(with: r) { d, _, _ in
            DispatchQueue.main.async {
                if let d = d, let j = try? JSONSerialization.jsonObject(with: d) as? [String: Any] {
                    self.up = true
                    self.armed = j["armed"] as? Bool ?? false
                    self.cameraOK = j["camera"] as? Bool ?? false
                    self.cameraName = j["camera_name"] as? String ?? ""
                } else { self.up = false }
                self.refresh()
            }
        }.resume()
    }
    func refresh() {
        let (color, text): (NSColor?, String) =
            !up ? (.systemYellow, "Server down; restarting.") :
            armed ? (.systemRed, "Laser armed: the eye is closed.") :
            !cameraOK ? (.systemYellow, "Camera \(cameraName) not found.") :
            (nil, "Watching the bed through \(cameraName).")
        if let b = item.button {
            if b.image == nil { b.image = eyeImage() }
            (b.cell as? NSButtonCell)?.highlightsBy = []
            b.contentTintColor = color; b.toolTip = text
        }
        stateLine.title = text
    }
    @objc func openPage() { NSWorkspace.shared.open(URL(string: "http://localhost:\(port)/")!) }
    @objc func openLog() { NSWorkspace.shared.open(URL(fileURLWithPath: logPath)) }
    @objc func restartServer() { log("restart from menu"); server?.terminate() }
    @objc func quit() { stopping = true; server?.terminate(); exit(0) }
}

AVCaptureDevice.requestAccess(for: .video) { ok in
    log("camera permission: \(ok)")
    DispatchQueue.main.async { startServer() }
}
NSApplication.shared.setActivationPolicy(.accessory)
let statusBar = StatusBar()
log("RaioEye started")
NSApplication.shared.run()
