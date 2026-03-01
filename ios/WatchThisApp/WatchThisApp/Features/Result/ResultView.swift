import SwiftUI

struct ResultView: View {
    @Bindable var coordinator: AppCoordinator
    @Environment(\.openURL) private var openURL
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var appeared = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: WTSpacing.lg) {
                if let response = coordinator.currentResponse {
                    card(response)
                        .scaleEffect(reduceMotion || appeared ? 1.0 : 0.96)
                        .opacity(appeared ? 1.0 : 0.0)
                        .onAppear {
                            withAnimation(.spring(response: 0.45, dampingFraction: 0.82)) {
                                appeared = true
                            }
                        }
                }

                if coordinator.isLoading {
                    loadingCard
                }

                if let error = coordinator.errorMessage {
                    ErrorCard(message: error) {
                        Task { await coordinator.spinAgain() }
                    }
                }

                actionButtons
            }
            .padding(.horizontal, WTSpacing.md)
            .padding(.vertical, WTSpacing.md)
        }
        .accessibilityIdentifier("result_screen")
        .background(WTColor.bgPrimary)
        .navigationTitle("Your Pick")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    coordinator.showHistorySheet = true
                } label: {
                    Image(systemName: "clock.arrow.circlepath")
                        .foregroundStyle(WTColor.accentTeal)
                }
            }
        }
    }

    @ViewBuilder
    private func card(_ response: RecommendationResponse) -> some View {
        VStack(alignment: .leading, spacing: WTSpacing.md) {
            PosterView(
                posterURL: response.recommendation.posterURL,
                title: response.recommendation.title
            )
            .accessibilityIdentifier("result_poster")

            HStack(alignment: .center) {
                VStack(alignment: .leading, spacing: WTSpacing.xxs) {
                    Text(response.recommendation.title)
                        .font(WTTypography.title())
                        .foregroundStyle(WTColor.inkPrimary)
                    Text(response.recommendation.displayMeta)
                        .font(WTTypography.caption())
                        .foregroundStyle(WTColor.inkSecondary)
                }
                Spacer()
                ConfidenceBadge(confidence: response.confidence)
            }

            Text(response.pitch)
                .font(WTTypography.body())
                .foregroundStyle(WTColor.inkPrimary)
                .fixedSize(horizontal: false, vertical: true)

            VStack(alignment: .leading, spacing: WTSpacing.xs) {
                Text("Where to watch")
                    .font(WTTypography.bodyStrong())
                    .foregroundStyle(WTColor.inkPrimary)

                if response.streamingSources.isEmpty {
                    Text("Find where to watch")
                        .font(WTTypography.caption())
                        .foregroundStyle(WTColor.inkSecondary)
                } else {
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: WTSpacing.xs) {
                            ForEach(response.streamingSources) { source in
                                Button {
                                    if let link = source.webUrl, let url = URL(string: link) {
                                        openURL(url)
                                    }
                                } label: {
                                    StreamingPill(name: source.name, type: source.type)
                                }
                                .buttonStyle(.plain)
                                .accessibilityLabel("Open \(source.name)")
                            }
                        }
                    }
                }
            }
        }
        .padding(WTSpacing.md)
        .background(WTColor.bgCard)
        .clipShape(RoundedRectangle(cornerRadius: WTSpacing.cardRadius, style: .continuous))
        .accessibilityIdentifier("result_card")
    }

    private var loadingCard: some View {
        VStack(alignment: .leading, spacing: WTSpacing.sm) {
            Text(coordinator.loadingMessage)
                .font(WTTypography.bodyStrong())
                .foregroundStyle(WTColor.inkPrimary)
            RoundedRectangle(cornerRadius: 10)
                .fill(WTColor.inkSecondary.opacity(0.12))
                .frame(height: 14)
                .shimmering()

            if coordinator.showSlowRequestAction {
                Button("Go back") {
                    coordinator.cancelActiveRequest()
                }
                .font(WTTypography.caption())
                .foregroundStyle(WTColor.accentTeal)
            }
        }
        .padding(WTSpacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(WTColor.bgCard)
        .clipShape(RoundedRectangle(cornerRadius: WTSpacing.cardRadius, style: .continuous))
    }

    private var actionButtons: some View {
        VStack(spacing: WTSpacing.sm) {
            PrimaryButton(title: "Spin Again", isLoading: coordinator.isLoading) {
                Task {
                    await coordinator.spinAgain()
                }
            }
            .accessibilityIdentifier("spin_again_button")

            PrimaryButton(title: "New Mood", style: .outline, isEnabled: !coordinator.isLoading) {
                coordinator.newMood()
            }
            .accessibilityIdentifier("new_mood_button")
        }
    }
}
