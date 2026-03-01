from __future__ import annotations

from typing import Any

import httpx

from config import Settings, get_settings


class OMDbClient:
    base_url = "https://www.omdbapi.com/"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._timeout = httpx.Timeout(self.settings.http_timeout_seconds)

    async def get_by_imdb_id(self, imdb_id: str | None) -> dict[str, Any] | None:
        if not imdb_id or not self.settings.omdb_api_key:
            return None

        params = {
            "i": imdb_id,
            "apikey": self.settings.omdb_api_key,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            payload = response.json()

        if payload.get("Response") == "False":
            return None
        return payload

    @staticmethod
    def parse_ratings(payload: dict[str, Any] | None) -> dict[str, Any]:
        if not payload:
            return {}

        ratings = payload.get("Ratings", [])
        result: dict[str, Any] = {}
        for item in ratings:
            source = item.get("Source")
            value = item.get("Value")
            if not source or not value:
                continue
            key = source.lower().replace(" ", "_")
            result[key] = value

        imdb_rating = payload.get("imdbRating")
        metascore = payload.get("Metascore")

        if imdb_rating and imdb_rating != "N/A":
            try:
                result["imdb_numeric"] = float(imdb_rating)
            except ValueError:
                pass

        if metascore and metascore != "N/A":
            try:
                result["metacritic_numeric"] = int(metascore)
            except ValueError:
                pass

        return result
