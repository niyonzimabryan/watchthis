import Foundation

enum FormatFilter: String, Codable, CaseIterable, Identifiable {
    case movie
    case tv
    case episode
    case any

    var id: Self { self }

    var title: String {
        switch self {
        case .movie: return "Movie"
        case .tv: return "TV"
        case .episode: return "Episode"
        case .any: return "Any"
        }
    }
}

enum LengthFilter: String, Codable, CaseIterable, Identifiable {
    case quick
    case standard
    case long
    case epic
    case any

    var id: Self { self }

    var title: String {
        switch self {
        case .quick: return "Quick"
        case .standard: return "Standard"
        case .long: return "Long"
        case .epic: return "Epic"
        case .any: return "Any"
        }
    }
}

struct RecommendInput: Codable, Sendable {
    var moodInput: String
    var sessionId: String?
    var format: FormatFilter
    var length: LengthFilter
    var rerollOf: String?
    var excludedTmdbIds: [Int]

    init(
        moodInput: String,
        sessionId: String?,
        format: FormatFilter,
        length: LengthFilter,
        rerollOf: String? = nil,
        excludedTmdbIds: [Int] = []
    ) {
        self.moodInput = moodInput
        self.sessionId = sessionId
        self.format = format
        self.length = length
        self.rerollOf = rerollOf
        self.excludedTmdbIds = excludedTmdbIds
    }
}

struct RouletteInput: Codable, Sendable {
    var sessionId: String?
    var format: FormatFilter
    var length: LengthFilter
    var rerollOf: String?
    var excludedTmdbIds: [Int]

    init(
        sessionId: String?,
        format: FormatFilter,
        length: LengthFilter,
        rerollOf: String? = nil,
        excludedTmdbIds: [Int] = []
    ) {
        self.sessionId = sessionId
        self.format = format
        self.length = length
        self.rerollOf = rerollOf
        self.excludedTmdbIds = excludedTmdbIds
    }
}

struct StreamingSource: Codable, Hashable, Identifiable, Sendable {
    var sourceId: String?
    var name: String
    var type: String
    var webUrl: String?
    var format: String?

    var id: String {
        if let sourceId {
            return sourceId
        }
        return "\(name)-\(type)-\(webUrl ?? "")"
    }
}

struct Candidate: Codable, Hashable, Identifiable, Sendable {
    var tmdbId: Int
    var mediaType: String
    var title: String
    var year: Int?
    var posterUrl: String?
    var genres: [String]
    var overview: String
    var voteAverage: Double
    var voteCount: Int
    var runtime: Int?
    var keywords: [String]
    var topCast: [String]
    var imdbId: String?

    var id: Int { tmdbId }

    var displayMeta: String {
        let media = mediaType.uppercased()
        let yearText = year.map(String.init) ?? "-"
        if let runtime {
            return "\(media) • \(yearText) • \(runtime)m"
        }
        return "\(media) • \(yearText)"
    }

    var posterURL: URL? {
        guard let posterUrl else { return nil }
        return URL(string: posterUrl)
    }
}

struct RecommendationResponse: Codable, Hashable, Identifiable, Sendable {
    var requestId: String
    var recommendation: Candidate
    var pitch: String
    var confidence: Double
    var reasoning: String
    var streamingSources: [StreamingSource]

    var id: String { requestId }
}

struct APIErrorResponse: Codable {
    var detail: String?
}
