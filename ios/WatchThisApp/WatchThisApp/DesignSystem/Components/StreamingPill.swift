import SwiftUI

struct StreamingPill: View {
    let name: String
    let type: String

    var body: some View {
        HStack(spacing: WTSpacing.xs) {
            Image(systemName: iconName)
                .font(.system(size: 12, weight: .bold))
            Text(name)
                .font(WTTypography.caption())
        }
        .foregroundStyle(WTColor.bgCard)
        .padding(.horizontal, WTSpacing.sm)
        .padding(.vertical, WTSpacing.xs)
        .background(WTColor.accentTeal)
        .clipShape(Capsule())
    }

    private var iconName: String {
        switch type.lowercased() {
        case "free":
            return "gift.fill"
        case "rent", "buy":
            return "dollarsign.circle.fill"
        case "info":
            return "info.circle.fill"
        default:
            return "play.circle.fill"
        }
    }
}
