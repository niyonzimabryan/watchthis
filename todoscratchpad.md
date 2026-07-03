# Project Ledger — todoscratchpad.md

> Living document tracking tasks, improvements, and ideas for WatchThis.
> Updated by Claude Code after each set of changes.

---

## Open Prioritized List

<!-- Peer-synced with Hermes kanban + Linear. Reconciled 2026-07-03. Merged on origin/main: PR #1/#2/#4/#5 (lifespan)/#6 (model-lint). -->

- [ ] **P1 — Connect iOS app to Railway** (`BRY-109`, `t_df7af342`, **in_review**) — open **PR #3** `bry-109-ios-railway-url` remains unmerged as of 2026-07-03 (head `59e336c0c3203609398a0b404c6cd3dffa93f6a5`); Release config points at `https://watchthis.up.railway.app`. The earlier "feedback capture" blocker is stale — `POST /vote` + `GET /vote-stats` shipped in [PR #2](https://github.com/niyonzimabryan/watchthis/pull/2) (merged 2026-05-12; contract matches web UI, 8 endpoint tests, full suite 63 passed against origin/main). What actually remains: merge PR #3 + Bryan's manual Xcode Release build verification of mood/roulette/reroll/history flows.
- [ ] **P2 — Get 200+ voted recs** (`BRY-112`, `t_35f6c746`, blocked) — the linchpin dataset gating Phase 2–4
- [ ] **P3 — Build eval suite from good/bad vote pairs** (`BRY-114`, `t_28bb2732`, blocked) — gated on the 200-vote dataset
- [ ] **P3 — Add user ID / device fingerprint** (`BRY-127`, `t_c26f52bf`, blocked) — persistent identity for taste profiles
- [ ] **P4 — Streaming source accuracy** (`BRY-129`, `t_ef315162`, blocked) — surface "last checked" / flag stale Watchmode data

---

## Current Tasks

### PM-groomed release sequence (2026-05-07)

1. ~~**Fix feedback capture before any tester push**~~ — **DONE (PR #2, merged 2026-05-12; verified 2026-07-01):** `POST /vote` + `GET /vote-stats` live in `api/routes.py`, SQLite `votes` table with UPSERT per `(request_id, session_id)`, contract matches the web UI, 8 endpoint tests.
2. **Add basic abuse/cost protection before sharing the public URL** — Free WatchThis still pays for LLM calls. Outcome: Railway deployment has a simple per-session/IP cap with a friendly error state, not surprise Anthropic spend.
3. **Run the 200+ voted-rec tester loop** — Only after vote persistence and rate limiting work. Outcome: 200 usable voted recommendations with enough metadata to diagnose recommendation quality.
4. **Point iOS Release config at Railway for live testing** — Small unlock for native testing, not App Store launch. Outcome: a Release build uses `https://watchthis.up.railway.app` and can complete mood/roulette flows.

### Explicitly deferred / killed

- **Kill as scoped: "Watch Now" deep-link on TV cast page.** Prior decision says DashCast pages are not interactive; put deep-links on the phone result screen if we revive this.
- **Defer App Store icon/launch artwork.** No App Store submission is in the active release sequence.
- **Defer one-command setup.** Useful only if WatchThis becomes an open-source project; current goal is free/wabi release, not contributor onboarding.
- **Defer eval automation, taste profiles, collaborative filtering, monetization, scheduled agents.** These require vote data first; no work before the 200-vote loop produces signal.
- **Archive idea-only notes with no action:** ads concern, taste-profile lock-in, SQLite multi-replica concern, HTTPS redirect check unless ops finds a real redirect failure.

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

## Future Ideas

> Forward-looking features / directions, organized by phase. Phase 2/3/4 are all gated on the 200-vote dataset (see "Get 200+ voted recs" — the linchpin); the 2026-05-12 Hermes-kanban audit parked the matching tasks to priority-1. Also parked there: the items under "Explicitly deferred / killed" above (Watch-Now deep-link → revivable on the phone result screen; App Store icon/artwork; one-command setup if it ever goes OSS). Strategy musings (ads = perverse incentives; taste profile = lock-in) live here too as notes, not tasks. The active near-term backlog lives in the kanban / Linear.

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

- [x] **FastAPI `on_event("startup")` is deprecated** — Migrated API startup to FastAPI lifespan context manager pattern (2026-05-22)
- [ ] **No error handling on vote endpoint for missing request_log** — If DB is fresh (no request_log rows), votes will 404. Edge case but could confuse testers
- [ ] **SQLite concurrent writes on Railway** — Single-container is fine now but if you ever scale to multiple replicas, SQLite won't handle concurrent writes. Cross that bridge when needed (Postgres migration)
- [ ] **No HTTPS redirect** — Railway handles this but worth confirming all traffic goes through HTTPS
- [ ] **`.env` in project root has API keys** — Already in `.gitignore` but double-check before any public repo push

---
*Last updated: 2026-07-03*
