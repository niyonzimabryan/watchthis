from __future__ import annotations

from typing import Any

import httpx

from config import Settings, get_settings
from data.models import StreamingSource


class WatchmodeClient:
    base_url = "https://api.watchmode.com/v1"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._timeout = httpx.Timeout(self.settings.http_timeout_seconds)

    async def get_sources_for_tmdb_id(self, tmdb_id: int, media_type: str = "movie") -> list[StreamingSource]:
        if not self.settings.watchmode_api_key:
            return []

        search_field = "tmdb_movie_id" if media_type == "movie" else "tmdb_tv_id"
        search_payload = await self._get(
            "/search/",
            {
                "apiKey": self.settings.watchmode_api_key,
                "search_field": search_field,
                "search_value": tmdb_id,
            },
        )

        title_results = search_payload.get("title_results", [])
        if not title_results:
            return []

        watchmode_id = title_results[0].get("id")
        if not watchmode_id:
            return []

        sources_payload = await self._get(
            f"/title/{watchmode_id}/sources/",
            {"apiKey": self.settings.watchmode_api_key},
        )

        selected_rows = self._select_region_rows(sources_payload)
        ranked = [self._to_source(row) for row in selected_rows if row.get("name")]
        ranked = self._dedupe_sources(ranked)
        ranked.sort(key=self._sort_priority)
        return ranked

    async def _get(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any] | list[dict[str, Any]]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self._timeout) as client:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()

    @staticmethod
    def _to_source(row: dict[str, Any]) -> StreamingSource:
        return StreamingSource(
            source_id=str(row.get("source_id")) if row.get("source_id") is not None else None,
            name=row.get("name", "Unknown"),
            type=row.get("type", "sub"),
            web_url=row.get("web_url"),
            format=row.get("format"),
        )

    @staticmethod
    def _sort_priority(source: StreamingSource) -> tuple[int, str]:
        order = {
            "sub": 0,
            "free": 1,
            "rent": 2,
            "buy": 3,
        }
        return (order.get(source.type, 9), source.name.lower())

    def _select_region_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        preferred_region = (self.settings.watch_region or "US").upper()
        preferred = [row for row in rows if str(row.get("region", "")).upper() == preferred_region]
        return preferred if preferred else rows

    @staticmethod
    def _dedupe_sources(rows: list[StreamingSource]) -> list[StreamingSource]:
        deduped: list[StreamingSource] = []
        seen: set[tuple[str, str, str]] = set()
        for row in rows:
            key = (row.name.lower(), row.type.lower(), (row.web_url or "").strip().lower())
            if key in seen:
                continue
            seen.add(key)
            deduped.append(row)
        return deduped
