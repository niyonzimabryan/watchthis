# WatchThis iPhone Frontend Summary

Date: 2026-03-01

## What was built

- Native SwiftUI iOS app scaffold at `ios/WatchThisApp` targeting iOS 17+.
- Four-screen MVP flow:
  - Onboarding (one-time with `hasSeenOnboarding` persistence)
  - Mood Input (mood text, format chips, length chips, pick + roulette CTAs)
  - Result (poster, metadata, pitch, confidence, streaming pills, reroll/new mood)
  - History sheet (session-local, max 12, reopen and clear actions)
- Mock-first data architecture with live API option and debug-time mode switch.
- Request/session logic:
  - Stable `session_id` persisted locally
  - Reroll uses `reroll_of` and `excluded_tmdb_ids`
  - Exclusion reset when context changes

## Design system implemented

- Locked color tokens, rounded typography, spacing scale, and corner radii.
- Reusable components: primary button, chip, confidence badge, streaming pill, poster view, error card.
- Motion behaviors:
  - Result card spring entrance
  - CTA pulse animation
  - Skeleton shimmer loader
- Accessibility pass:
  - Dynamic Type friendly typography usage
  - Control identifiers/labels for UI testing
  - Minimum tap targets via component sizing
  - Reduced-motion checks for animations

## Networking and environments

- `RecommendationService` protocol with:
  - `LiveRecommendationService` (FastAPI endpoints)
  - `MockRecommendationService` (local fixtures)
- `AppEnvironment` reads:
  - `APP_MODE`
  - `API_BASE_URL`
- Build configs:
  - `Debug.xcconfig`: mock mode + local URL
  - `Release.xcconfig`: live mode + production URL placeholder

## Backend compatibility updates

- Added `poster_url` to API `Candidate` model and retrieval pipeline.
- Mock catalog/test data now carries poster paths and produces full TMDB image URLs.

## Tests and verification

- Python tests: `32 passed` (`.venv/bin/pytest -q`).
- iOS unit tests: `7 passed` using:
  - `xcodebuild -project ios/WatchThisApp/WatchThisApp.xcodeproj -scheme WatchThisApp -destination 'platform=iOS Simulator,name=iPhone 17' -only-testing:WatchThisAppTests -skip-testing:WatchThisAppUITests -derivedDataPath /tmp/WatchThisDD test`
- iOS UI tests: `2 passed` using:
  - `xcodebuild -project ios/WatchThisApp/WatchThisApp.xcodeproj -scheme WatchThisApp -destination 'platform=iOS Simulator,name=iPhone 17' -only-testing:WatchThisAppUITests -derivedDataPath /tmp/WatchThisDD test`

## Known follow-ups

- Set final production backend URL in `ios/WatchThisApp/Config/Release.xcconfig`.
- Expand UI tests for history restore + reroll exclusion behavior.
