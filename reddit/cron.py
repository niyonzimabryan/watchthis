from __future__ import annotations

import json

from clients.tmdb_client import TMDBClient
from config import get_settings
from data.database import init_db, managed_connection
from reddit.extractor import RecommendationExtractor
from reddit.scraper import RedditScraper
from reddit.resolver import TMDBResolver


async def run_weekly_scrape(limit_per_subreddit: int = 50) -> None:
    settings = get_settings()
    init_db(settings)

    scraper = RedditScraper()
    extractor = RecommendationExtractor()
    resolver = TMDBResolver(TMDBClient(settings))

    posts = await scraper.fetch_default_seed(limit_per_subreddit=limit_per_subreddit)

    inserted = 0
    for post in posts:
        title = post.get("title", "")
        body = post.get("selftext", "")
        subreddit = post.get("subreddit", "unknown")
        post_score = int(post.get("score", 0) or 0)
        comment_count = int(post.get("num_comments", 0) or 0)
        post_url = f"https://www.reddit.com{post.get('permalink', '')}" if post.get("permalink") else None

        for pair in extractor.extract_pairs(title, body):
            rec_tmdb_id = await resolver.resolve_title(pair["recommended_title"], media_type="movie")
            source_tmdb_id = await resolver.resolve_title(pair["source_title"], media_type="movie")

            with managed_connection(settings.db_path_obj) as conn:
                conn.execute(
                    """
                    INSERT INTO reddit_recommendations (
                        source_title,
                        source_tmdb_id,
                        recommended_title,
                        recommended_tmdb_id,
                        mood_tags,
                        subreddit,
                        post_score,
                        comment_count,
                        post_url
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        pair["source_title"],
                        source_tmdb_id,
                        pair["recommended_title"],
                        rec_tmdb_id,
                        json.dumps(pair["mood_tags"], ensure_ascii=True),
                        subreddit,
                        post_score,
                        comment_count,
                        post_url,
                    ),
                )
                inserted += 1

    with managed_connection(settings.db_path_obj) as conn:
        conn.execute(
            """
            INSERT INTO reddit_scrape_log (subreddit, last_scraped_at, posts_processed, pairs_extracted, status)
            VALUES (?, CURRENT_TIMESTAMP, ?, ?, ?)
            """,
            ("ALL", len(posts), inserted, "success"),
        )
