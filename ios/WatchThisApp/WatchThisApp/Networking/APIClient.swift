import Foundation

enum APIClientError: LocalizedError {
    case invalidResponse
    case httpError(Int, String)
    case decodeError

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "Invalid response from server."
        case .httpError(let code, let detail):
            if detail.isEmpty {
                return "Request failed with status \(code)."
            }
            return detail
        case .decodeError:
            return "Could not decode server response."
        }
    }
}

struct APIClient {
    let baseURL: URL
    let urlSession: URLSession

    init(baseURL: URL, urlSession: URLSession = .shared) {
        self.baseURL = baseURL
        self.urlSession = urlSession
    }

    static func makeEncoder() -> JSONEncoder {
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        return encoder
    }

    static func makeDecoder() -> JSONDecoder {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return decoder
    }

    func post<Payload: Encodable, Output: Decodable>(path: String, payload: Payload) async throws -> Output {
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.httpMethod = "POST"
        request.timeoutInterval = 20
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try APIClient.makeEncoder().encode(payload)

        let (data, response) = try await urlSession.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIClientError.invalidResponse
        }

        if !(200...299).contains(httpResponse.statusCode) {
            let detail = (try? APIClient.makeDecoder().decode(APIErrorResponse.self, from: data).detail) ?? ""
            throw APIClientError.httpError(httpResponse.statusCode, detail)
        }

        do {
            return try APIClient.makeDecoder().decode(Output.self, from: data)
        } catch {
            throw APIClientError.decodeError
        }
    }
}
