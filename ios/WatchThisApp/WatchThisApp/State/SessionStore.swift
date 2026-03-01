import Foundation

final class SessionStore {
    private let defaults: UserDefaults
    private let key: String

    init(defaults: UserDefaults = .standard, key: String = "watchthis.session_id") {
        self.defaults = defaults
        self.key = key
    }

    var sessionId: String {
        if let value = defaults.string(forKey: key), !value.isEmpty {
            return value
        }
        let value = UUID().uuidString
        defaults.set(value, forKey: key)
        return value
    }
}
