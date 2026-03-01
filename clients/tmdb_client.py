from __future__ import annotations

from typing import Any

import httpx

from config import Settings, get_settings
from core.constants import MOCK_CATALOG


class TMDBClient:
    base_url = "https://api.themoviedb.org/3"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._timeout = httpx.Timeout(self.settings.http_timeout_seconds)

    async def discover(self, media_type: str, params: dict[str, Any], page: int = 1) -> list[dict[str, Any]]:
        if not self._has_auth():
            return self._mock_discover(media_type, params)

        endpoint = f"/discover/{'tv' if media_type in {'tv', 'episode'} else 'movie'}"
        query = {
            "page": page,
            **params,
        }
        auth_params, headers = self._auth()
        query.update(auth_params)
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self._timeout) as client:
            response = await client.get(endpoint, params=query, headers=headers)
            response.raise_for_status()
            payload = response.json()

        return payload.get("results", [])

    async def trending(self, media_type: str = "all", time_window: str = "week") -> list[dict[str, Any]]:
        if not self._has_auth():
            return self._mock_discover("any", {})

        endpoint = f"/trending/{media_type}/{time_window}"
        params, headers = self._auth()
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self._timeout) as client:
            response = await client.get(endpoint, params=params, headers=headers)
            response.raise_for_status()
            payload = response.json()

        return payload.get("results", [])

    async def get_details(self, media_type: str, tmdb_id: int) -> dict[str, Any]:
        if not self._has_auth():
            return self._mock_details(media_type, tmdb_id)

        endpoint = f"/{'tv' if media_type in {'tv', 'episode'} else 'movie'}/{tmdb_id}"
        params, headers = self._auth()
        params["append_to_response"] = "keywords,credits,external_ids"
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self._timeout) as client:
            response = await client.get(endpoint, params=params, headers=headers)
            response.raise_for_status()
            return response.json()

    async def search(self, query: str, media_type: str = "movie") -> list[dict[str, Any]]:
        if not self._has_auth():
            return []

        endpoint = f"/search/{'tv' if media_type in {'tv', 'episode'} else 'movie'}"
        params, headers = self._auth()
        params.update(
            {
                "query": query,
                "include_adult": "false",
                "page": 1,
            }
        )
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self._timeout) as client:
            response = await client.get(endpoint, params=params, headers=headers)
            response.raise_for_status()
            return response.json().get("results", [])

    def _has_auth(self) -> bool:
        return bool(self.settings.tmdb_api_key or self.settings.tmdb_read_access_token)

    def _auth(self) -> tuple[dict[str, Any], dict[str, str]]:
        if self.settings.tmdb_api_key:
            return {"api_key": self.settings.tmdb_api_key}, {}
        if self.settings.tmdb_read_access_token:
            return {}, {"Authorization": f"Bearer {self.settings.tmdb_read_access_token}"}
        return {}, {}

    def _mock_discover(self, media_type: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        catalog = [item for item in MOCK_CATALOG if media_type in {"any", item["media_type"]}]

        with_genres = self._parse_int_list(params.get("with_genres"))
        without_genres = self._parse_int_list(params.get("without_genres"))
        min_vote = float(params.get("vote_average.gte", 0.0) or 0.0)
        min_count = int(params.get("vote_count.gte", 0) or 0)
        min_runtime = int(params.get("with_runtime.gte", 0) or 0)
        max_runtime = int(params.get("with_runtime.lte", 9999) or 9999)

        filtered: list[dict[str, Any]] = []
        for item in catalog:
            genres = set(item.get("genres", []))
            runtime = int(item.get("runtime", 0) or 0)
            if with_genres and not genres.intersection(with_genres):
                continue
            if without_genres and genres.intersection(without_genres):
                continue
            if float(item.get("vote_average", 0.0) or 0.0) < min_vote:
                continue
            if int(item.get("vote_count", 0) or 0) < min_count:
                continue
            if not (min_runtime <= runtime <= max_runtime):
                continue
            filtered.append(self._mock_to_tmdb_result(item))

        filtered.sort(key=lambda row: float(row.get("vote_average") or 0.0), reverse=True)
        return filtered

    def _mock_details(self, media_type: str, tmdb_id: int) -> dict[str, Any]:
        for item in MOCK_CATALOG:
            if int(item["id"]) == tmdb_id and (media_type in {"any", item["media_type"]} or media_type == "episode"):
                return {
                    "id": item["id"],
                    "title": item["title"],
                    "name": item["title"],
                    "genres": [{"id": gid, "name": gname} for gid, gname in zip(item["genres"], item["genre_names"])],
                    "overview": item["overview"],
                    "vote_average": item["vote_average"],
                    "vote_count": item["vote_count"],
                    "poster_path": item.get("poster_path"),
                    "runtime": item.get("runtime"),
                    "episode_run_time": [item.get("runtime")],
                    "release_date": f"{item['year']}-01-01" if item.get("year") else None,
                    "first_air_date": f"{item['year']}-01-01" if item.get("year") else None,
                    "keywords": {
                        "keywords": [{"name": name} for name in item.get("keywords", [])],
                        "results": [{"name": name} for name in item.get("keywords", [])],
                    },
                    "credits": {
                        "cast": [{"name": name} for name in item.get("cast", [])],
                    },
                    "external_ids": {"imdb_id": item.get("imdb_id")},
                    "imdb_id": item.get("imdb_id"),
                }

        raise ValueError(f"Mock TMDB item not found for {media_type=} {tmdb_id=}")

    @staticmethod
    def _mock_to_tmdb_result(item: dict[str, Any]) -> dict[str, Any]:
        is_movie = item.get("media_type") == "movie"
        date_field = "release_date" if is_movie else "first_air_date"
        title_field = "title" if is_movie else "name"
        return {
            "id": item["id"],
            title_field: item["title"],
            date_field: f"{item['year']}-01-01" if item.get("year") else None,
            "overview": item["overview"],
            "genre_ids": item.get("genres", []),
            "vote_average": item.get("vote_average", 0.0),
            "vote_count": item.get("vote_count", 0),
            "poster_path": item.get("poster_path"),
            "media_type": item.get("media_type"),
        }

    @staticmethod
    def _parse_int_list(raw: Any) -> set[int]:
        if raw is None:
            return set()
        if isinstance(raw, list):
            return {int(v) for v in raw}
        if isinstance(raw, int):
            return {raw}
        if isinstance(raw, str) and raw.strip():
            return {int(chunk) for chunk in raw.split(",") if chunk.strip().isdigit()}
        return set()
