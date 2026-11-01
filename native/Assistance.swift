import Cocoa
import UserNotifications

enum PanelMode: String { case automatic, always, hidden }
struct OverlayPolicy {
    static func visible(mode: PanelMode, live: Bool, layer: Int) -> Bool {
        mode == .always || (mode == .automatic && live && layer > 0)
    }
}
struct BatteryPolicy {
    static func warning(side: String, percentage: Int, fresh: Bool, enabled: Bool) -> String? {
        guard enabled, fresh, (0...20).contains(percentage) else { return nil }
        return "Metade \(side == "left" ? "esquerda" : "direita"): \(percentage)% de bateria."
    }
    var levels: [String:Int] = [:]
    mutating func observe(side: String, percentage: Int, fresh: Bool) -> Int? {
        guard fresh, (0...100).contains(percentage) else { return nil }
        if percentage > 25 { levels[side] = 0; return nil }
        let level = percentage <= 10 ? 2 : percentage <= 20 ? 1 : 0
        guard level > (levels[side] ?? 0) else { return nil }
        levels[side] = level
        return percentage
    }
}
