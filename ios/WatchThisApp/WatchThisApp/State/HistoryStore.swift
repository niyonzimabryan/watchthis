import Foundation

@MainActor
final class HistoryStore {
    private let defaults: UserDefaults
    private let storageKey: String
    private let maxItems: Int

    private(set) var items: [RecommendationResponse]

    init(
        defaults: UserDefaults = .standard,
        storageKey: String = "watchthis.history",
        maxItems: Int = 12
    ) {
        self.defaults = defaults
        self.storageKey = storageKey
        self.maxItems = maxItems
        self.items = Self.load(defaults: defaults, key: storageKey)
    }

    func add(_ response: RecommendationResponse) {
        items.removeAll { $0.requestId == response.requestId }
        items.insert(response, at: 0)
        if items.count > maxItems {
            items = Array(items.prefix(maxItems))
        }
        persist()
    }

    func clear() {
        items = []
        defaults.removeObject(forKey: storageKey)
    }

    private func persist() {
        do {
            let data = try APIClient.makeEncoder().encode(items)
            defaults.set(data, forKey: storageKey)
        } catch {
            defaults.removeObject(forKey: storageKey)
        }
    }

    private static func load(defaults: UserDefaults, key: String) -> [RecommendationResponse] {
        guard let data = defaults.data(forKey: key) else {
            return []
        }

        do {
            return try APIClient.makeDecoder().decode([RecommendationResponse].self, from: data)
        } catch {
            return []
        }
    }
}
