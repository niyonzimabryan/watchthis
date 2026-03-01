import XCTest
@testable import WatchThisApp

final class NetworkingCodecTests: XCTestCase {
    func testRecommendInputEncodesSnakeCaseKeys() throws {
        let input = RecommendInput(
            moodInput: "cozy and funny",
            sessionId: "session-1",
            format: .movie,
            length: .standard,
            rerollOf: "req-1",
            excludedTmdbIds: [13, 680]
        )

        let data = try APIClient.makeEncoder().encode(input)
        let payload = try XCTUnwrap(try JSONSerialization.jsonObject(with: data) as? [String: Any])

        XCTAssertEqual(payload["mood_input"] as? String, "cozy and funny")
        XCTAssertEqual(payload["session_id"] as? String, "session-1")
        XCTAssertEqual(payload["reroll_of"] as? String, "req-1")
        XCTAssertEqual(payload["excluded_tmdb_ids"] as? [Int], [13, 680])
    }

    func testRecommendationResponseDecodesPosterURL() throws {
        let json = """
        {
          "request_id": "req-1",
          "recommendation": {
            "tmdb_id": 13,
            "media_type": "movie",
            "title": "Forrest Gump",
            "year": 1994,
            "poster_url": "https://image.tmdb.org/t/p/w780/demo.jpg",
            "genres": ["Drama"],
            "overview": "Overview",
            "vote_average": 8.5,
            "vote_count": 25000,
            "runtime": 142,
            "keywords": ["comfort"],
            "top_cast": ["Tom Hanks"],
            "imdb_id": "tt0109830"
          },
          "pitch": "Pitch",
          "confidence": 0.91,
          "reasoning": "Reasoning",
          "streaming_sources": []
        }
        """.data(using: .utf8)!

        let decoded = try APIClient.makeDecoder().decode(RecommendationResponse.self, from: json)
        XCTAssertEqual(decoded.recommendation.tmdbId, 13)
        XCTAssertEqual(decoded.recommendation.posterUrl, "https://image.tmdb.org/t/p/w780/demo.jpg")
    }
}
