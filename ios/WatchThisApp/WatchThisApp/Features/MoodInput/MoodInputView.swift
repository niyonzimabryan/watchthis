import SwiftUI

struct MoodInputView: View {
    @Bindable var coordinator: AppCoordinator

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: WTSpacing.lg) {
                header
                moodCard
                filtersCard
                actionButtons
                statusBlock
            }
            .padding(.horizontal, WTSpacing.md)
            .padding(.top, WTSpacing.md)
            .padding(.bottom, WTSpacing.xl)
        }
        .background(WTColor.bgPrimary)
        .navigationTitle("Pick For Tonight")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    coordinator.showHistorySheet = true
                } label: {
                    Image(systemName: "clock.arrow.circlepath")
                        .foregroundStyle(WTColor.accentTeal)
                }
                .accessibilityLabel("Open history")
                .accessibilityIdentifier("history_button")
            }
#if DEBUG
            ToolbarItem(placement: .topBarLeading) {
                Menu {
                    ForEach(AppMode.allCases) { mode in
                        Button(mode.title) {
                            coordinator.setDebugModeOverride(mode)
                        }
                    }
                    Button("Use Build Default") {
                        coordinator.setDebugModeOverride(nil)
                    }
                } label: {
                    Text(coordinator.effectiveMode.title)
                        .font(WTTypography.caption())
                        .foregroundStyle(WTColor.accentGold)
                }
            }
#endif
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: WTSpacing.xs) {
            Text("What are you in the mood for?")
                .font(WTTypography.title())
                .foregroundStyle(WTColor.inkPrimary)
            Text("Describe your vibe in one sentence. We will return one recommendation.")
                .font(WTTypography.body())
                .foregroundStyle(WTColor.inkSecondary)
        }
    }

    private var moodCard: some View {
        VStack(alignment: .leading, spacing: WTSpacing.sm) {
            Text("Mood")
                .font(WTTypography.bodyStrong())
                .foregroundStyle(WTColor.inkPrimary)

            TextEditor(text: $coordinator.moodInput)
                .font(WTTypography.body())
                .foregroundStyle(WTColor.inkPrimary)
                .frame(minHeight: 130)
                .scrollContentBackground(.hidden)
                .padding(WTSpacing.xs)
                .background(WTColor.bgCard)
                .clipShape(RoundedRectangle(cornerRadius: WTSpacing.cardRadius, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: WTSpacing.cardRadius, style: .continuous)
                        .stroke(WTColor.inkSecondary.opacity(0.15), lineWidth: 1)
                )
                .accessibilityIdentifier("mood_input")

            if coordinator.showSampleDataBanner {
                HStack(spacing: WTSpacing.xs) {
                    Image(systemName: "sparkles")
                    Text("Sample data mode")
                        .font(WTTypography.caption())
                }
                .foregroundStyle(WTColor.accentGold)
                .padding(.horizontal, WTSpacing.sm)
                .padding(.vertical, WTSpacing.xs)
                .background(WTColor.accentGold.opacity(0.13))
                .clipShape(Capsule())
                .accessibilityIdentifier("sample_banner")
            }
        }
        .padding(WTSpacing.md)
        .background(WTColor.bgCard)
        .clipShape(RoundedRectangle(cornerRadius: WTSpacing.cardRadius, style: .continuous))
    }

    private var filtersCard: some View {
        VStack(alignment: .leading, spacing: WTSpacing.md) {
            VStack(alignment: .leading, spacing: WTSpacing.xs) {
                Text("Format")
                    .font(WTTypography.bodyStrong())
                    .foregroundStyle(WTColor.inkPrimary)
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: WTSpacing.xs) {
                        ForEach(FormatFilter.allCases) { item in
                            FilterChip(
                                label: item.title,
                                isSelected: coordinator.selectedFormat == item
                            ) {
                                coordinator.selectedFormat = item
                            }
                        }
                    }
                    .padding(.vertical, WTSpacing.xxs)
                }
            }

            VStack(alignment: .leading, spacing: WTSpacing.xs) {
                Text("Length")
                    .font(WTTypography.bodyStrong())
                    .foregroundStyle(WTColor.inkPrimary)
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: WTSpacing.xs) {
                        ForEach(LengthFilter.allCases) { item in
                            FilterChip(
                                label: item.title,
                                isSelected: coordinator.selectedLength == item
                            ) {
                                coordinator.selectedLength = item
                            }
                        }
                    }
                    .padding(.vertical, WTSpacing.xxs)
                }
            }
        }
        .padding(WTSpacing.md)
        .background(WTColor.bgCard)
        .clipShape(RoundedRectangle(cornerRadius: WTSpacing.cardRadius, style: .continuous))
    }

    private var actionButtons: some View {
        VStack(spacing: WTSpacing.sm) {
            PrimaryButton(
                title: "Pick For Me",
                style: .filled,
                isLoading: coordinator.isLoading,
                pulse: true
            ) {
                Task {
                    await coordinator.submitMood()
                }
            }
            .accessibilityIdentifier("pick_button")

            PrimaryButton(
                title: "Roulette",
                style: .outline,
                isLoading: coordinator.isLoading
            ) {
                Task {
                    await coordinator.startRoulette()
                }
            }
            .accessibilityIdentifier("roulette_button")
        }
    }

    @ViewBuilder
    private var statusBlock: some View {
        if coordinator.isLoading {
            VStack(alignment: .leading, spacing: WTSpacing.sm) {
                Text(coordinator.loadingMessage)
                    .font(WTTypography.bodyStrong())
                    .foregroundStyle(WTColor.inkPrimary)
                RoundedRectangle(cornerRadius: 12)
                    .fill(WTColor.inkSecondary.opacity(0.12))
                    .frame(height: 12)
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
            .background(WTColor.bgCard)
            .clipShape(RoundedRectangle(cornerRadius: WTSpacing.cardRadius, style: .continuous))
        } else if let error = coordinator.errorMessage {
            ErrorCard(message: error) {
                Task {
                    await coordinator.submitMood()
                }
            }
        }
    }
}
