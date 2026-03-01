import SwiftUI

struct FilterChip: View {
    let label: String
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(label)
                .font(WTTypography.caption())
                .foregroundStyle(isSelected ? WTColor.bgCard : WTColor.inkPrimary)
                .padding(.horizontal, WTSpacing.sm)
                .padding(.vertical, WTSpacing.xs)
                .background(isSelected ? WTColor.accentTeal : WTColor.bgCard)
                .overlay(
                    RoundedRectangle(cornerRadius: WTSpacing.buttonRadius, style: .continuous)
                        .stroke(isSelected ? WTColor.accentTeal : WTColor.inkSecondary.opacity(0.18), lineWidth: 1)
                )
                .clipShape(RoundedRectangle(cornerRadius: WTSpacing.buttonRadius, style: .continuous))
        }
        .frame(minHeight: 44)
        .accessibilityAddTraits(isSelected ? .isSelected : [])
    }
}
