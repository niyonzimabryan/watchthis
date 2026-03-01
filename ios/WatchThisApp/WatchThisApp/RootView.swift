import SwiftUI

struct RootView: View {
    @Bindable var coordinator: AppCoordinator

    var body: some View {
        Group {
            if !coordinator.hasSeenOnboarding {
                OnboardingView(coordinator: coordinator)
            } else {
                NavigationStack(path: $coordinator.path) {
                    MoodInputView(coordinator: coordinator)
                        .navigationDestination(for: AppRoute.self) { route in
                            switch route {
                            case .result:
                                ResultView(coordinator: coordinator)
                            }
                        }
                }
            }
        }
        .background(WTColor.bgPrimary.ignoresSafeArea())
        .sheet(isPresented: $coordinator.showHistorySheet) {
            HistorySheetView(coordinator: coordinator)
                .presentationDetents([.medium, .large])
                .presentationDragIndicator(.visible)
        }
    }
}
