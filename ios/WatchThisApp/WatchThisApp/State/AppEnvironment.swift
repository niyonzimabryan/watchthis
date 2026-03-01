import Foundation

enum AppMode: String, CaseIterable, Identifiable {
    case mock
    case live

    var id: String { rawValue }

    var title: String {
        rawValue.uppercased()
    }
}

struct AppEnvironment {
    let mode: AppMode
    let baseURL: URL

    static func fromBundle(_ bundle: Bundle = .main) -> AppEnvironment {
        let info = bundle.infoDictionary ?? [:]
        let modeRaw = (info["APP_MODE"] as? String)?.lowercased() ?? "mock"
        let mode = AppMode(rawValue: modeRaw) ?? .mock

        let defaultURL = URL(string: "http://127.0.0.1:8000")!
        let urlString = (info["API_BASE_URL"] as? String) ?? defaultURL.absoluteString
        let baseURL = URL(string: urlString) ?? defaultURL

        return AppEnvironment(mode: mode, baseURL: baseURL)
    }

    static func from(values: [String: String]) -> AppEnvironment {
        let mode = AppMode(rawValue: values["APP_MODE"]?.lowercased() ?? "mock") ?? .mock
        let defaultURL = URL(string: "http://127.0.0.1:8000")!
        let url = URL(string: values["API_BASE_URL"] ?? defaultURL.absoluteString) ?? defaultURL
        return AppEnvironment(mode: mode, baseURL: url)
    }
}
