import Foundation

@MainActor
protocol RecommendationService {
    func recommend(input: RecommendInput) async throws -> RecommendationResponse
    func roulette(input: RouletteInput) async throws -> RecommendationResponse
}
