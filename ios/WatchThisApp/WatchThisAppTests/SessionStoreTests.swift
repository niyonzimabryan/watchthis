import XCTest
@testable import WatchThisApp

final class SessionStoreTests: XCTestCase {
    func testSessionIdIsStablePerStore() {
        let suite = UserDefaults(suiteName: "session-store-tests")!
        suite.removePersistentDomain(forName: "session-store-tests")

        let store = SessionStore(defaults: suite, key: "session")
        let first = store.sessionId
        let second = store.sessionId

        XCTAssertFalse(first.isEmpty)
        XCTAssertEqual(first, second)
    }
}
