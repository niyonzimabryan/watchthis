# Product Decisions

## Confirmed

1. Anthropic dependency:
- Production behavior is strict.
- If `ANTHROPIC_API_KEY` is missing or Anthropic calls fail, return a clear error.
- Optional local override exists via `WATCHTHIS_ALLOW_HEURISTIC_FALLBACK=true` for development/testing.

2. Reroll scope:
- Reroll exclusion is session-based.
- Session is a stable client identifier (`session_id`) provided by the caller (for example from browser `localStorage`).
- Exclusions are read from `request_log` for that session, not globally across all users.

3. TV handling:
- V1 stays series-level for TV recommendations (no episode-level picking yet).

4. Ranking preference:
- No hard confidence floor right now.
- Ranking should prioritize taste fit and quality; popularity is secondary.

5. Streaming fallback:
- Primary path is direct provider links from Watchmode.
- If unavailable/rate-limited, return a JustWatch search fallback link.

## Remaining Follow-Ups

1. Frontend/session contract:
- FE should generate and persist one `session_id` per user context and pass it on every `/recommend` and `/roulette` call.
