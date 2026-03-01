import XCTest

final class WatchThisAppUITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    @MainActor
    func testOnboardingToMoodInputFlow() throws {
        let app = XCUIApplication()
        app.launchArguments = ["--reset-onboarding", "--ui-testing"]
        app.launch()

        let cta = app.buttons["onboarding_cta"]
        if cta.waitForExistence(timeout: 4) {
            cta.tap()
        }

        XCTAssertTrue(app.textViews["mood_input"].waitForExistence(timeout: 6))
    }

    @MainActor
    func testMoodToResultFlowInMockMode() throws {
        let app = XCUIApplication()
        app.launchArguments = ["--reset-onboarding", "--ui-testing"]
        app.launch()

        let onboarding = app.buttons["onboarding_cta"]
        if onboarding.waitForExistence(timeout: 4) {
            onboarding.tap()
        }
        XCTAssertTrue(app.buttons["roulette_button"].waitForExistence(timeout: 6))
        app.buttons["roulette_button"].tap()

        let resultAppeared =
            app.buttons["spin_again_button"].waitForExistence(timeout: 12) ||
            app.otherElements["result_card"].waitForExistence(timeout: 2) ||
            app.scrollViews["result_screen"].waitForExistence(timeout: 2)
        XCTAssertTrue(resultAppeared)
    }
}
