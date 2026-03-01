import SwiftUI

enum WTColor {
    static let bgPrimary = Color(hex: "#F7F6F2")
    static let bgCard = Color(hex: "#FFFFFF")
    static let inkPrimary = Color(hex: "#1F2937")
    static let inkSecondary = Color(hex: "#4B5563")
    static let accentCoral = Color(hex: "#E86E6E")
    static let accentTeal = Color(hex: "#2F7F7A")
    static let accentGold = Color(hex: "#D9A441")
    static let successMint = Color(hex: "#5BAE8A")
    static let warningRose = Color(hex: "#C65E6A")
}

extension Color {
    init(hex: String) {
        let sanitized = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: sanitized).scanHexInt64(&int)

        let r, g, b: UInt64
        switch sanitized.count {
        case 6:
            (r, g, b) = (int >> 16, int >> 8 & 0xFF, int & 0xFF)
        default:
            (r, g, b) = (31, 41, 55)
        }

        self.init(
            .sRGB,
            red: Double(r) / 255.0,
            green: Double(g) / 255.0,
            blue: Double(b) / 255.0,
            opacity: 1.0
        )
    }
}
