# WatchThis — Product Requirements Document

## Overview

WatchThis is a mood-based TV/movie recommendation engine. Users describe how they're feeling in free text (or hit a roulette button to skip input entirely), and the system returns a single, high-confidence recommendation with a poster, a personalized pitch explaining *why* it fits their mood, where to stream it, and aggregated ratings. The system prioritizes decisiveness over optionality — the goal is to eliminate decision paralysis, not add more choices.

**Target user:** Anyone who has spent 20 minutes scrolling Netflix and given up. Couples arguing about what to watch. People who know what vibe they want but not what title.

---

## Core User Flows

### Flow 1: Mood-Based Recommendation
1. User types a free-text mood description (e.g., "I just had a brutal day and want something cozy and funny with zero emotional stakes")
2. User optionally selects format preference: Movie / TV Episode / Series / Don't Care
3. User optionally selects length preference: Quick (<30 min) / Standard (30-60 min) / Long (60-120 min) / Epic (120+ min) / Don't Care
4. System returns a single recommendation card:
   - Poster image
   - Title + year
   - Format + runtime
   - 1-2 sentence personalized pitch tied to the user's mood input
   - Where to stream (with platform icons/names)
   - Ratings: TMDB score, Rotten Tomatoes, Metacritic, IMDB
   - "Spin Again" button (re-rolls with same mood input)

### Flow 2: Roulette Mode
1. User hits the "Just Pick Something" / roulette button — no text input required
2. User can still optionally set format and length toggles
3. System returns a recommendation card (same format as above) with a generic pitch (e.g., "Trending right now and highly rated — give it a shot")
4. "Spin Again" re-rolls

---

## System Architecture

### High-Level Flow

```
User Input (mood text + filters)
        │
        ▼
┌─────────────────────────┐
│   Recommendation Engine  │
│   (Orchestrator)         │
│                          │
│  1. Mood Interpretation  │◄── Claude Haiku (fast, cheap)
│     → genres, keywords,  │
│       tone descriptors   │
│                          │
│  2. Candidate Retrieval  │◄── TMDB Discover API
│     → 20-40 candidates   │
│     filtered by format,  │
│     length, quality      │
│                          │
│  3. Signal Enrichment    │◄── Reddit Recommendation DB
│     → boost/penalize     │    OMDb Ratings
│     based on community   │    TMDB Keywords
│     signal               │
│                          │
│  4. Ranking + Selection  │◄── Claude Sonnet (quality matters here)
│     → pick THE ONE       │
│     → generate pitch     │
│                          │
│  5. Streaming Lookup     │◄── Watchmode API
│     → where to watch     │
└─────────────────────────┘
        │
        ▼
   Recommendation Card
   (returned to client)
```

### Component Breakdown

#### 1. Mood Interpreter (Claude Haiku)

**Purpose:** Parse free-text mood input into structured search parameters.

**Input:** Raw mood string (e.g., "I want something dark and twisty, like a psychological thriller but not too violent")

**Output (JSON):**
```json
{
  "genres": [53, 9648],           // TMDB genre IDs: Thriller, Mystery
  "genre_operator": "OR",         // AND or OR for genre combination
  "keywords": ["psychological", "twist ending", "suspense"],
  "mood_tags": ["dark", "cerebral", "tense"],
  "exclude_genres": [27],         // Horror (user said "not too violent")
  "exclude_keywords": ["gore", "slasher"],
  "min_vote_average": 6.5,        // Quality floor
  "min_vote_count": 100,          // Relevance floor
  "year_range": null,             // null = no preference
  "tone": "dark-cerebral"         // Canonical tone label for Reddit matching
}
```

**Model choice rationale:** Haiku is sufficient for structured extraction. This is a classification/parsing task, not a creative one. Keeps latency low and cost minimal since this runs on every request.

**Prompt design notes:**
- Include the full TMDB genre ID mapping in the system prompt (static, ~20 genres for movies, ~16 for TV)
- Include a curated keyword vocabulary mapped to TMDB keyword IDs for common mood descriptors
- Handle edge cases: vague inputs ("something good"), contradictory inputs ("scary but not scary"), non-English mood words
- For roulette mode: skip this step entirely, use a random genre + "trending" as the discovery parameters

#### 2. Candidate Retrieval (TMDB Discover API)

**Purpose:** Pull a pool of 20-40 candidates matching the interpreted mood.

**API endpoints used:**
- `GET /discover/movie` — for movie candidates
- `GET /discover/tv` — for TV show candidates
- `GET /trending/{media_type}/{time_window}` — for roulette mode and recency boost

**Query construction:**
```
/discover/movie?
  with_genres={genre_ids}           // from mood interpreter
  without_genres={exclude_ids}      // exclusions
  with_keywords={keyword_ids}       // TMDB keyword IDs (requires ID lookup)
  vote_average.gte={min_vote}       // quality floor
  vote_count.gte={min_count}        // relevance floor
  with_runtime.gte={min_runtime}    // from length filter
  with_runtime.lte={max_runtime}    // from length filter
  sort_by=vote_average.desc         // or popularity.desc for broader results
  page=1
```

**Length filter mapping:**
| User Selection | Runtime Filter (movies) | TV Handling |
|---|---|---|
| Quick (<30 min) | N/A (skip movies) | episode_run_time filter or flag for sitcoms |
| Standard (30-60 min) | 30-60 min | Standard TV episodes |
| Long (60-120 min) | 60-120 min | Prestige TV episodes or short movies |
| Epic (120+ min) | 120+ min | Skip TV, movies only |
| Don't Care | No filter | Include both |

**Candidate enrichment:**
For each candidate returned, fetch additional details via `append_to_response`:
```
/movie/{id}?append_to_response=keywords,credits
```
This gives us keywords (for Reddit matching) and top cast (for the pitch).

**Caching strategy:**
- Cache TMDB Discover results by query hash for 6 hours (content doesn't change frequently)
- Cache individual movie/show details for 24 hours
- Cache genre and keyword ID lists indefinitely (refresh weekly)

#### 3. Signal Enrichment

##### 3a. Reddit Recommendation Database

**Purpose:** Boost candidates that real humans frequently co-recommend for similar moods/tastes.

**Data model:**
```sql
CREATE TABLE reddit_recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_title TEXT NOT NULL,           -- "if you liked X"
    source_tmdb_id INTEGER,              -- TMDB ID for source (nullable, resolved async)
    recommended_title TEXT NOT NULL,      -- "watch Y"
    recommended_tmdb_id INTEGER,         -- TMDB ID for rec (nullable, resolved async)
    mood_tags TEXT,                       -- JSON array of extracted mood descriptors
    subreddit TEXT NOT NULL,             -- source subreddit
    post_score INTEGER DEFAULT 0,        -- Reddit post/comment score (proxy for agreement)
    comment_count INTEGER DEFAULT 0,     -- engagement signal
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    post_url TEXT                         -- source URL for debugging
);

CREATE INDEX idx_rec_tmdb ON reddit_recommendations(recommended_tmdb_id);
CREATE INDEX idx_source_tmdb ON reddit_recommendations(source_tmdb_id);
CREATE INDEX idx_mood_tags ON reddit_recommendations(mood_tags);

CREATE TABLE reddit_scrape_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subreddit TEXT NOT NULL,
    last_scraped_at TIMESTAMP,
    posts_processed INTEGER,
    pairs_extracted INTEGER,
    status TEXT                           -- success, partial, failed
);
```

**Subreddits to scrape:**
- r/MovieSuggestions (~2.5M members) — primary source
- r/televisionsuggestions (~350K) — TV-specific
- r/ifyoulikeblank (~1.4M) — cross-media "if you like X try Y"
- r/NetflixBestOf (~2M) — streaming-specific picks
- r/horror (for horror mood tags specifically)
- r/MovieSuggestions top posts of all time + last 2 years of weekly threads

**Scraping approach:**
- Use Reddit's JSON API (append `.json` to any Reddit URL — no auth needed for public posts)
- Extract recommendation pairs using Claude Haiku: feed post title + top 10 comments, extract structured `{source, recommended, mood_tags}` pairs
- Run weekly via cron job
- Initial seed: scrape top 1000 posts from each subreddit (one-time)
- Weekly refresh: scrape new posts from the past 7 days
- Resolve TMDB IDs asynchronously via TMDB search API after extraction

**Scoring integration:**
When ranking candidates, check if the candidate's TMDB ID appears in `reddit_recommendations`:
- Appears as `recommended_tmdb_id` with matching mood tags → boost score by 1.5x
- Appears with high `post_score` (>100 upvotes) → additional 1.2x boost
- Appears frequently (>3 independent recommendations) → additional 1.3x boost
- Net boost is multiplicative, capped at 3x

##### 3b. OMDb Ratings Enrichment

**Purpose:** Add Rotten Tomatoes, Metacritic, and IMDB ratings to candidates.

**API:** OMDb API (free tier: 1,000 calls/day)

**Lookup:** By IMDB ID (TMDB provides `imdb_id` in movie details)
```
GET http://www.omdbapi.com/?i={imdb_id}&apikey={key}
```

**Response fields used:**
- `Ratings[].Source` / `Ratings[].Value` — RT, Metacritic, IMDB
- `Metascore` — numeric Metacritic score
- `imdbRating` — numeric IMDB score

**Caching:** Cache OMDb responses by IMDB ID for 7 days (ratings don't change frequently).

**Rate limit management:** 
- 1,000 calls/day = ~41/hour
- Only fetch OMDb for the final 5-10 candidates after initial ranking, not all 40
- Cache aggressively to minimize API calls

#### 4. Ranking + Selection (Claude Sonnet)

**Purpose:** Given enriched candidates, pick the single best match and generate the personalized pitch.

**Input to Sonnet:**
```json
{
  "user_mood": "original mood text",
  "user_filters": { "format": "movie", "length": "standard" },
  "candidates": [
    {
      "tmdb_id": 550,
      "title": "Fight Club",
      "year": 1999,
      "genres": ["Drama", "Thriller"],
      "overview": "...",
      "vote_average": 8.4,
      "runtime": 139,
      "keywords": ["dual identity", "nihilism", "twist ending"],
      "rt_score": "79%",
      "metacritic": 66,
      "imdb_rating": 8.8,
      "reddit_boost": 2.1,
      "reddit_mood_match": ["dark", "mind-bending", "twist"],
      "top_cast": ["Brad Pitt", "Edward Norton"]
    }
    // ... 5-10 candidates
  ]
}
```

**Output:**
```json
{
  "selected_tmdb_id": 550,
  "pitch": "After a brutal day, you need something that'll grab you by the collar and not let go. Fight Club starts slow and seductive, then detonates — it's the kind of movie that makes you forget you were tired. Don't look up spoilers.",
  "confidence": 0.87,
  "reasoning": "Strong mood match (dark, cerebral, twist), high Reddit signal for 'bad day' moods, universal streaming availability"
}
```

**Model choice rationale:** Sonnet is the right balance of quality and cost here. The pitch needs to feel genuinely tailored — this is the moment that makes the product feel magical vs. generic. Haiku pitches would be noticeably worse. Opus is overkill for this task.

**Prompt design notes:**
- Instruct the model to write the pitch in second person, directly addressing the user's stated mood
- Keep pitch to 2 sentences max — punchy, not a review
- Avoid spoilers explicitly
- For roulette mode: write a lighter, more playful pitch since there's no mood to mirror
- Include `confidence` score so we can track recommendation quality over time
- Include `reasoning` for internal logging/tracing (not shown to user)

#### 5. Streaming Availability (Watchmode API)

**Purpose:** Tell the user where they can actually watch the recommendation right now.

**API:** Watchmode (free tier: 1,000 calls)

**Lookup flow:**
1. Search Watchmode by TMDB ID: `GET /v1/search/?search_field=tmdb_movie_id&search_value={tmdb_id}`
2. Get streaming sources: `GET /v1/title/{watchmode_id}/sources/`

**Response fields used:**
- `source_id` — streaming service ID
- `name` — service name (Netflix, Hulu, etc.)
- `type` — "sub" (subscription), "rent", "buy", "free"
- `web_url` — direct link to watch
- `format` — SD/HD/4K

**Display priority:** Show subscription services first (most users have these), then free, then rent/buy.

**Caching:** Cache streaming availability by TMDB ID for 48 hours. Streaming catalogs change but not hourly.

**Rate limit management:**
- Only call Watchmode for the single selected recommendation (not all candidates)
- 1,000 calls/month = ~33/day on free tier
- If we exhaust the free tier, degrade gracefully: show the recommendation without streaming links, with a "Check JustWatch.com" fallback link

---

## Data Layer

### Database: SQLite (local dev) → PostgreSQL (production)

**Tables:**

```sql
-- Cache for TMDB discover results
CREATE TABLE tmdb_discover_cache (
    query_hash TEXT PRIMARY KEY,
    response_json TEXT NOT NULL,
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

-- Cache for individual title details (TMDB + OMDb combined)
CREATE TABLE title_cache (
    tmdb_id INTEGER PRIMARY KEY,
    media_type TEXT NOT NULL,              -- "movie" or "tv"
    tmdb_data JSON NOT NULL,              -- full TMDB response
    omdb_data JSON,                        -- full OMDb response (nullable)
    watchmode_data JSON,                   -- streaming availability (nullable)
    tmdb_cached_at TIMESTAMP,
    omdb_cached_at TIMESTAMP,
    watchmode_cached_at TIMESTAMP
);

-- Reddit recommendations (see section 3a above)
-- reddit_recommendations table
-- reddit_scrape_log table

-- Request log for tracing and analytics
CREATE TABLE request_log (
    id TEXT PRIMARY KEY,                   -- UUID
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    mood_input TEXT,                        -- raw user input (null for roulette)
    format_filter TEXT,                     -- movie/tv/episode/any
    length_filter TEXT,                     -- quick/standard/long/epic/any
    mood_interpretation JSON,              -- Haiku output
    candidates_count INTEGER,              -- how many TMDB returned
    selected_tmdb_id INTEGER,              -- what was picked
    selected_title TEXT,                   -- for quick log scanning
    pitch TEXT,                            -- generated pitch
    confidence FLOAT,                      -- model confidence
    reasoning TEXT,                        -- model reasoning
    latency_ms INTEGER,                    -- total request time
    latency_mood_ms INTEGER,              -- Haiku interpretation time
    latency_tmdb_ms INTEGER,              -- TMDB fetch time
    latency_enrichment_ms INTEGER,        -- OMDb + Reddit lookup time
    latency_ranking_ms INTEGER,           -- Sonnet ranking time
    latency_streaming_ms INTEGER,         -- Watchmode lookup time
    is_roulette BOOLEAN DEFAULT FALSE,
    is_reroll BOOLEAN DEFAULT FALSE,
    reroll_of TEXT,                        -- UUID of original request (if reroll)
    error TEXT                             -- null if success
);
```

### TMDB Genre ID Reference (hardcoded)

**Movie genres:**
| ID | Name |
|---|---|
| 28 | Action |
| 12 | Adventure |
| 16 | Animation |
| 35 | Comedy |
| 80 | Crime |
| 99 | Documentary |
| 18 | Drama |
| 10751 | Family |
| 14 | Fantasy |
| 36 | History |
| 27 | Horror |
| 10402 | Music |
| 9648 | Mystery |
| 10749 | Romance |
| 878 | Science Fiction |
| 10770 | TV Movie |
| 53 | Thriller |
| 10752 | War |
| 37 | Western |

**TV genres:**
| ID | Name |
|---|---|
| 10759 | Action & Adventure |
| 16 | Animation |
| 35 | Comedy |
| 80 | Crime |
| 99 | Documentary |
| 18 | Drama |
| 10751 | Family |
| 10762 | Kids |
| 9648 | Mystery |
| 10763 | News |
| 10764 | Reality |
| 10765 | Sci-Fi & Fantasy |
| 10766 | Soap |
| 10767 | Talk |
| 10768 | War & Politics |
| 37 | Western |

---

## API Keys & External Services

| Service | Free Tier Limits | Key Env Var |
|---|---|---|
| TMDB | ~40 req/10 sec, no daily cap | `TMDB_API_KEY` |
| Watchmode | 1,000 calls total (free tier) | `WATCHMODE_API_KEY` |
| OMDb | 1,000 calls/day | `OMDB_API_KEY` |
| Anthropic (Claude) | Pay per token | `ANTHROPIC_API_KEY` |

---

## Tracing & Observability

### Structured Logging

Every request logs to `request_log` table with full pipeline breakdown:
- Input parameters
- Each stage output (mood interpretation, candidate count, selection, pitch)
- Per-stage latency
- Errors at any stage

### Log Levels

```
INFO  — successful recommendation served
WARN  — degraded response (e.g., Watchmode unavailable, OMDb rate limited)
ERROR — pipeline failure (e.g., TMDB down, Claude API error)
DEBUG — full candidate list, scoring breakdown, cache hits/misses
```

### Metrics to Track (via request_log queries)

- **Recommendations per day** — usage volume
- **Average latency** — total and per-stage
- **Reroll rate** — % of requests that trigger "spin again" (proxy for recommendation quality)
- **Cache hit rate** — per cache layer (TMDB, OMDb, Watchmode)
- **API budget consumption** — daily OMDb calls, cumulative Watchmode calls
- **Error rate** — by stage
- **Confidence distribution** — are we consistently confident or guessing?
- **Reddit boost frequency** — how often does Reddit signal influence the pick?

### Future: Langfuse Integration

When ready to add LLM-specific tracing:
- Wrap Haiku and Sonnet calls with Langfuse trace decorators
- Track token usage, prompt versions, latency per model call
- Enable prompt A/B testing (e.g., different pitch styles)
- Track cost per recommendation

---

## Testing Strategy

### Unit Tests

**Mood Interpreter:**
- Parses common mood descriptions into correct genre/keyword combinations
- Handles edge cases: empty input, very long input, non-English, emoji-only, contradictory inputs
- Correctly maps exclusion language ("not too violent") to `exclude_genres`
- Returns valid TMDB genre IDs only

**Candidate Retrieval:**
- Constructs correct TMDB API query params from mood interpretation
- Handles format/length filter combinations correctly
- Handles empty TMDB results gracefully (broadens search)
- Respects cache TTLs

**Signal Enrichment:**
- Reddit boost calculation is correct (multiplicative, capped at 3x)
- OMDb lookup handles missing IMDB IDs
- OMDb lookup handles missing/null ratings gracefully
- Cache reads/writes work correctly

**Ranking:**
- Sonnet receives correctly formatted candidate list
- Handles single candidate (just pick it)
- Handles all candidates having low confidence
- Pitch output respects length constraint (2 sentences)

**Streaming Lookup:**
- Watchmode lookup by TMDB ID works for movies and TV
- Handles "not available on any service" case
- Displays subscription services before rent/buy
- Graceful degradation when Watchmode is unavailable

### Integration Tests

- **Full pipeline: mood → recommendation** — end-to-end with real API calls (use test mood inputs with known expected genres)
- **Full pipeline: roulette → recommendation** — end-to-end without mood input
- **Reroll: same mood → different recommendation** — verify we don't return the same title on spin again
- **Cache behavior** — verify cache hits on repeated queries, cache expiry works
- **Rate limit handling** — simulate OMDb/Watchmode exhaustion, verify graceful degradation
- **Error propagation** — TMDB down → meaningful error, Claude down → meaningful error

### Test Data

Maintain a fixture set of 10 "golden" mood inputs with expected behavior:
1. "cozy comfort comedy" → should return comedy/romance, high rating
2. "dark psychological thriller" → should return thriller/mystery
3. "something my kids would like" → should return family/animation, PG
4. "mind-bending sci-fi" → should return sci-fi with keywords like "twist"
5. "I want to cry" → should return drama, keywords like "tearjerker"
6. "background noise while I cook" → should return light sitcom/reality
7. "date night movie" → should return romance/comedy, not too heavy
8. "can't sleep, need something long and slow" → should return long runtime, meditative
9. "just had a breakup" → should return comfort content, avoid romance
10. "roulette" → should return something trending + well-rated

---

## Project Structure

```
watchthis/
├── README.md
├── requirements.txt                  # Python dependencies
├── .env.example                      # Template for API keys
├── config.py                         # Settings, env vars, constants
│
├── core/
│   ├── __init__.py
│   ├── orchestrator.py               # Main pipeline: mood → recommendation
│   ├── mood_interpreter.py           # Claude Haiku: text → structured params
│   ├── candidate_retrieval.py        # TMDB Discover queries
│   ├── signal_enrichment.py          # Reddit boost + OMDb ratings
│   ├── ranker.py                     # Claude Sonnet: pick + pitch
│   └── streaming_lookup.py           # Watchmode: where to watch
│
├── clients/
│   ├── __init__.py
│   ├── tmdb_client.py                # TMDB API wrapper
│   ├── omdb_client.py                # OMDb API wrapper
│   ├── watchmode_client.py           # Watchmode API wrapper
│   └── anthropic_client.py           # Claude API wrapper (Haiku + Sonnet)
│
├── data/
│   ├── __init__.py
│   ├── database.py                   # SQLite connection, migrations
│   ├── cache.py                      # Cache read/write/invalidation
│   ├── models.py                     # Pydantic models for all data types
│   └── migrations/
│       └── 001_initial.sql           # Schema creation
│
├── reddit/
│   ├── __init__.py
│   ├── scraper.py                    # Reddit JSON API scraper
│   ├── extractor.py                  # Claude Haiku: post → rec pairs
│   ├── resolver.py                   # TMDB ID resolution for titles
│   └── cron.py                       # Weekly scrape job entrypoint
│
├── api/
│   ├── __init__.py
│   ├── server.py                     # FastAPI app (minimal, for future FE)
│   └── routes.py                     # /recommend, /roulette endpoints
│
├── cli/
│   └── main.py                       # Terminal interface for local use
│
├── tests/
│   ├── __init__.py
│   ├── test_mood_interpreter.py
│   ├── test_candidate_retrieval.py
│   ├── test_signal_enrichment.py
│   ├── test_ranker.py
│   ├── test_streaming_lookup.py
│   ├── test_orchestrator.py          # Integration tests
│   ├── test_reddit_scraper.py
│   ├── conftest.py                   # Fixtures, mock API responses
│   └── fixtures/
│       ├── tmdb_responses.json       # Canned TMDB responses
│       ├── omdb_responses.json       # Canned OMDb responses
│       ├── watchmode_responses.json  # Canned Watchmode responses
│       └── golden_moods.json         # 10 test mood inputs + expected outputs
│
├── scripts/
│   ├── seed_reddit.py                # One-time initial Reddit scrape
│   └── run_tests.sh                  # Test runner with coverage
│
└── logs/
    └── .gitkeep
```

---

## Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| Language | Python 3.11+ | Best Anthropic SDK support, fast prototyping |
| API Framework | FastAPI | Async, auto-docs, easy to add FE later |
| Database | SQLite (local) → PostgreSQL (prod) | Zero setup locally, easy migration path |
| ORM / Query | Raw SQL + Pydantic models | Keep it simple, no ORM overhead |
| HTTP Client | httpx (async) | Async requests to all external APIs |
| LLM Client | anthropic Python SDK | Official SDK, supports Haiku/Sonnet/Opus |
| Testing | pytest + pytest-asyncio | Standard Python testing |
| CLI | Typer or argparse | Simple terminal interface |
| Task Scheduling | APScheduler or cron | Reddit weekly scrape |
| Deployment (future) | Railway | Simple, supports Python + PostgreSQL, cheap |

---

## Deployment Notes (Future)

For local development:
- SQLite database stored at `./data/watchthis.db`
- All API keys in `.env` file
- Run via `python cli/main.py` for terminal or `uvicorn api.server:app` for API

For production (Railway):
- PostgreSQL addon for database
- Environment variables for API keys
- Single `Procfile`: `web: uvicorn api.server:app --host 0.0.0.0 --port $PORT`
- Reddit cron via Railway cron jobs or APScheduler background task

---

## Open Questions / Future Considerations

1. **Duplicate avoidance on reroll** — Track the last N recommendations per session and exclude from candidate pool. For v1, pass excluded TMDB IDs to the ranker and instruct it to not re-pick.

2. **Cold start for Reddit data** — Initial scrape may take several hours for 5,000+ posts across 5 subreddits. Run `scripts/seed_reddit.py` as a one-time setup step before first use.

3. **Watchmode free tier exhaustion** — 1,000 lifetime calls is tight. Monitor usage closely. Upgrade to paid ($5/month for 10K calls) if the product gets traction. Degrade gracefully in the meantime.

4. **LLM cost estimation** — Rough per-request cost:
   - Haiku (mood interpretation): ~500 input + 200 output tokens = ~$0.0003
   - Sonnet (ranking + pitch): ~2000 input + 300 output tokens = ~$0.012
   - Total per recommendation: ~$0.013
   - Reddit scraping (Haiku extraction): ~$0.001 per post
   - 1,000 recs/month ≈ $13/month in LLM costs

5. **User preferences / history** — v1 is stateless. Future version could store preferences ("I hate horror", "I love A24 films") and past recommendations to improve over time.

6. **Group mode** — "We both like X but disagree on Y" — future feature, not v1.
