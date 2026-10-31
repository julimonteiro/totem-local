import Cocoa
import WebKit
import SwiftUI

final class FloatingPanel: NSPanel {
    override var canBecomeKey: Bool { false }
    override var canBecomeMain: Bool { false }
}

final class AppDelegate: NSObject, NSApplicationDelegate, WKNavigationDelegate, WKScriptMessageHandler, NSMenuDelegate {
    var editor: NSWindow!
    var overlay: FloatingPanel!
    var statusItem: NSStatusItem!
    var backend: Process?
    let base = "http://127.0.0.1:8767"
    let root: String = {
        let besideApp = Bundle.main.bundleURL.deletingLastPathComponent()
        if FileManager.default.fileExists(atPath: besideApp.appendingPathComponent("local/server.py").path) { return besideApp.path }
        return FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent("TOTEM Local").path
    }()
    var retries = 0
    let liveModel = LiveModel()

    func applicationDidFinishLaunching(_ notification: Notification) {
        do { try prepareWorkspace() } catch { fail("Não foi possível preparar os arquivos locais: \(error.localizedDescription)"); return }
        NSApp.setActivationPolicy(.regular)
        let menu = NSMenu()
        let appItem = NSMenuItem()
        menu.addItem(appItem)
        let appMenu = NSMenu()
        appMenu.delegate = self
        let toggle = appMenu.addItem(withTitle: "Painel flutuante", action: #selector(toggleOverlay), keyEquivalent: "1")
        toggle.target = self
        appMenu.addItem(withTitle: "Abrir editor", action: #selector(showEditor), keyEquivalent: "2")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Sair do TOTEM Local", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appItem.submenu = appMenu
        NSApp.mainMenu = menu
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        statusItem.button?.title = "⌨ TOTEM"
        let statusMenu = appMenu.copy() as! NSMenu
        statusMenu.delegate = self
        statusItem.menu = statusMenu
        waitForServer()
    }

    var architecture: String {
#if arch(arm64)
        return "arm64"
#else
        return "x86_64"
#endif
    }
    func prepareWorkspace() throws {
        guard let resources = Bundle.main.resourceURL else { return }
        let seed = resources.appendingPathComponent("Workspace")
        guard FileManager.default.fileExists(atPath: seed.path) else { return }
        let destination = URL(fileURLWithPath: root)
        // Development checkout already owns its source and configuration.
        if destination == Bundle.main.bundleURL.deletingLastPathComponent() { return }
        try FileManager.default.createDirectory(at: destination, withIntermediateDirectories: true)
        for folder in ["local", "telemetry", "config", "artifacts"] {
            let from = seed.appendingPathComponent(folder)
            let to = destination.appendingPathComponent(folder)
            if !FileManager.default.fileExists(atPath: from.path) { continue }
            if FileManager.default.fileExists(atPath: to.path) {
                if folder == "config" || folder == "artifacts" { continue }
                try FileManager.default.removeItem(at: to)
            }
            try FileManager.default.copyItem(at: from, to: to)
        }
    }

    func waitForServer() {
        let url = URL(string: base + "/api/state")!
        var request = URLRequest(url: url)
        request.timeoutInterval = 2
        URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
            DispatchQueue.main.async {
                guard let self = self else { return }
                if let response = response as? HTTPURLResponse, response.statusCode == 200 {
                    self.createWindows()
                    return
                }
                if self.retries == 0 {
                    let process = Process()
                    let embedded = Bundle.main.resourceURL!.appendingPathComponent("Python-" + self.architecture + "/python/bin/python3.13")
                    let devPython = URL(fileURLWithPath: self.root + "/.venv/bin/python")
                    process.executableURL = FileManager.default.fileExists(atPath: embedded.path) ? embedded : (FileManager.default.fileExists(atPath: devPython.path) ? devPython : URL(fileURLWithPath: "/usr/bin/python3"))
                    process.arguments = ["-B", self.root + "/local/server.py"]
                    var env = ProcessInfo.processInfo.environment
                    env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
                    env["PYTHONDONTWRITEBYTECODE"] = "1"
                    env["PYTHONNOUSERSITE"] = "1"
                    env.removeValue(forKey: "PYTHONPATH")
                    env.removeValue(forKey: "PYTHONHOME")
                    process.environment = env
                    process.currentDirectoryURL = URL(fileURLWithPath: self.root)
                    let logPath = self.root + "/server.log"
                    if !FileManager.default.fileExists(atPath: logPath) { FileManager.default.createFile(atPath: logPath, contents: nil) }
                    if let log = FileHandle(forWritingAtPath: logPath) {
                        log.seekToEndOfFile()
                        process.standardOutput = log
                        process.standardError = log
                    }
                    do { try process.run(); self.backend = process }
                    catch { self.fail("Não foi possível iniciar o serviço local: \(error.localizedDescription)"); return }
                }
                self.retries += 1
                if self.retries > 15 { self.fail("O serviço local não iniciou. Confira o arquivo server.log na pasta TOTEM-Local."); return }
                DispatchQueue.main.asyncAfter(deadline: .now() + 1) { self.waitForServer() }
            }
        }.resume()
    }

    func createWindows() {
        guard editor == nil else { return }
        editor = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1180, height: 830), styleMask: [.titled,.closable,.miniaturizable,.resizable], backing: .buffered, defer: false)
        editor.title = "TOTEM Local · Editor"
        editor.minSize = NSSize(width: 800, height: 650)
        editor.isReleasedWhenClosed = false
        editor.contentView = editorContent()
        editor.center()
        overlay = FloatingPanel(contentRect: NSRect(x: 0, y: 0, width: 840, height: 350), styleMask: [.titled,.closable,.resizable,.nonactivatingPanel], backing: .buffered, defer: false)
        overlay.title = "TOTEM · Mapa ao vivo"
        overlay.standardWindowButton(.zoomButton)?.isHidden = true
        overlay.standardWindowButton(.miniaturizeButton)?.isHidden = true
        overlay.standardWindowButton(.closeButton)?.isHidden = false
        overlay.level = .floating
        overlay.collectionBehavior = [.canJoinAllSpaces,.fullScreenAuxiliary]
        overlay.hidesOnDeactivate = false
        overlay.isReleasedWhenClosed = false
        overlay.minSize = NSSize(width: 650, height: 335)
        liveModel.start()
        overlay.contentView = NSHostingView(rootView: NativeOverlay(model: liveModel))
        overlay.isOpaque = false
        overlay.backgroundColor = .clear
        overlay.titlebarAppearsTransparent = true
        overlay.setFrameAutosaveName("TotemOverlay")
        if let frame = NSScreen.main?.visibleFrame {
            overlay.setFrameOrigin(NSPoint(x: frame.maxX - 860, y: frame.minY + 30))
        }
        showEditor()
        showOverlay()
    }

    func editorContent() -> NSView {
        let stack = NSStackView()
        stack.orientation = .vertical
        stack.spacing = 0
        stack.alignment = .width
        let label = NSTextField(labelWithString: "Teste de digitação do macOS")
        label.font = .systemFont(ofSize: 12, weight: .medium)
        let input = NSTextField(string: "")
        input.placeholderString = "Clique aqui e digite com o TOTEM"
        input.font = .systemFont(ofSize: 14)
        input.bezelStyle = .roundedBezel
        input.setAccessibilityIdentifier("totem-macos-typing-test")
        let row = NSStackView(views: [label, input])
        row.orientation = .horizontal
        row.spacing = 16
        row.edgeInsets = NSEdgeInsets(top: 12, left: 24, bottom: 12, right: 24)
        row.heightAnchor.constraint(equalToConstant: 56).isActive = true
        input.widthAnchor.constraint(greaterThanOrEqualToConstant: 350).isActive = true
        stack.addArrangedSubview(row)
        let web = webView(path: "/")
        web.setContentHuggingPriority(.defaultLow, for: .vertical)
        stack.addArrangedSubview(web)
        return stack
    }

    func webView(path: String) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.userContentController.add(self, name: "bluetooth")
        let view = WKWebView(frame: .zero, configuration: config)
        view.navigationDelegate = self
        view.setValue(false, forKey: "drawsBackground")
        view.load(URLRequest(url: URL(string: base + path)!))
        return view
    }

    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        let url = navigationAction.request.url
        decisionHandler(url?.host == "127.0.0.1" && url?.port == 8767 ? .allow : .cancel)
    }

    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        if message.name == "bluetooth" { liveModel.connectBluetooth() }
    }
    @objc func showOverlay() { overlay?.orderFrontRegardless() }
    @objc func toggleOverlay() {
        guard let overlay = overlay else { return }
        if overlay.isVisible { overlay.orderOut(nil) }
        else { overlay.orderFrontRegardless() }
    }
    func menuWillOpen(_ menu: NSMenu) {
        for item in menu.items where item.action == #selector(toggleOverlay) {
            item.state = overlay?.isVisible == true ? .on : .off
        }
    }
    @objc func showEditor() { editor?.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true) }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { false }
    func applicationWillTerminate(_ notification: Notification) { backend?.terminate() }
    func fail(_ message: String) {
        let alert = NSAlert(); alert.messageText = "TOTEM Local"; alert.informativeText = message
        alert.runModal(); NSApp.terminate(nil)
    }
}
#if !TOTEM_MENU_TEST
@main
struct TotemMain {
    static func main() {
        let app = NSApplication.shared
        let delegate = AppDelegate()
        app.delegate = delegate
        withExtendedLifetime(delegate) { app.run() }
    }
}
#endif
