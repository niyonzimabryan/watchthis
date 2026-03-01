from __future__ import annotations

from clients.anthropic_client import AnthropicClient
from data.models import Candidate, RankedRecommendation, UserFilters


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
        ranked = await self.anthropic_client.rank_candidates(user_mood, filters, candidates, is_roulette)

        selected = next((row for row in candidates if row.tmdb_id == ranked.selected_tmdb_id), None)
        if selected is None:
            selected = candidates[0]
            ranked = RankedRecommendation(
                selected_tmdb_id=selected.tmdb_id,
                pitch=ranked.pitch,
                confidence=ranked.confidence,
                reasoning=ranked.reasoning,
            )

        return selected, ranked
