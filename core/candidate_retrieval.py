from __future__ import annotations

import asyncio
from typing import Any

from clients.tmdb_client import TMDBClient
from config import Settings, get_settings
from data.cache import compute_query_hash, get_tmdb_discover_cache, set_tmdb_discover_cache
from data.database import managed_connection
from data.models import Candidate, FormatFilter, LengthFilter, MoodInterpretation, UserFilters


class CandidateRetriever:
    poster_base_url = "https://image.tmdb.org/t/p/w780"

    def __init__(self, tmdb_client: TMDBClient, settings: Settings | None = None) -> None:
        self.tmdb_client = tmdb_client
        self.settings = settings or get_settings()

    async def retrieve(
        self,
        interpretation: MoodInterpretation,
        filters: UserFilters,
        is_roulette: bool = False,
        excluded_tmdb_ids: list[int] | None = None,
    ) -> list[Candidate]:
        excluded = set(excluded_tmdb_ids or [])
        media_types = self._resolve_media_types(filters.format)

        raw_rows: list[dict[str, Any]] = []
        for media_type in media_types:
            if is_roulette:
                discovered = await self.tmdb_client.trending(media_type=media_type if media_type in {"movie", "tv"} else "all")
                raw_rows.extend(discovered)
            else:
                raw_rows.extend(await self._discover_variants(media_type, interpretation, filters.length))

        if not raw_rows and not is_roulette:
            fallback = MoodInterpretation(
                genres=[],
                keywords=interpretation.keywords,
                mood_tags=interpretation.mood_tags,
                min_vote_average=max(5.8, interpretation.min_vote_average - 0.8),
                min_vote_count=max(80, interpretation.min_vote_count // 2),
                year_range=interpretation.year_range,
                original_language=interpretation.original_language,
                tone=interpretation.tone,
            )
            for media_type in media_types:
                raw_rows.extend(await self._discover_variants(media_type, fallback, filters.length))

        deduped = self._dedupe_rows(raw_rows)
        details = await self._fetch_details_batch(deduped[:80], media_types)

        candidates: list[Candidate] = []
        for row in details:
            candidate = self._to_candidate(row)
            if candidate.tmdb_id in excluded:
                continue
            if not self._runtime_matches_length(candidate.runtime, filters.length, candidate.media_type):
                continue
            if not self._matches_year_range(candidate, interpretation):
                continue
            if self._matches_exclusions(candidate, interpretation):
                continue
            candidates.append(candidate)

        candidates.sort(
            key=lambda item: (item.vote_average, item.vote_count, item.popularity or 0.0),
            reverse=True,
        )
        return candidates[:60]

    async def _discover_variants(
        self,
        media_type: str,
        interpretation: MoodInterpretation,
        length: LengthFilter,
    ) -> list[dict[str, Any]]:
        tasks = [
            self._discover_with_cache(
                media_type,
                self._build_discover_params(interpretation, length, media_type, sort_by="vote_average.desc"),
                page=1,
            ),
            self._discover_with_cache(
                media_type,
                self._build_discover_params(interpretation, length, media_type, sort_by="popularity.desc"),
                page=1,
            ),
            self._discover_with_cache(
                media_type,
                self._build_discover_params(interpretation, length, media_type, sort_by="vote_average.desc"),
                page=2,
            ),
        ]
        results = await asyncio.gather(*tasks)
        rows: list[dict[str, Any]] = []
        for payload in results:
            rows.extend(payload)
        return rows

    async def _discover_with_cache(self, media_type: str, params: dict[str, Any], page: int = 1) -> list[dict[str, Any]]:
        cache_key = compute_query_hash({"media_type": media_type, "page": page, **params})
        with managed_connection() as conn:
            cached = get_tmdb_discover_cache(conn, cache_key)
            if cached is not None:
                return cached

        discovered = await self.tmdb_client.discover(media_type, params=params, page=page)

        with managed_connection() as conn:
            set_tmdb_discover_cache(conn, cache_key, discovered, ttl_hours=self.settings.tmdb_discover_ttl_hours)

        return discovered

    async def _fetch_details_batch(
        self,
        rows: list[dict[str, Any]],
        requested_media_types: list[str],
    ) -> list[dict[str, Any]]:
        async def fetch(row: dict[str, Any]) -> dict[str, Any] | None:
            tmdb_id = int(row["id"])
            media_type = self._infer_media_type(row, requested_media_types)
            try:
                payload = await self.tmdb_client.get_details(media_type, tmdb_id)
                payload["_media_type"] = media_type
                return payload
            except Exception:
                return None

        tasks = [fetch(row) for row in rows]
        results = await asyncio.gather(*tasks)
        return [result for result in results if result is not None]

    @staticmethod
    def _resolve_media_types(format_filter: FormatFilter) -> list[str]:
        if format_filter == FormatFilter.MOVIE:
            return ["movie"]
        if format_filter in {FormatFilter.TV, FormatFilter.EPISODE}:
            return ["tv"]
        return ["movie", "tv"]

    def _build_discover_params(
        self,
        interpretation: MoodInterpretation,
        length: LengthFilter,
        media_type: str,
        sort_by: str,
    ) -> dict[str, Any]:
        vote_floor = max(self.settings.quality_vote_count_floor, interpretation.min_vote_count)
        params: dict[str, Any] = {
            "vote_average.gte": interpretation.min_vote_average,
            "vote_count.gte": vote_floor,
            "sort_by": sort_by,
        }

        if interpretation.genres:
            params["with_genres"] = ",".join(str(value) for value in interpretation.genres)
        if interpretation.exclude_genres:
            params["without_genres"] = ",".join(str(value) for value in interpretation.exclude_genres)
        if interpretation.original_language:
            params["with_original_language"] = interpretation.original_language

        start_year, end_year = self._effective_year_range(interpretation)
        if media_type == "movie":
            params["primary_release_date.gte"] = f"{start_year}-01-01"
            params["primary_release_date.lte"] = f"{end_year}-12-31"
        else:
            params["first_air_date.gte"] = f"{start_year}-01-01"
            params["first_air_date.lte"] = f"{end_year}-12-31"

        runtime = CandidateRetriever._runtime_bounds(length, media_type)
        if runtime:
            params["with_runtime.gte"] = runtime[0]
            params["with_runtime.lte"] = runtime[1]

        return params

    @staticmethod
    def _runtime_bounds(length: LengthFilter, media_type: str) -> tuple[int, int] | None:
        if media_type == "movie":
            if length == LengthFilter.QUICK:
                return (60, 95)
            if length == LengthFilter.STANDARD:
                return (90, 130)
            if length == LengthFilter.LONG:
                return (120, 170)
            if length == LengthFilter.EPIC:
                return (140, 400)
            return None

        if length == LengthFilter.QUICK:
            return (0, 30)
        if length == LengthFilter.STANDARD:
            return (30, 60)
        if length == LengthFilter.LONG:
            return (60, 120)
        if length == LengthFilter.EPIC:
            return (120, 400)
        return None

    @staticmethod
    def _runtime_matches_length(runtime: int | None, length: LengthFilter, media_type: str) -> bool:
        if runtime is None or length == LengthFilter.ANY:
            return True

        bounds = CandidateRetriever._runtime_bounds(length, media_type)
        if not bounds:
            return True
        return bounds[0] <= runtime <= bounds[1]

    def _effective_year_range(self, interpretation: MoodInterpretation) -> tuple[int, int]:
        start_year = self.settings.min_release_year
        end_year = 2100

        if interpretation.year_range:
            start_year = max(start_year, interpretation.year_range[0])
            end_year = min(end_year, interpretation.year_range[1])

        if start_year > end_year:
            start_year, end_year = end_year, start_year
        return start_year, end_year

    def _matches_year_range(self, candidate: Candidate, interpretation: MoodInterpretation) -> bool:
        if candidate.year is None:
            return True
        start_year, end_year = self._effective_year_range(interpretation)
        return start_year <= candidate.year <= end_year

    @staticmethod
    def _matches_exclusions(candidate: Candidate, interpretation: MoodInterpretation) -> bool:
        if not interpretation.exclude_keywords:
            return False

        text = " ".join(
            [
                candidate.title.lower(),
                candidate.overview.lower(),
                " ".join(keyword.lower() for keyword in candidate.keywords),
                " ".join(genre.lower() for genre in candidate.genres),
            ]
        )
        return any(keyword.lower() in text for keyword in interpretation.exclude_keywords)

    @staticmethod
    def _dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[int] = set()
        deduped: list[dict[str, Any]] = []
        for row in rows:
            tmdb_id = int(row.get("id", 0))
            if not tmdb_id or tmdb_id in seen:
                continue
            seen.add(tmdb_id)
            deduped.append(row)
        return deduped

    @staticmethod
    def _infer_media_type(row: dict[str, Any], requested_media_types: list[str]) -> str:
        if row.get("media_type") in {"movie", "tv"}:
            return str(row["media_type"])
        if "title" in row:
            return "movie"
        if "name" in row:
            return "tv"
        return requested_media_types[0]

    @staticmethod
    def _to_candidate(detail: dict[str, Any]) -> Candidate:
        media_type = detail.get("_media_type") or "movie"

        title = detail.get("title") or detail.get("name") or "Unknown"
        release_date = detail.get("release_date") or detail.get("first_air_date")
        year = int(release_date[:4]) if release_date and len(release_date) >= 4 else None

        genre_rows = detail.get("genres") or []
        genre_names = [row.get("name") for row in genre_rows if row.get("name")]

        keyword_block = detail.get("keywords") or {}
        keyword_rows = keyword_block.get("keywords") or keyword_block.get("results") or []
        keywords = [row.get("name") for row in keyword_rows if row.get("name")]

        cast_rows = detail.get("credits", {}).get("cast", [])
        top_cast = [row.get("name") for row in cast_rows[:3] if row.get("name")]

        runtime = detail.get("runtime")
        if runtime is None:
            episode_run_time = detail.get("episode_run_time") or []
            runtime = episode_run_time[0] if episode_run_time else None

        imdb_id = detail.get("imdb_id") or detail.get("external_ids", {}).get("imdb_id")
        poster_path = detail.get("poster_path")
        poster_url = None
        if isinstance(poster_path, str) and poster_path.strip():
            normalized = poster_path if poster_path.startswith("/") else f"/{poster_path}"
            poster_url = f"{CandidateRetriever.poster_base_url}{normalized}"
        production_countries = detail.get("production_countries") or []
        origin_countries = detail.get("origin_country") or []
        primary_country = None
        if production_countries and isinstance(production_countries, list):
            first = production_countries[0]
            if isinstance(first, dict):
                primary_country = first.get("iso_3166_1")
        if not primary_country and origin_countries and isinstance(origin_countries, list):
            primary_country = origin_countries[0]

        return Candidate(
            tmdb_id=int(detail["id"]),
            media_type=media_type,
            title=title,
            year=year,
            poster_url=poster_url,
            primary_country=(str(primary_country).upper() if primary_country else None),
            original_language=(detail.get("original_language") or None),
            genres=genre_names,
            overview=detail.get("overview") or "",
            vote_average=float(detail.get("vote_average") or 0.0),
            vote_count=int(detail.get("vote_count") or 0),
            popularity=float(detail.get("popularity") or 0.0) if detail.get("popularity") is not None else None,
            runtime=int(runtime) if runtime is not None else None,
            keywords=keywords,
            top_cast=top_cast,
            imdb_id=imdb_id,
            raw=detail,
        )
