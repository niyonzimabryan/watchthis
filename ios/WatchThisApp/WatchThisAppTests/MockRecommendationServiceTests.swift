import XCTest
@testable import WatchThisApp

@MainActor
final class MockRecommendationServiceTests: XCTestCase {
    func testRerollAvoidsExcludedTmdbId() async throws {
        let service = MockRecommendationService(samples: [
            Self.sample(id: "a", tmdbId: 13),
            Self.sample(id: "b", tmdbId: 680)
        ])

        let response = try await service.recommend(
            input: RecommendInput(
                moodInput: "anything",
                sessionId: "test",
                format: .any,
                length: .any,
                rerollOf: "a",
                excludedTmdbIds: [13]
            )
        )

        XCTAssertEqual(response.recommendation.tmdbId, 680)
    }

    private static func sample(id: String, tmdbId: Int) -> RecommendationResponse {
        RecommendationResponse(
            requestId: id,
            recommendation: Candidate(
                tmdbId: tmdbId,
                mediaType: "movie",
                title: "Sample",
                year: 2024,
                posterUrl: nil,
                genres: [],
                overview: "",
                voteAverage: 7,
                voteCount: 100,
                runtime: 100,
                keywords: [],
                topCast: [],
                imdbId: nil
            ),
            pitch: "pitch",
            confidence: 0.8,
            reasoning: "reason",
            streamingSources: []
        )
    }
}
