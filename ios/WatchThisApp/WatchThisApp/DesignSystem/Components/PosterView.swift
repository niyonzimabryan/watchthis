import SwiftUI

struct PosterView: View {
    let posterURL: URL?
    let title: String

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: WTSpacing.cardRadius, style: .continuous)
                .fill(
                    LinearGradient(
                        colors: [WTColor.accentTeal.opacity(0.9), WTColor.accentCoral.opacity(0.9), WTColor.accentGold.opacity(0.75)],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )

            if let posterURL {
                AsyncImage(url: posterURL) { phase in
                    switch phase {
                    case .success(let image):
                        image
                            .resizable()
                            .scaledToFill()
                    case .failure:
                        placeholder
                    case .empty:
                        placeholder.shimmering()
                    @unknown default:
                        placeholder
                    }
                }
            } else {
                placeholder
            }
        }
        .frame(maxWidth: .infinity)
        .aspectRatio(2.0 / 3.0, contentMode: .fit)
        .clipShape(RoundedRectangle(cornerRadius: WTSpacing.cardRadius, style: .continuous))
    }

    private var placeholder: some View {
        VStack(spacing: WTSpacing.sm) {
            Text(initials)
                .font(.system(size: 34, weight: .bold, design: .rounded))
                .foregroundStyle(Color.white)
            Text("WatchThis")
                .font(WTTypography.caption())
                .foregroundStyle(Color.white.opacity(0.85))
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var initials: String {
        let tokens = title.split(separator: " ")
        let letters = tokens.prefix(2).compactMap { $0.first }
        return letters.isEmpty ? "WT" : String(letters)
    }
}
