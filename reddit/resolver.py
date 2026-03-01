from __future__ import annotations

from clients.tmdb_client import TMDBClient


class TMDBResolver:
    def __init__(self, tmdb_client: TMDBClient) -> None:
        self.tmdb_client = tmdb_client

    async def resolve_title(self, title: str, media_type: str = "movie") -> int | None:
        results = await self.tmdb_client.search(title, media_type=media_type)
        if not results:
            return None
        return int(results[0]["id"])
