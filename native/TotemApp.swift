import Cocoa
import WebKit
import SwiftUI
import UserNotifications

final class FloatingPanel: NSPanel {
    override var canBecomeKey: Bool { false }
    override var canBecomeMain: Bool { false }
}

final class AppDelegate: NSObject, NSApplicationDelegate, WKNavigationDelegate, WKScriptMessageHandler, NSMenuDelegate, NSWindowDelegate {
    var editor: NSWindow!
    var overlay: FloatingPanel!
    var statusItem: NSStatusItem!
    var editorWebView: WKWebView?
    var tutorialRequested = false
    var backend: Process?
    let base = "http://127.0.0.1:8767"
    let root: String = {
        let besideApp = Bundle.main.bundleURL.deletingLastPathComponent()
        if FileManager.default.fileExists(atPath: besideApp.appendingPathComponent("local/server.py").path) { return besideApp.path }
        return FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent("TOTEM Local").path
    }()
    var retries = 0
    let liveModel = LiveModel()
    var preferences = UserDefaults.standard
    var panelMode: PanelMode { PanelMode(rawValue: preferences.string(forKey: "panelMode") ?? "automatic") ?? .automatic }
    var hidePanel: DispatchWorkItem?
    var batteryPolicy = BatteryPolicy()
    var assistanceRequested: String?


    func applicationDidFinishLaunching(_ notification: Notification) {
        do { try prepareWorkspace() } catch { fail("Não foi possível preparar os arquivos locais: \(error.localizedDescription)"); return }
        NSApp.setActivationPolicy(.regular)
        if let resources = Bundle.main.resourceURL,
           let icon = NSImage(contentsOf: resources.appendingPathComponent("AppIcon.icns")) { NSApp.applicationIconImage = icon }
        let menu = NSMenu()
        let appItem = NSMenuItem()
        menu.addItem(appItem)
        let appMenu = NSMenu()
        appMenu.delegate = self
        let toggle = appMenu.addItem(withTitle: "Painel flutuante", action: #selector(toggleOverlay), keyEquivalent: "1")
        toggle.target = self
        appMenu.addItem(withTitle: "Abrir editor", action: #selector(showEditor), keyEquivalent: "2")
        let tutorial = appMenu.addItem(withTitle: "Tutorial de adaptação", action: #selector(showTutorial), keyEquivalent: "3")
        tutorial.target = self
        for (title, mode) in [("Automático por camada", PanelMode.automatic), ("Sempre visível", .always), ("Oculto", .hidden)] {
            let item = appMenu.addItem(withTitle: title, action: #selector(selectPanelMode(_:)), keyEquivalent: "")
            item.target = self; item.representedObject = mode.rawValue
        }
        for (title, section) in [("Como faço…?", "search"), ("Treino adaptativo", "practice"), ("Perfis de layout", "profiles"), ("Diagnóstico", "diagnostics")] {
            let item = appMenu.addItem(withTitle: title, action: #selector(openAssistance(_:)), keyEquivalent: "")
            item.target = self; item.representedObject = section
        }
        let alerts = appMenu.addItem(withTitle: "Avisos de bateria", action: #selector(toggleBatteryAlerts), keyEquivalent: "")
        alerts.target = self
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
        overlay.delegate = self
        batteryPolicy.levels = preferences.dictionary(forKey: "batteryLevels") as? [String:Int] ?? [:]
        liveModel.onUpdate = { [weak self] data in
            guard let self = self else { return }
            self.applyPanelState(live: self.liveModel.live, layer: self.liveModel.activeLayer)
            self.checkBatteries(data)
        }
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
        applyPanelState(live: liveModel.live, layer: liveModel.activeLayer)
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
        editorWebView = web
        web.setContentHuggingPriority(.defaultLow, for: .vertical)
        stack.addArrangedSubview(web)
        return stack
    }

    func webView(path: String) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.userContentController.add(self, name: "bluetooth")
        config.userContentController.add(self, name: "exportKeymap")
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
        if message.name == "exportKeymap", let data = message.body as? [String:Any], let source = data["source"] as? String, source.utf8.count <= 200000 {
            let panel = NSSavePanel(); panel.nameFieldStringValue = "totem-layout.keymap"
            panel.beginSheetModal(for: editor) { response in
                if response == .OK, let url = panel.url {
                    do { try source.write(to: url, atomically: true, encoding: .utf8) }
                    catch { let alert = NSAlert(); alert.messageText = "Não foi possível exportar"; alert.informativeText = error.localizedDescription; alert.beginSheetModal(for: self.editor) }
                }
            }
        }
    }
    @objc func showTutorial() {
        showEditor()
        tutorialRequested = true
        editorWebView?.evaluateJavaScript("window.TotemTutorial ? (window.TotemTutorial.open(), true) : false") { [weak self] result, _ in
            if result as? Bool == true { self?.tutorialRequested = false }
        }
    }
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        if webView === editorWebView && tutorialRequested { showTutorial() }
        if let section = assistanceRequested { showAssistance(section) }
    }
    @objc func showOverlay() { setPanelMode(.always) }
    @objc func toggleOverlay() { setPanelMode(overlay?.isVisible == true ? .hidden : .always) }
    @objc func selectPanelMode(_ item: NSMenuItem) {
        if let raw = item.representedObject as? String, let mode = PanelMode(rawValue: raw) { setPanelMode(mode) }
    }
    func setPanelMode(_ mode: PanelMode) {
        preferences.set(mode.rawValue, forKey: "panelMode")
        applyPanelState(live: liveModel.live, layer: liveModel.activeLayer)
    }
    func applyPanelState(live: Bool, layer: Int) {
        if OverlayPolicy.visible(mode: panelMode, live: live, layer: layer) {
            hidePanel?.cancel(); hidePanel = nil; overlay?.orderFrontRegardless()
        } else if panelMode == .automatic && live && overlay?.isVisible == true {
            if hidePanel == nil {
                let work = DispatchWorkItem { [weak self] in self?.overlay?.orderOut(nil); self?.hidePanel = nil }
                hidePanel = work; DispatchQueue.main.asyncAfter(deadline: .now()+0.35, execute: work)
            }
        } else { hidePanel?.cancel(); hidePanel = nil; overlay?.orderOut(nil) }
    }
    func windowWillClose(_ notification: Notification) {
        if notification.object as? NSWindow === overlay { setPanelMode(.hidden) }
    }
    @objc func openAssistance(_ item: NSMenuItem) { showAssistance(item.representedObject as? String ?? "search") }
    func showAssistance(_ section: String) {
        guard ["search", "practice", "profiles", "diagnostics"].contains(section) else { return }
        showEditor(); assistanceRequested = section
        editorWebView?.evaluateJavaScript("window.TotemAssistance ? (window.TotemAssistance.open('\(section)'), true) : false") { [weak self] result, _ in
            if result as? Bool == true { self?.assistanceRequested = nil }
        }
    }
    @objc func toggleBatteryAlerts() {
        if preferences.bool(forKey: "batteryAlerts") { preferences.set(false, forKey: "batteryAlerts"); showBatteryNotice(""); return }
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert,.sound]) { [weak self] granted, _ in
            DispatchQueue.main.async {
                self?.preferences.set(true, forKey: "batteryAlerts")
                self?.showBatteryNotice(granted ? "Avisos de bateria ativados." : "Notificações não autorizadas. Os avisos aparecerão no app.")
            }
        }
    }
    func showBatteryNotice(_ text: String) {
        liveModel.batteryNotice = text
        if let encoded = try? JSONSerialization.data(withJSONObject: [text]), let json = String(data: encoded, encoding: .utf8) {
            editorWebView?.evaluateJavaScript("document.dispatchEvent(new CustomEvent('totem:battery',{detail:\(json)[0]}))")
        }
    }
    func checkBatteries(_ data: [String:Any]) {
        let sides = data["sides"] as? [String:[String:Any]] ?? [:]
        var warnings: [String] = []
        for side in ["left", "right"] {
            let d = sides[side] ?? [:]
            let percentage = (d["battery"] as? NSNumber)?.intValue ?? -1
            if let warning = BatteryPolicy.warning(side: side, percentage: percentage, fresh: d["fresh"] as? Bool ?? false, enabled: preferences.bool(forKey: "batteryAlerts")) { warnings.append(warning) }
            guard preferences.bool(forKey: "batteryAlerts") else { continue }
            if let value = batteryPolicy.observe(side: side, percentage: percentage, fresh: d["fresh"] as? Bool ?? false) {
                let label = side == "left" ? "esquerda" : "direita"
                let text = "Metade \(label): \(value)% de bateria."
                let content = UNMutableNotificationContent(); content.title = "TOTEM · hora de carregar"; content.body = text; content.sound = .default
                UNUserNotificationCenter.current().add(UNNotificationRequest(identifier: "battery-"+side, content: content, trigger: nil))
            }
        }
        let currentWarning = warnings.joined(separator: " · ")
        if liveModel.batteryNotice != currentWarning { showBatteryNotice(currentWarning) }
        preferences.set(batteryPolicy.levels, forKey: "batteryLevels")
    }
    func menuWillOpen(_ menu: NSMenu) {
        for item in menu.items {
            if item.action == #selector(toggleOverlay) { item.state = overlay?.isVisible == true ? .on : .off }
            if item.action == #selector(selectPanelMode(_:)) { item.state = (item.representedObject as? String) == panelMode.rawValue ? .on : .off }
            if item.action == #selector(toggleBatteryAlerts) { item.state = preferences.bool(forKey: "batteryAlerts") ? .on : .off }
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
