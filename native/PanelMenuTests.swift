import Cocoa

@main
struct PanelMenuTests {
    static func main() {
        let app = NSApplication.shared
        app.setActivationPolicy(.accessory)
        let delegate = AppDelegate()
        delegate.overlay = FloatingPanel(contentRect: NSRect(x: -10000, y: -10000, width: 1, height: 1), styleMask: [.nonactivatingPanel], backing: .buffered, defer: false)
        delegate.overlay.isReleasedWhenClosed = false
        let menu = NSMenu()
        let item = menu.addItem(withTitle: "Painel flutuante", action: #selector(AppDelegate.toggleOverlay), keyEquivalent: "1")
        item.target = delegate
        let copy = menu.copy() as! NSMenu
        delegate.menuWillOpen(menu)
        precondition(item.state == .off)
        delegate.toggleOverlay()
        precondition(delegate.overlay.isVisible)
        precondition(!delegate.overlay.canBecomeKey && !delegate.overlay.canBecomeMain)
        delegate.menuWillOpen(copy)
        precondition(copy.items[0].state == .on)
        delegate.toggleOverlay()
        precondition(!delegate.overlay.isVisible)
        delegate.menuWillOpen(menu)
        precondition(item.state == .off)
        delegate.showOverlay()
        delegate.overlay.close()
        delegate.menuWillOpen(copy)
        precondition(copy.items[0].state == .off)
        delegate.toggleOverlay()
        precondition(delegate.overlay.isVisible)
        delegate.overlay.orderOut(nil)
        print("Panel menu: show, hide, close/reopen and focus checks passed")
    }
}
