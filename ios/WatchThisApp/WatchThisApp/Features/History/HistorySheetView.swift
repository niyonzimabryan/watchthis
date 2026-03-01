import SwiftUI

struct HistorySheetView: View {
    @Bindable var coordinator: AppCoordinator
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            Group {
                if coordinator.historyItems.isEmpty {
                    ContentUnavailableView(
                        "No history yet",
                        systemImage: "clock.arrow.circlepath",
                        description: Text("Your recent picks will show up here.")
                    )
                } else {
                    List(coordinator.historyItems) { item in
                        Button {
                            coordinator.openHistory(item)
                            dismiss()
                        } label: {
                            VStack(alignment: .leading, spacing: WTSpacing.xxs) {
                                Text(item.recommendation.title)
                                    .font(WTTypography.bodyStrong())
                                    .foregroundStyle(WTColor.inkPrimary)
                                Text(item.recommendation.displayMeta)
                                    .font(WTTypography.caption())
                                    .foregroundStyle(WTColor.inkSecondary)
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(.vertical, WTSpacing.xxs)
                        }
                        .accessibilityIdentifier("history_item_\(item.recommendation.tmdbId)")
                    }
                    .listStyle(.plain)
                }
            }
            .navigationTitle("Recent Picks")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Close") {
                        dismiss()
                    }
                }
                if !coordinator.historyItems.isEmpty {
                    ToolbarItem(placement: .topBarTrailing) {
                        Button("Clear") {
                            coordinator.clearHistory()
                        }
                        .foregroundStyle(WTColor.warningRose)
                    }
                }
            }
        }
    }
}
