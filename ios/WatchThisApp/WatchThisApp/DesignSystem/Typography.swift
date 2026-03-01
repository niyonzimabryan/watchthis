import SwiftUI

enum WTTypography {
    static func hero() -> Font {
        .system(size: 34, weight: .bold, design: .rounded)
    }

    static func title() -> Font {
        .system(size: 28, weight: .bold, design: .rounded)
    }

    static func subtitle() -> Font {
        .system(size: 20, weight: .semibold, design: .rounded)
    }

    static func body() -> Font {
        .system(size: 17, weight: .regular, design: .default)
    }

    static func bodyStrong() -> Font {
        .system(size: 17, weight: .semibold, design: .default)
    }

    static func caption() -> Font {
        .system(size: 13, weight: .medium, design: .default)
    }
}
