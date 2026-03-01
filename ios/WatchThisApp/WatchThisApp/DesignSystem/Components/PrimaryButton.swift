import SwiftUI

struct PrimaryButton: View {
    enum Style {
        case filled
        case outline
    }

    let title: String
    var style: Style = .filled
    var isEnabled: Bool = true
    var isLoading: Bool = false
    var pulse: Bool = false
    let action: () -> Void

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var pulseScale: CGFloat = 1.0

    var body: some View {
        Button(action: action) {
            HStack(spacing: WTSpacing.xs) {
                if isLoading {
                    ProgressView()
                        .progressViewStyle(.circular)
                        .tint(style == .filled ? .white : WTColor.accentTeal)
                }
                Text(title)
                    .font(WTTypography.bodyStrong())
                    .lineLimit(1)
            }
            .frame(maxWidth: .infinity, minHeight: 52)
            .padding(.horizontal, WTSpacing.md)
            .foregroundStyle(foregroundColor)
            .background(background)
            .overlay(
                RoundedRectangle(cornerRadius: WTSpacing.buttonRadius, style: .continuous)
                    .strokeBorder(borderColor, lineWidth: style == .outline ? 1.5 : 0)
            )
            .clipShape(RoundedRectangle(cornerRadius: WTSpacing.buttonRadius, style: .continuous))
            .contentShape(RoundedRectangle(cornerRadius: WTSpacing.buttonRadius, style: .continuous))
            .scaleEffect(reduceMotion || !pulse ? 1.0 : pulseScale)
        }
        .disabled(!isEnabled || isLoading)
        .accessibilityAddTraits(.isButton)
        .onAppear {
            guard pulse, !reduceMotion else { return }
            withAnimation(.easeInOut(duration: 2.0).repeatForever(autoreverses: true)) {
                pulseScale = 1.03
            }
        }
    }

    private var foregroundColor: Color {
        style == .filled ? .white : WTColor.accentTeal
    }

    private var borderColor: Color {
        style == .filled ? .clear : WTColor.accentTeal.opacity(0.35)
    }

    @ViewBuilder
    private var background: some View {
        switch style {
        case .filled:
            LinearGradient(
                colors: [WTColor.accentTeal, WTColor.accentCoral],
                startPoint: .leading,
                endPoint: .trailing
            )
        case .outline:
            WTColor.bgCard
        }
    }
}
