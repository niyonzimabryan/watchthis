import SwiftUI

struct ErrorCard: View {
    let message: String
    let retryAction: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: WTSpacing.sm) {
            HStack(spacing: WTSpacing.xs) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .foregroundStyle(WTColor.warningRose)
                Text("Something went wrong")
                    .font(WTTypography.bodyStrong())
                    .foregroundStyle(WTColor.inkPrimary)
            }

            Text(message)
                .font(WTTypography.body())
                .foregroundStyle(WTColor.inkSecondary)

            Button("Try Again", action: retryAction)
                .font(WTTypography.bodyStrong())
                .foregroundStyle(WTColor.accentTeal)
                .padding(.top, WTSpacing.xs)
        }
        .padding(WTSpacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(WTColor.bgCard)
        .overlay(
            RoundedRectangle(cornerRadius: WTSpacing.cardRadius, style: .continuous)
                .stroke(WTColor.warningRose.opacity(0.25), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: WTSpacing.cardRadius, style: .continuous))
    }
}
