# WatchThis

Mood-based TV/movie recommendation engine that returns one decisive pick.

## Quick Start

1. Create a virtualenv and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Configure env vars:

```bash
cp .env.example .env
```

3. Run API:

```bash
uvicorn api.server:app --reload
```

4. Run CLI:

```bash
python -m cli.main recommend --session-id demo-user --mood "cozy comfort comedy"
python -m cli.main roulette --session-id demo-user
```

5. Validate integrations after adding keys:

```bash
python scripts/validate_integrations.py
```

6. Run end-to-end backend smoke test (starts API, checks health + recommend + reroll + roulette):

```bash
./scripts/smoke_api.sh
```

7. Run stress test:

```bash
python scripts/stress_test.py --requests 10 --with-rerolls
```

8. Inspect request tracing from SQLite log:

```bash
python scripts/trace_request.py --latest
python scripts/trace_request.py --request-id <REQUEST_ID>
```

## Curated Exceptions List

To allow specific titles below the RT floor, populate `data/curated_exceptions.md` with a markdown table:

```md
| title | media_type | year |
|---|---|---|
| School of Rock | movie | 2003 |
| Ted Lasso | tv | 2020 |
```

Config knobs:

- `WATCHTHIS_RT_MIN_SCORE` (default `75`)
- `WATCHTHIS_RT_FALLBACK_SCORE` (default `70`)
- `WATCHTHIS_CURATED_CATALOG_ENABLED` (default `true`)
- `WATCHTHIS_CURATED_CATALOG_PATH` (default `data/curated_exceptions.md`)

## Notes

- Anthropic is required by default (`ANTHROPIC_API_KEY`). If missing, recommendation requests return an explicit error.
- For local dev/testing only, set `WATCHTHIS_ALLOW_HEURISTIC_FALLBACK=true` to use deterministic fallback logic.
- Ranking model defaults to Sonnet; set `WATCHTHIS_USE_OPUS_FOR_RANKING=true` to route ranking/explanations to Opus.
- `session_id` should be stable per user context and is used for reroll duplicate avoidance.
- If Watchmode streaming sources are unavailable, the response includes a JustWatch fallback link.
- SQLite DB initializes automatically at first run.
