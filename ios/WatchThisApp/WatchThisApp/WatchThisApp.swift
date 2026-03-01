import SwiftUI

@main
struct WatchThisApp: App {
    init() {
        let args = ProcessInfo.processInfo.arguments
        if args.contains("--reset-onboarding") {
            UserDefaults.standard.removeObject(forKey: "watchthis.has_seen_onboarding")
            UserDefaults.standard.removeObject(forKey: "watchthis.history")
        }
    }

    @State private var coordinator = AppCoordinator.makeDefault()

    var body: some Scene {
        WindowGroup {
            RootView(coordinator: coordinator)
        }
    }
}
