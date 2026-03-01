from __future__ import annotations

import math
import re
from dataclasses import dataclass

from config import Settings, get_settings
from data.curated_catalog import CuratedCatalog
from data.database import get_recent_selected_titles, get_title_selection_counts, managed_connection
from data.models import Candidate


COUNTRY_WEIGHTS = {
    "US": 1.0,
    "GB": 0.92,
    "KR": 0.80,
    "JP": 0.80,
    "FR": 0.80,
}


@dataclass
class ScoredCandidate:
    candidate: Candidate
    score: float
    rt_score: float | None
    is_exception: bool


class CandidateCurator:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.catalog = CuratedCatalog(self.settings.curated_catalog_path)
        self.allowed_countries = {country.upper() for country in self.settings.allowed_countries}

    def curate(
        self,
        candidates: list[Candidate],
        user_mood: str | None,
        mood_tags: list[str],
        session_id: str | None,
    ) -> list[Candidate]:
        if not candidates:
            return []

        with managed_connection(self.settings.db_path_obj) as conn:
            recent_titles = {self._norm(title) for title in get_recent_selected_titles(conn, session_id, limit=30)}
            global_counts = {self._norm(k): v for k, v in get_title_selection_counts(conn, limit=500).items()}

        scored: list[ScoredCandidate] = []
        scored_fallback: list[ScoredCandidate] = []

        for candidate in candidates:
            rt = self._parse_rt_percent(candidate.rt_score)
            is_exception = self.settings.curated_catalog_enabled and self.catalog.contains(candidate)

            if not self._country_allowed(candidate.primary_country) and not is_exception:
                continue

            in_floor = is_exception or (rt is not None and rt >= self.settings.rt_min_score)

            # For KR/JP/FR, require stronger popularity/quality unless explicitly curated.
            if (
                (candidate.primary_country or "").upper() in {"KR", "JP", "FR"}
                and not is_exception
                and not self._is_high_signal_international(candidate, rt)
            ):
                continue

            score = self._score_candidate(candidate, rt, user_mood, mood_tags, recent_titles, global_counts)
            pack = ScoredCandidate(candidate=candidate, score=score, rt_score=rt, is_exception=is_exception)
            if in_floor:
                scored.append(pack)
            elif self._in_fallback_band(candidate, rt):
                scored_fallback.append(pack)

        scored.sort(key=lambda row: row.score, reverse=True)
        shortlist = self._diversify(scored, self.settings.shortlist_size)

        if len(shortlist) < max(4, self.settings.shortlist_size // 2):
            scored_fallback.sort(key=lambda row: row.score, reverse=True)
            merged = shortlist + [row for row in scored_fallback if row not in shortlist]
            shortlist = self._diversify(merged, self.settings.shortlist_size)

        return [row.candidate for row in shortlist]

    def _score_candidate(
        self,
        candidate: Candidate,
        rt: float | None,
        user_mood: str | None,
        mood_tags: list[str],
        recent_titles: set[str],
        global_counts: dict[str, int],
    ) -> float:
        weighted_rt_proxy = self._weighted_rt_proxy(rt, candidate.imdb_rating)
        rt_component = self._compress_quality_percent(rt) * 1.3
        weighted_component = self._compress_quality_percent(weighted_rt_proxy) * 0.9
        tmdb_component = candidate.vote_average * 5.5
        imdb_component = (candidate.imdb_rating or 0.0) * 4.0
        meta_component = (candidate.metacritic or 0) * 0.22
        popularity_component = math.log10(max(1, candidate.vote_count)) * 2.3 + (candidate.popularity or 0.0) * 0.025
        community_component = candidate.reddit_boost * 4.2
        mood_component = self._mood_alignment(candidate, user_mood, mood_tags)

        score = (
            rt_component
            + weighted_component
            + tmdb_component
            + imdb_component
            + meta_component
            + popularity_component
            + community_component
            + mood_component
        )

        country_weight = COUNTRY_WEIGHTS.get((candidate.primary_country or "").upper(), 0.75)
        score *= country_weight

        norm_title = self._norm(candidate.title)
        if norm_title in recent_titles:
            score -= 30.0

        global_seen = global_counts.get(norm_title, 0)
        score -= min(45.0, global_seen * 2.8)

        if global_seen >= 5 and (rt is None or rt < 93):
            score -= 20.0

        # Tiny bonus to non-obvious but still high-quality options.
        if rt and rt >= 88 and global_seen <= 1:
            score += 1.5

        return score

    def _weighted_rt_proxy(self, rt: float | None, imdb_rating: float | None) -> float:
        if rt is None and imdb_rating is None:
            return 0.0
        if rt is None:
            return (imdb_rating or 0.0) * 10
        if imdb_rating is None:
            return rt
        # RT audience is unavailable from OMDb in most cases; IMDb is used as audience proxy.
        return 0.4 * rt + 0.6 * ((imdb_rating or 0.0) * 10)

    def _mood_alignment(self, candidate: Candidate, user_mood: str | None, mood_tags: list[str]) -> float:
        if not user_mood and not mood_tags:
            return 0.0

        tokens = set(self._tokenize(user_mood or ""))
        tokens.update(self._tokenize(" ".join(mood_tags)))

        candidate_text = " ".join(
            [
                candidate.title,
                candidate.overview,
                " ".join(candidate.keywords),
                " ".join(candidate.genres),
            ]
        ).lower()

        hits = sum(1 for token in tokens if token and token in candidate_text)
        return min(20.0, hits * 2.4)

    def _country_allowed(self, primary_country: str | None) -> bool:
        if not self.allowed_countries:
            return True
        if primary_country is None:
            return True
        return primary_country.upper() in self.allowed_countries

    @staticmethod
    def _is_high_signal_international(candidate: Candidate, rt: float | None) -> bool:
        return (rt is not None and rt >= 82.0 and candidate.vote_count >= 1000) or (
            (candidate.imdb_rating or 0) >= 7.8 and candidate.vote_count >= 2000
        )

    def _in_fallback_band(self, candidate: Candidate, rt: float | None) -> bool:
        if rt is not None and rt >= self.settings.rt_fallback_score:
            return True
        if rt is None and candidate.vote_average >= 8.0 and candidate.vote_count >= 4000:
            return True
        return False

    def _diversify(self, scored: list[ScoredCandidate], size: int) -> list[ScoredCandidate]:
        if not scored:
            return []

        selected: list[ScoredCandidate] = []
        country_counts: dict[str, int] = {}
        decade_counts: dict[int, int] = {}

        max_us = max(1, math.ceil(size * 0.65))
        max_gb = max(1, math.ceil(size * 0.30))
        max_other = max(1, math.ceil(size * 0.25))
        max_decade = max(2, math.ceil(size * 0.35))

        for row in scored:
            if len(selected) >= size:
                break

            country = (row.candidate.primary_country or "").upper()
            decade = (row.candidate.year // 10) * 10 if row.candidate.year else None

            country_cap = max_other
            if country == "US":
                country_cap = max_us
            elif country == "GB":
                country_cap = max_gb

            if country and country_counts.get(country, 0) >= country_cap:
                continue
            if decade is not None and decade_counts.get(decade, 0) >= max_decade:
                continue

            selected.append(row)
            if country:
                country_counts[country] = country_counts.get(country, 0) + 1
            if decade is not None:
                decade_counts[decade] = decade_counts.get(decade, 0) + 1

        if len(selected) < size:
            seen_ids = {row.candidate.tmdb_id for row in selected}
            for row in scored:
                if len(selected) >= size:
                    break
                if row.candidate.tmdb_id in seen_ids:
                    continue
                selected.append(row)
                seen_ids.add(row.candidate.tmdb_id)

        return selected

    @staticmethod
    def _parse_rt_percent(value: str | None) -> float | None:
        if not value:
            return None
        match = re.search(r"(\d{1,3})", value)
        if not match:
            return None
        try:
            parsed = float(match.group(1))
        except ValueError:
            return None
        return max(0.0, min(100.0, parsed))

    @staticmethod
    def _compress_quality_percent(value: float | None) -> float:
        if value is None:
            return 0.0
        if value <= 80:
            return value
        return 80 + ((value - 80) * 0.35)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [token for token in re.split(r"[^a-z0-9]+", text.lower()) if len(token) >= 3]

    @staticmethod
    def _norm(value: str) -> str:
        return " ".join(value.lower().split())
