import Foundation
import Observation

@MainActor
enum AppRoute: Hashable {
    case result
}

@MainActor
@Observable
final class AppCoordinator {
    private enum Constants {
        static let onboardingKey = "watchthis.has_seen_onboarding"
        static let loadingMessages = [
            "Reading your vibe...",
            "Scanning high-confidence picks...",
            "Locking in one recommendation..."
        ]
    }

    private let defaults: UserDefaults
    private let sessionStore: SessionStore
    private let historyStore: HistoryStore
    private let liveService: RecommendationService
    private let mockService: RecommendationService

    private var currentContextKey: String?
    private var activeNetworkTask: Task<RecommendationResponse, Error>?
    private var loadingRotationTask: Task<Void, Never>?
    private var slowRequestTask: Task<Void, Never>?

    private(set) var environment: AppEnvironment

    var path: [AppRoute] = []
    var hasSeenOnboarding: Bool
    var moodInput = ""
    var selectedFormat: FormatFilter = .any
    var selectedLength: LengthFilter = .any
    var currentResponse: RecommendationResponse?
    var historyItems: [RecommendationResponse]
    var isLoading = false
    var loadingMessage = Constants.loadingMessages[0]
    var showSlowRequestAction = false
    var errorMessage: String?
    var showHistorySheet = false
    var showSampleDataBanner = false
    var excludedTmdbIds: [Int] = []
    var lastRequestWasRoulette = false

#if DEBUG
    var debugModeOverride: AppMode?
#endif

    init(
        environment: AppEnvironment,
        sessionStore: SessionStore,
        historyStore: HistoryStore,
        liveService: RecommendationService,
        mockService: RecommendationService,
        defaults: UserDefaults = .standard
    ) {
        self.environment = environment
        self.sessionStore = sessionStore
        self.historyStore = historyStore
        self.liveService = liveService
        self.mockService = mockService
        self.defaults = defaults
        self.historyItems = historyStore.items
        self.hasSeenOnboarding = defaults.bool(forKey: Constants.onboardingKey)
    }

    static func makeDefault() -> AppCoordinator {
        let environment = AppEnvironment.fromBundle()
        let sessionStore = SessionStore()
        let historyStore = HistoryStore()
        let liveService = LiveRecommendationService(baseURL: environment.baseURL)
        let mockService = MockRecommendationService()

        return AppCoordinator(
            environment: environment,
            sessionStore: sessionStore,
            historyStore: historyStore,
            liveService: liveService,
            mockService: mockService
        )
    }

    var effectiveMode: AppMode {
#if DEBUG
        return debugModeOverride ?? environment.mode
#else
        return environment.mode
#endif
    }

    func completeOnboarding() {
        hasSeenOnboarding = true
        defaults.set(true, forKey: Constants.onboardingKey)
    }

    func submitMood() async {
        let trimmed = moodInput.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            errorMessage = "Tell us your mood first so we can pick one great title."
            return
        }

        lastRequestWasRoulette = false
        resetContextIfNeeded(newKey: makeContextKey(isRoulette: false, moodText: trimmed))

        let input = RecommendInput(
            moodInput: trimmed,
            sessionId: sessionStore.sessionId,
            format: selectedFormat,
            length: selectedLength,
            excludedTmdbIds: excludedTmdbIds
        )
        await performRequest {
            try await self.executeRecommend(input)
        }
    }

    func startRoulette() async {
        lastRequestWasRoulette = true
        resetContextIfNeeded(newKey: makeContextKey(isRoulette: true, moodText: nil))

        let input = RouletteInput(
            sessionId: sessionStore.sessionId,
            format: selectedFormat,
            length: selectedLength,
            excludedTmdbIds: excludedTmdbIds
        )
        await performRequest {
            try await self.executeRoulette(input)
        }
    }

    func spinAgain() async {
        guard let currentResponse else {
            return
        }

        if !excludedTmdbIds.contains(currentResponse.recommendation.tmdbId) {
            excludedTmdbIds.append(currentResponse.recommendation.tmdbId)
        }

        if lastRequestWasRoulette {
            let input = RouletteInput(
                sessionId: sessionStore.sessionId,
                format: selectedFormat,
                length: selectedLength,
                rerollOf: currentResponse.requestId,
                excludedTmdbIds: excludedTmdbIds
            )
            await performRequest {
                try await self.executeRoulette(input)
            }
        } else {
            let trimmed = moodInput.trimmingCharacters(in: .whitespacesAndNewlines)
            let input = RecommendInput(
                moodInput: trimmed,
                sessionId: sessionStore.sessionId,
                format: selectedFormat,
                length: selectedLength,
                rerollOf: currentResponse.requestId,
                excludedTmdbIds: excludedTmdbIds
            )
            await performRequest {
                try await self.executeRecommend(input)
            }
        }
    }

    func cancelActiveRequest() {
        activeNetworkTask?.cancel()
        stopLoadingUX()
        errorMessage = "Request canceled."
    }

    func newMood() {
        path.removeAll()
        errorMessage = nil
    }

    func openHistory(_ response: RecommendationResponse) {
        currentResponse = response
        if !path.contains(.result) {
            path.append(.result)
        }
        errorMessage = nil
        showHistorySheet = false
    }

    func clearHistory() {
        historyStore.clear()
        historyItems = historyStore.items
    }

#if DEBUG
    func setDebugModeOverride(_ mode: AppMode?) {
        debugModeOverride = mode
    }
#endif

    private func executeRecommend(_ input: RecommendInput) async throws -> RecommendationResponse {
        switch effectiveMode {
        case .mock:
            return try await mockService.recommend(input: input)
        case .live:
            do {
                return try await liveService.recommend(input: input)
            } catch {
                let fallback = try await mockService.recommend(input: input)
                showSampleDataBanner = true
                return fallback
            }
        }
    }

    private func executeRoulette(_ input: RouletteInput) async throws -> RecommendationResponse {
        switch effectiveMode {
        case .mock:
            return try await mockService.roulette(input: input)
        case .live:
            do {
                return try await liveService.roulette(input: input)
            } catch {
                let fallback = try await mockService.roulette(input: input)
                showSampleDataBanner = true
                return fallback
            }
        }
    }

    private func performRequest(_ operation: @escaping @MainActor () async throws -> RecommendationResponse) async {
        startLoadingUX()
        errorMessage = nil
        showSampleDataBanner = (effectiveMode == .mock)

        let task = Task {
            try await operation()
        }
        activeNetworkTask = task

        do {
            let response = try await task.value
            handleSuccess(response)
        } catch is CancellationError {
            // Explicit cancellation, no-op because cancel path updates state.
        } catch {
            errorMessage = (error as? LocalizedError)?.errorDescription ?? "Unable to fetch recommendation right now."
        }

        stopLoadingUX()
    }

    private func handleSuccess(_ response: RecommendationResponse) {
        currentResponse = response

        if !excludedTmdbIds.contains(response.recommendation.tmdbId) {
            excludedTmdbIds.append(response.recommendation.tmdbId)
        }

        historyStore.add(response)
        historyItems = historyStore.items
        errorMessage = nil
        if !path.contains(.result) {
            path.append(.result)
        }
    }

    private func makeContextKey(isRoulette: Bool, moodText: String?) -> String {
        if isRoulette {
            return "roulette|\(selectedFormat.rawValue)|\(selectedLength.rawValue)"
        }
        let mood = moodText ?? ""
        return "mood|\(mood.lowercased())|\(selectedFormat.rawValue)|\(selectedLength.rawValue)"
    }

    private func resetContextIfNeeded(newKey: String) {
        if currentContextKey != newKey {
            excludedTmdbIds = []
            currentContextKey = newKey
        }
    }

    private func startLoadingUX() {
        isLoading = true
        showSlowRequestAction = false
        loadingMessage = Constants.loadingMessages[0]

        loadingRotationTask?.cancel()
        slowRequestTask?.cancel()

        loadingRotationTask = Task { [weak self] in
            guard let self else { return }
            var idx = 0
            while !Task.isCancelled {
                try? await Task.sleep(for: .milliseconds(1200))
                idx = (idx + 1) % Constants.loadingMessages.count
                self.loadingMessage = Constants.loadingMessages[idx]
            }
        }

        slowRequestTask = Task { [weak self] in
            guard let self else { return }
            try? await Task.sleep(for: .seconds(8))
            guard !Task.isCancelled else { return }
            self.showSlowRequestAction = true
        }
    }

    private func stopLoadingUX() {
        isLoading = false
        showSlowRequestAction = false
        loadingRotationTask?.cancel()
        slowRequestTask?.cancel()
        activeNetworkTask = nil
    }
}
