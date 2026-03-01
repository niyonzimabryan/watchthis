import Foundation

struct LiveRecommendationService: RecommendationService {
    private let client: APIClient

    init(baseURL: URL) {
        self.client = APIClient(baseURL: baseURL)
    }

    func recommend(input: RecommendInput) async throws -> RecommendationResponse {
        try await client.post(path: "recommend", payload: input)
    }

    func roulette(input: RouletteInput) async throws -> RecommendationResponse {
        try await client.post(path: "roulette", payload: input)
    }
}
