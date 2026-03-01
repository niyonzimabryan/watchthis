import SwiftUI

struct OnboardingView: View {
    @Bindable var coordinator: AppCoordinator

    var body: some View {
        ZStack {
            LinearGradient(
                colors: [WTColor.bgPrimary, WTColor.accentTeal.opacity(0.15), WTColor.accentCoral.opacity(0.12)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()

            VStack(alignment: .leading, spacing: WTSpacing.lg) {
                Spacer()

                VStack(alignment: .leading, spacing: WTSpacing.md) {
                    Text("WatchThis")
                        .font(WTTypography.hero())
                        .foregroundStyle(WTColor.inkPrimary)

                    Text("Your social movie friend that picks one great thing to watch right now.")
                        .font(WTTypography.subtitle())
                        .foregroundStyle(WTColor.inkSecondary)

                    Text("No scrolling spiral. No 20-tab comparison. One confident pick, fast.")
                        .font(WTTypography.body())
                        .foregroundStyle(WTColor.inkSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }

                PrimaryButton(title: "Let's pick something", pulse: true) {
                    coordinator.completeOnboarding()
                }
                .accessibilityIdentifier("onboarding_cta")

                Spacer()
            }
            .padding(WTSpacing.xl)
        }
    }
}
