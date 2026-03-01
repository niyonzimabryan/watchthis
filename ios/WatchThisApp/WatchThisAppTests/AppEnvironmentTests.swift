import XCTest
@testable import WatchThisApp

final class AppEnvironmentTests: XCTestCase {
    func testEnvironmentParsesModeAndURL() {
        let env = AppEnvironment.from(
            values: [
                "APP_MODE": "live",
                "API_BASE_URL": "https://example.test"
            ]
        )

        XCTAssertEqual(env.mode, .live)
        XCTAssertEqual(env.baseURL.absoluteString, "https://example.test")
    }

    func testEnvironmentFallsBackToMockWhenModeIsInvalid() {
        let env = AppEnvironment.from(values: ["APP_MODE": "unknown"])
        XCTAssertEqual(env.mode, .mock)
    }
}
