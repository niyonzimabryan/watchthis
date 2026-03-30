from __future__ import annotations

from clients.anthropic_client import AnthropicClient
from data.models import Candidate, FormatFilter, LengthFilter, RankedRecommendation, UserFilters

# Runtime bounds for hard enforcement (mirrors candidate_retrieval.py)
_MOVIE_RUNTIME = {
    LengthFilter.QUICK: (0, 95),
    LengthFilter.STANDARD: (60, 140),
    LengthFilter.LONG: (100, 200),
    LengthFilter.EPIC: (140, 500),
}
_TV_RUNTIME = {
    LengthFilter.QUICK: (0, 35),
    LengthFilter.STANDARD: (20, 65),
    LengthFilter.LONG: (50, 120),
    LengthFilter.EPIC: (90, 500),
}


def _runtime_ok(candidate: Candidate, filters: UserFilters) -> bool:
    """Hard check: does this candidate's runtime fit the user's length filter?"""
    if filters.length == LengthFilter.ANY:
        return True
    if candidate.runtime is None:
        return True  # Can't filter what we don't know

    bounds = _MOVIE_RUNTIME if candidate.media_type == "movie" else _TV_RUNTIME
    rng = bounds.get(filters.length)
    if rng is None:
        return True
    return rng[0] <= candidate.runtime <= rng[1]


def _format_ok(candidate: Candidate, filters: UserFilters) -> bool:
    """Hard check: does this candidate's format match the user's filter?"""
    if filters.format == FormatFilter.ANY:
        return True
    if filters.format == FormatFilter.MOVIE:
        return candidate.media_type == "movie"
    if filters.format in (FormatFilter.TV, FormatFilter.EPISODE):
        return candidate.media_type == "tv"
    return True


class Ranker:
    def __init__(self, anthropic_client: AnthropicClient) -> None:
        self.anthropic_client = anthropic_client

    async def rank(
        self,
        user_mood: str | None,
        filters: UserFilters,
        candidates: list[Candidate],
        is_roulette: bool,
    ) -> tuple[Candidate, RankedRecommendation]:
        # Pre-filter candidates to only those matching format + length
        valid = [c for c in candidates if _format_ok(c, filters) and _runtime_ok(c, filters)]
        if not valid:
            valid = candidates  # Fallback: don't return nothing

        ranked = await self.anthropic_client.rank_candidates(user_mood, filters, valid, is_roulette)

        selected = next((row for row in valid if row.tmdb_id == ranked.selected_tmdb_id), None)
        if selected is None:
            selected = valid[0]
            ranked = RankedRecommendation(
                selected_tmdb_id=selected.tmdb_id,
                pitch=ranked.pitch,
                confidence=ranked.confidence,
                reasoning=ranked.reasoning,
            )

        return selected, ranked
