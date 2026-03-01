from __future__ import annotations

from typing import Any

import httpx

SUBREDDITS = [
    "MovieSuggestions",
    "televisionsuggestions",
    "ifyoulikeblank",
    "NetflixBestOf",
    "horror",
]


class RedditScraper:
    def __init__(self, timeout_seconds: float = 15.0) -> None:
        self.timeout = httpx.Timeout(timeout_seconds)

    async def fetch_subreddit_posts(self, subreddit: str, listing: str = "new", limit: int = 25) -> list[dict[str, Any]]:
        url = f"https://www.reddit.com/r/{subreddit}/{listing}.json"
        params = {"limit": limit}
        headers = {"User-Agent": "watchthis-bot/0.1"}
        async with httpx.AsyncClient(timeout=self.timeout, headers=headers) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

        children = payload.get("data", {}).get("children", [])
        return [child.get("data", {}) for child in children if child.get("data")]

    async def fetch_default_seed(self, limit_per_subreddit: int = 50) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for subreddit in SUBREDDITS:
            posts = await self.fetch_subreddit_posts(subreddit, listing="top", limit=limit_per_subreddit)
            rows.extend(posts)
        return rows
