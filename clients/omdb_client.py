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
    def parse_awards(payload: dict[str, Any] | None) -> tuple[str | None, str | None]:
        """Return (raw_awards_string, compact_badge).

        Compact badge prioritizes the most prestigious surface form:
        Oscar Winner > Oscar Nominee > Emmy Winner > Emmy Nominee >
        Golden Globe Winner > Golden Globe Nominee. Generic "wins" are
        ignored — they don't read as a recommendation cue.
        """
        if not payload:
            return None, None

        raw = payload.get("Awards")
        if not isinstance(raw, str) or not raw.strip() or raw.strip() == "N/A":
            return None, None

        text = raw.strip()
        lowered = text.lower()

        priorities: list[tuple[str, str, str]] = [
            ("won", "oscar", "Oscar Winner"),
            ("nominated for", "oscar", "Oscar Nominee"),
            ("won", "primetime emmy", "Emmy Winner"),
            ("nominated for", "primetime emmy", "Emmy Nominee"),
            ("won", "emmy", "Emmy Winner"),
            ("nominated for", "emmy", "Emmy Nominee"),
            ("won", "golden globe", "Golden Globe Winner"),
            ("nominated for", "golden globe", "Golden Globe Nominee"),
            ("won", "bafta", "BAFTA Winner"),
            ("won", "palme d'or", "Palme d'Or Winner"),
        ]
        for verb, award, badge in priorities:
            if verb in lowered and award in lowered:
                return text, badge

        return text, None

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
