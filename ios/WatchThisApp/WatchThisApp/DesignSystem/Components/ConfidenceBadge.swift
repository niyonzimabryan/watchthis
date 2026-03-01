import SwiftUI

struct ConfidenceBadge: View {
    let confidence: Double

    var body: some View {
        let pct = Int((confidence * 100).rounded())
        HStack(spacing: WTSpacing.xs) {
            Circle()
                .fill(WTColor.successMint)
                .frame(width: 8, height: 8)
            Text("\(pct)% match")
                .font(WTTypography.caption())
                .foregroundStyle(WTColor.inkPrimary)
        }
        .padding(.horizontal, WTSpacing.sm)
        .padding(.vertical, WTSpacing.xs)
        .background(WTColor.successMint.opacity(0.14))
        .clipShape(Capsule())
        .accessibilityLabel("Confidence \(pct) percent")
    }
}
