from __future__ import annotations

from urllib.parse import quote_plus

from clients.watchmode_client import WatchmodeClient
from data.models import StreamingSource


class StreamingLookup:
    def __init__(self, watchmode_client: WatchmodeClient) -> None:
        self.watchmode_client = watchmode_client

    async def get_sources(self, tmdb_id: int, media_type: str, title: str, year: int | None = None) -> list[StreamingSource]:
        try:
            sources = await self.watchmode_client.get_sources_for_tmdb_id(tmdb_id, media_type=media_type)
            if sources:
                return sources
            return [self._justwatch_fallback(title, year)]
        except Exception:
            return [self._justwatch_fallback(title, year)]

    @staticmethod
    def _justwatch_fallback(title: str, year: int | None = None) -> StreamingSource:
        query = f"{title} {year}" if year else title
        return StreamingSource(
            name="JustWatch",
            type="info",
            web_url=f"https://www.justwatch.com/us/search?q={quote_plus(query)}",
            format=None,
        )
