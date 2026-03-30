# Project Ledger — todoscratchpad.md

> Living document tracking tasks, improvements, and ideas for WatchThis.
> Updated by Claude Code after each set of changes.

---

## Current Tasks

- [ ] **Get 200+ voted recs** — Manual testing with friends via live Railway URL to build training dataset
- [ ] **Connect iOS app to Railway** — Update `Release` config `API_BASE_URL` to `https://watchthis.up.railway.app`
- [ ] **Add production app icon and launch artwork** — For iOS App Store submission
- [ ] **One-command setup for new cloners** — Create a `setup.sh` (or Makefile) that: creates a venv, installs Python deps (`pip install -r requirements.txt`), installs frontend deps (`cd web && npm install`), copies `.env.example` → `.env` with prompts for API keys, seeds the Reddit DB, and runs initial DB migrations. Goal: `git clone && ./setup.sh && ./run.sh` and you're live. Also consider adding a `docker-compose.yml` for truly zero-config setup (Dockerfile already exists).
- [ ] **"Watch Now" deep-link on TV cast page** — Add buttons on the Chromecast cast view that link directly to streaming service pages for the recommended title (e.g., Netflix title page). Assume the user has the sub; fall back to the show's page on that service.

## Completed

- [x] **Web UI built** — React + Vite + Tailwind frontend mirroring iOS app (Onboarding, Mood Input, Result, History) (2026-03-24)
- [x] **Feedback voting system** — Upvote/downvote UI with optional reasoning text box, `feedback_votes` DB table with denormalized training signals, `/vote` and `/vote-stats` API endpoints (2026-03-24)
- [x] **Railway deployment** — Single-container deploy (FastAPI serves built Vite frontend), SQLite on persistent volume at `/data/watchthis.db`, all API keys as env vars (2026-03-24)
  - **URL:** `https://watchthis.up.railway.app`
  - **Railway project:** `8fa8d200-9014-40e6-94b7-5090a00a6abe`
  - **Service ID:** `c952980a-74e6-4d69-b8cc-19ecf33898db`
  - **Deploy:** `railway up --detach` from project root
  - **Logs:** `railway logs` from project root
  - **Volume:** mounted at `/data` for SQLite persistence
- [x] **Model names updated** — `claude-3-5-haiku-latest` → `claude-haiku-4-5-20251001`, `claude-3-5-sonnet-latest` → `claude-sonnet-4-6`, `claude-opus-4-1` → `claude-opus-4-6` — fixed in both `config.py` and `.env` (2026-03-24)
- [x] **DB migrations auto-run on startup** — `api/server.py` calls `init_db()` on FastAPI startup event (2026-03-24)
- [x] 2026-03-01: Audited current project status (backend shape, tests, runtime smoke, iOS-client gap)
- [x] 2026-03-01: Added backend `poster_url` support from candidate retrieval through API model response
- [x] 2026-03-01: Added iOS SwiftUI MVP app scaffold (`Onboarding`, `Mood Input`, `Result`, `History`)
- [x] 2026-03-01: Implemented mock/live service switching, session persistence, reroll exclusions, and capped local history
- [x] 2026-03-01: Added iOS unit tests and UI tests; stabilized roulette-to-result UI assertion

## Grill-Me Findings (2026-03-29)

### Architecture Decisions Resolved
- **Cast interrupts TV** — by design, no confirmation prompt. "Show Me" = takes over TV immediately.
- **DashCast dependency risk** — Google could deprecate the receiver. Fallback: `catt cast_site` (different receiver) or generate image + default media receiver.
- **In-memory cast store** — OK for personal use. If server restarts, cast view URL 404s. Could move to SQLite if it matters.
- **Deep-links belong on phone, not TV** — DashCast pages aren't interactive (no remote cursor). "Open on Netflix" should be a button on the phone after casting, not on the TV screen.

### Open Design Questions
- **Group mode still planned?** — `tv-cast-prd.md` describes full WebSocket room system. Solo cast is the MVP. Group mode would be a separate build phase if still wanted.
- **TV-off UX** — Cast failure takes ~10-15s. Should add frontend timeout at 8s with "TV might be off" message instead of just spinning.
- **Device rename fragility** — If Chromecast is renamed after saving, cast fails silently. Could add a "forget device" button or auto-re-scan on failure.

### Cast Feature Gaps (Non-Blocking)
- No tests for cast feature (zero coverage)
- No "stop casting" button in UI (endpoint exists, not wired)
- No cast-from-history shortcut (must go through full flow)
- Local IP detection fallback to "localhost" won't reach Chromecast
- Poster image silent failure (no placeholder on broken URL)

### Model Swap Decision (2026-03-29)
- **Ranking + pitch**: Sonnet → **Opus** (better creative writing, personalized pitches)
- **Mood interpretation**: Haiku → **Gemini Flash** (cheaper structured extraction)
- **Signal enrichment**: OMDb + Watchmode + Reddit scraper → **Gemini Pro with search grounding** (real-time ratings, streaming, community signal in one call)
- This eliminates Watchmode's 1,000 lifetime cap, OMDb's 1,000/day cap, and the Reddit scraper cron entirely

## Future Improvements

### Phase 2: Eval Suite
- [ ] Build eval suite from accumulated good/bad vote pairs
- [ ] Use Opus as judge: "Given this mood, would a human with taste pick this?"
- [ ] Tune ranking prompts and candidate filtering against eval results
- [ ] Measure upvote rate over time as quality metric

### Phase 3: Scheduled Improvement Agent
- [ ] Weekly scheduled agent reviews worst-rated recommendations, diagnoses why
- [ ] Agent rewrites ranking prompts based on failure patterns
- [ ] Build "never recommend" list from consistent downvotes
- [ ] Eventually: agent implements prompt/filter tweaks automatically

### Phase 4: Taste Profiles & Monetization
- [ ] Cluster users by voting patterns (collaborative filtering)
- [ ] Weight recommendations by similar-taste users
- [ ] Free tier (3 picks/day) → $3/month for unlimited + taste memory
- [ ] Taste profile = lock-in (users won't retrain elsewhere)
- [ ] Consider: ads create perverse incentives in a recommendation product

## Claude Suggestions & Opportunities

- [ ] **Add user ID / device fingerprint** — Right now `session_id` is random per browser. For taste profiles, need a persistent user identity (anonymous hash or optional sign-up)
- [ ] **Rate limiting on Railway** — Free API with Claude calls underneath could get expensive if someone hammers it. Add basic rate limiting before sharing URL widely
- [ ] **Vote reason analysis** — Once enough reasons accumulate, cluster them to find patterns (e.g. "too obvious", "already seen it", "not actually on that platform")
- [ ] **Streaming source accuracy** — Watchmode data can be stale. Consider showing "last checked" or letting users flag wrong streaming info
- [ ] **iOS app could share Railway URL** — Point iOS app at `watchthis.up.railway.app` for a quick live test without App Store submission

## Tech Debt & Bugs

- [ ] **FastAPI `on_event("startup")` is deprecated** — Should migrate to lifespan context manager pattern
- [ ] **No error handling on vote endpoint for missing request_log** — If DB is fresh (no request_log rows), votes will 404. Edge case but could confuse testers
- [ ] **SQLite concurrent writes on Railway** — Single-container is fine now but if you ever scale to multiple replicas, SQLite won't handle concurrent writes. Cross that bridge when needed (Postgres migration)
- [ ] **No HTTPS redirect** — Railway handles this but worth confirming all traffic goes through HTTPS
- [ ] **`.env` in project root has API keys** — Already in `.gitignore` but double-check before any public repo push

---
*Last updated: 2026-03-29*
