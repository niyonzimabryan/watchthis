CREATE TABLE IF NOT EXISTS tmdb_discover_cache (
    query_hash TEXT PRIMARY KEY,
    response_json TEXT NOT NULL,
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS title_cache (
    tmdb_id INTEGER PRIMARY KEY,
    media_type TEXT NOT NULL,
    tmdb_data TEXT NOT NULL,
    omdb_data TEXT,
    watchmode_data TEXT,
    tmdb_cached_at TIMESTAMP,
    omdb_cached_at TIMESTAMP,
    watchmode_cached_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reddit_recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_title TEXT NOT NULL,
    source_tmdb_id INTEGER,
    recommended_title TEXT NOT NULL,
    recommended_tmdb_id INTEGER,
    mood_tags TEXT,
    subreddit TEXT NOT NULL,
    post_score INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    post_url TEXT
);

CREATE INDEX IF NOT EXISTS idx_rec_tmdb ON reddit_recommendations(recommended_tmdb_id);
CREATE INDEX IF NOT EXISTS idx_source_tmdb ON reddit_recommendations(source_tmdb_id);

CREATE TABLE IF NOT EXISTS reddit_scrape_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subreddit TEXT NOT NULL,
    last_scraped_at TIMESTAMP,
    posts_processed INTEGER,
    pairs_extracted INTEGER,
    status TEXT
);

CREATE TABLE IF NOT EXISTS request_log (
    id TEXT PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_id TEXT,
    mood_input TEXT,
    format_filter TEXT,
    length_filter TEXT,
    mood_interpretation TEXT,
    candidates_count INTEGER,
    selected_tmdb_id INTEGER,
    selected_title TEXT,
    pitch TEXT,
    confidence FLOAT,
    reasoning TEXT,
    latency_ms INTEGER,
    latency_mood_ms INTEGER,
    latency_tmdb_ms INTEGER,
    latency_enrichment_ms INTEGER,
    latency_ranking_ms INTEGER,
    latency_streaming_ms INTEGER,
    is_roulette BOOLEAN DEFAULT FALSE,
    is_reroll BOOLEAN DEFAULT FALSE,
    reroll_of TEXT,
    error TEXT
);
