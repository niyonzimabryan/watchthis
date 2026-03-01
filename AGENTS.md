# AGENTS.md

This file is the working agreement for building WatchThis.  
It is intentionally lightweight and should be updated as we learn.

## How We Use This

- Treat this as a living document, not fixed rules.
- When we repeat a decision twice, add it here.
- Prefer practical defaults over perfect architecture.
- Keep product behavior aligned with `watchthis-prd.md`.

## Product Priorities (V1)

- Decisive UX: return one recommendation, not a list.
- Fast response times: optimize for perceived speed.
- High-confidence picks over broad coverage.
- Graceful degradation when external APIs fail or rate-limit.

## Engineering Defaults

- Language/runtime: Python 3.11+.
- API: FastAPI.
- Data modeling: Pydantic for request/response and core domain models.
- Storage: SQLite for local dev, schema designed for PostgreSQL migration.
- HTTP: `httpx` with explicit timeouts and retries where safe.
- Config: environment-driven (`.env` + `.env.example`), no hardcoded secrets.

## Code Style (Starter)

- Keep modules small and single-purpose.
- Prefer explicit names over clever abstractions.
- Add type hints for public functions and core pipeline code.
- Use docstrings for non-obvious behavior and integration boundaries.
- Raise actionable errors with context (provider, operation, key IDs).
- Avoid premature framework complexity; extract abstractions only when duplication is real.

## Reliability Rules

- Every external call must have:
  - timeout
  - error handling
  - structured log context
- Caching must include clear TTL ownership in code comments/constants.
- Never fail the full recommendation just because one enrichment source is down.
- Reroll should avoid immediate duplicates when feasible.

## Testing Rules

- Add/maintain unit tests for each core stage:
  - mood interpretation
  - candidate retrieval
  - enrichment
  - ranking
  - streaming lookup
- Add integration coverage for:
  - mood flow end-to-end
  - roulette flow end-to-end
  - reroll behavior
  - degradation paths (rate limits, upstream failures)
- Keep golden fixtures for mood inputs and expected behavior.

## Observability Rules

- Use structured logs with request IDs across the full pipeline.
- Log per-stage latency and overall latency.
- Capture degraded mode explicitly as `WARN`.
- Avoid logging secrets or full credential-like payloads.

## Security and Secrets

- Never commit `.env` or raw API keys.
- Keep `.env.example` updated whenever a new env var is introduced.
- Validate required env vars at startup with clear error messages.

## Definition of Done (for each feature)

- Behavior matches PRD intent.
- Failure paths are handled (not just happy path).
- Tests added/updated and passing locally.
- Logs are sufficient to debug production issues.
- Docs updated (`README.md`, this file, or both) if behavior changed.

## Change Log (Working Memory)

Add short bullets here as decisions harden.

- 2026-02-07: Started with pragmatic defaults; coding style to be refined during implementation.
- 2026-02-07: Implemented deterministic fallbacks for mood interpretation/ranking when Anthropic is unavailable.
- 2026-02-07: Implemented reroll duplicate avoidance using recent `request_log` history for the same mood text.
- 2026-02-07: Tracked non-blocking product decisions in `docs/open_questions.md`.
- 2026-02-07: Updated to session-scoped reroll exclusions via `session_id`.
- 2026-02-07: Anthropic is now required in normal runtime; deterministic fallback is opt-in for local dev/testing only.
- 2026-02-07: Added JustWatch fallback link when direct Watchmode sources are unavailable.
- 2026-02-07: Added quality guards in retrieval (vote-count floor and hard minimum release year).
- 2026-02-07: Added explicit mood-text constraints for language, anti-anime filtering, and year phrases (e.g., "after 2000").
