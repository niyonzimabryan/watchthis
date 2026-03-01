import Foundation

final class MockRecommendationService: RecommendationService {
    private let samples: [RecommendationResponse]

    init(bundle: Bundle = .main) {
        self.samples = Self.loadSamples(bundle: bundle)
    }

    init(samples: [RecommendationResponse]) {
        self.samples = samples
    }

    func recommend(input: RecommendInput) async throws -> RecommendationResponse {
        try await Task.sleep(for: .milliseconds(420))
        return buildResponse(
            moodText: input.moodInput,
            rerollOf: input.rerollOf,
            excludedTmdbIds: Set(input.excludedTmdbIds)
        )
    }

    func roulette(input: RouletteInput) async throws -> RecommendationResponse {
        try await Task.sleep(for: .milliseconds(360))
        return buildResponse(
            moodText: "roulette",
            rerollOf: input.rerollOf,
            excludedTmdbIds: Set(input.excludedTmdbIds)
        )
    }

    private func buildResponse(moodText: String, rerollOf: String?, excludedTmdbIds: Set<Int>) -> RecommendationResponse {
        guard !samples.isEmpty else {
            return Self.fallbackResponse()
        }

        var candidatePool = samples
        if !excludedTmdbIds.isEmpty {
            candidatePool = candidatePool.filter { !excludedTmdbIds.contains($0.recommendation.tmdbId) }
        }
        if candidatePool.isEmpty {
            candidatePool = samples
        }

        let index = Self.sampleIndex(for: moodText, count: candidatePool.count)
        var chosen = candidatePool[index]

        if let rerollOf, chosen.requestId == rerollOf {
            chosen = candidatePool[(index + 1) % candidatePool.count]
        }

        chosen.requestId = UUID().uuidString
        return chosen
    }

    private static func sampleIndex(for moodText: String, count: Int) -> Int {
        let scalarSum = moodText.unicodeScalars.map(\.value).reduce(0, +)
        return Int(scalarSum) % max(1, count)
    }

    private static func loadSamples(bundle: Bundle) -> [RecommendationResponse] {
        let files = ["mock_recommendation_1", "mock_recommendation_2", "mock_recommendation_3"]
        let decoder = APIClient.makeDecoder()

        return files.compactMap { name in
            guard let url = bundle.url(forResource: name, withExtension: "json"),
                  let data = try? Data(contentsOf: url),
                  let response = try? decoder.decode(RecommendationResponse.self, from: data)
            else {
                return nil
            }
            return response
        }
    }

    private static func fallbackResponse() -> RecommendationResponse {
        RecommendationResponse(
            requestId: UUID().uuidString,
            recommendation: Candidate(
                tmdbId: 13,
                mediaType: "movie",
                title: "Forrest Gump",
                year: 1994,
                posterUrl: nil,
                genres: ["Drama", "Comedy"],
                overview: "A warm, reliable watch for when you want one confident choice.",
                voteAverage: 8.5,
                voteCount: 26000,
                runtime: 142,
                keywords: ["comfort", "funny"],
                topCast: ["Tom Hanks"],
                imdbId: "tt0109830"
            ),
            pitch: "Sample mode is active. This title fits a comfort-first mood with a high confidence hit rate.",
            confidence: 0.84,
            reasoning: "Fallback response",
            streamingSources: [
                StreamingSource(
                    sourceId: nil,
                    name: "JustWatch",
                    type: "info",
                    webUrl: "https://www.justwatch.com/us/search?q=Forrest+Gump+1994",
                    format: nil
                )
            ]
        )
    }
}
