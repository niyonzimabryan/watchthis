import XCTest
@testable import WatchThisApp

@MainActor
final class HistoryStoreTests: XCTestCase {
    func testHistoryCapsAtMaximumSize() {
        let suite = UserDefaults(suiteName: "history-store-tests")!
        suite.removePersistentDomain(forName: "history-store-tests")

        let store = HistoryStore(defaults: suite, storageKey: "history", maxItems: 12)

        for idx in 0..<20 {
            store.add(Self.makeResponse(id: "req-\(idx)", tmdbId: idx + 100))
        }

        XCTAssertEqual(store.items.count, 12)
        XCTAssertEqual(store.items.first?.requestId, "req-19")
        XCTAssertEqual(store.items.last?.requestId, "req-8")
    }

    private static func makeResponse(id: String, tmdbId: Int) -> RecommendationResponse {
        RecommendationResponse(
            requestId: id,
            recommendation: Candidate(
                tmdbId: tmdbId,
                mediaType: "movie",
                title: "Title \(tmdbId)",
                year: 2020,
                posterUrl: nil,
                genres: ["Drama"],
                overview: "Overview",
                voteAverage: 8.0,
                voteCount: 1000,
                runtime: 100,
                keywords: [],
                topCast: [],
                imdbId: nil
            ),
            pitch: "Pitch",
            confidence: 0.8,
            reasoning: "Reasoning",
            streamingSources: []
        )
    }
}
