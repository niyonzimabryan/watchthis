from __future__ import annotations

import json
import math
from typing import Any

from clients.omdb_client import OMDbClient
from config import Settings, get_settings
from data.cache import get_title_cache, upsert_title_cache
from data.database import managed_connection
from data.models import Candidate


class SignalEnricher:
    def __init__(self, omdb_client: OMDbClient, settings: Settings | None = None) -> None:
        self.omdb_client = omdb_client
        self.settings = settings or get_settings()

    async def enrich(self, candidates: list[Candidate], mood_tags: list[str]) -> list[Candidate]:
        if not candidates:
            return candidates

        for candidate in candidates:
            boost, matches = self._compute_reddit_boost(candidate.tmdb_id, mood_tags)
            candidate.reddit_boost = boost
            candidate.reddit_mood_match = matches

        sorted_for_omdb = sorted(candidates, key=self._omdb_priority_score, reverse=True)
        for candidate in sorted_for_omdb[: self.settings.omdb_enrichment_limit]:
            await self._apply_omdb(candidate)

        return candidates

    def _compute_reddit_boost(self, tmdb_id: int, mood_tags: list[str]) -> tuple[float, list[str]]:
        with managed_connection() as conn:
            rows = conn.execute(
                """
                SELECT mood_tags, post_score
                FROM reddit_recommendations
                WHERE recommended_tmdb_id = ?
                """,
                (tmdb_id,),
            ).fetchall()

        if not rows:
            return 1.0, []

        tag_set = {tag.lower() for tag in mood_tags}
        mood_matches: set[str] = set()

        boost = 1.0
        occurrences = 0
        for row in rows:
            raw_tags = row["mood_tags"]
            post_score = int(row["post_score"] or 0)
            parsed = self._parse_json_array(raw_tags)
            lower = {value.lower() for value in parsed}

            if tag_set and lower.intersection(tag_set):
                boost *= 1.5
                mood_matches.update(lower.intersection(tag_set))
                occurrences += 1
            if post_score > 100:
                boost *= 1.2

        if occurrences > 3:
            boost *= 1.3

        return min(3.0, round(boost, 2)), sorted(mood_matches)

    async def _apply_omdb(self, candidate: Candidate) -> None:
        cached = None
        with managed_connection() as conn:
            cached = get_title_cache(conn, candidate.tmdb_id)

        omdb_payload: dict[str, Any] | None = None
        if cached and cached.get("omdb_data"):
            omdb_payload = cached["omdb_data"]
        else:
            omdb_payload = await self.omdb_client.get_by_imdb_id(candidate.imdb_id)
            if omdb_payload:
                with managed_connection() as conn:
                    tmdb_data = candidate.raw or {"id": candidate.tmdb_id}
                    upsert_title_cache(
                        conn,
                        tmdb_id=candidate.tmdb_id,
                        media_type=candidate.media_type,
                        tmdb_data=tmdb_data,
                        omdb_data=omdb_payload,
                    )

        parsed = self.omdb_client.parse_ratings(omdb_payload)
        candidate.rt_score = parsed.get("rotten_tomatoes")
        candidate.metacritic = parsed.get("metacritic_numeric")
        candidate.imdb_rating = parsed.get("imdb_numeric")

    @staticmethod
    def _omdb_priority_score(candidate: Candidate) -> float:
        return (
            candidate.vote_average * 10
            + math.log10(max(1, candidate.vote_count)) * 5
            + (candidate.popularity or 0.0) * 0.05
            + candidate.reddit_boost * 2
        )

    @staticmethod
    def _parse_json_array(raw: str | None) -> list[str]:
        if not raw:
            return []
        try:
            value = json.loads(raw)
            if isinstance(value, list):
                return [str(item) for item in value]
        except json.JSONDecodeError:
            return []
        return []
