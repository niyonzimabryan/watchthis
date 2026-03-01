from __future__ import annotations

import pytest

from core.orchestrator import WatchThisOrchestrator
from data.models import RecommendationRequest, UserFilters


@pytest.mark.asyncio
async def test_orchestrator_mood_flow_end_to_end():
    orchestrator = WatchThisOrchestrator.build_default()

    response = await orchestrator.recommend(
        RecommendationRequest(
            mood_input="cozy comfort comedy",
            filters=UserFilters(format="any", length="any"),
        )
    )

    assert response.request_id
    assert response.recommendation.title
    assert response.pitch
    assert 0.0 <= response.confidence <= 1.0


@pytest.mark.asyncio
async def test_orchestrator_roulette_end_to_end():
    orchestrator = WatchThisOrchestrator.build_default()

    response = await orchestrator.recommend(
        RecommendationRequest(
            mood_input=None,
            filters=UserFilters(format="any", length="any"),
            is_roulette=True,
        )
    )

    assert response.recommendation.tmdb_id > 0
    assert response.reasoning


@pytest.mark.asyncio
async def test_orchestrator_reroll_avoids_immediate_duplicate():
    orchestrator = WatchThisOrchestrator.build_default()

    first = await orchestrator.recommend(
        RecommendationRequest(
            mood_input="dark psychological thriller",
            session_id="session-a",
            filters=UserFilters(format="movie", length="any"),
        )
    )

    second = await orchestrator.recommend(
        RecommendationRequest(
            mood_input="dark psychological thriller",
            session_id="session-a",
            filters=UserFilters(format="movie", length="any"),
            is_reroll=True,
            reroll_of=first.request_id,
        )
    )

    assert first.recommendation.tmdb_id != second.recommendation.tmdb_id


@pytest.mark.asyncio
async def test_orchestrator_reroll_is_scoped_to_session():
    orchestrator = WatchThisOrchestrator.build_default()

    first = await orchestrator.recommend(
        RecommendationRequest(
            mood_input="dark psychological thriller",
            session_id="session-a",
            filters=UserFilters(format="movie", length="any"),
        )
    )

    second = await orchestrator.recommend(
        RecommendationRequest(
            mood_input="dark psychological thriller",
            session_id="session-b",
            filters=UserFilters(format="movie", length="any"),
            is_reroll=True,
            reroll_of=first.request_id,
        )
    )

    # Different sessions should not inherit each other's exclusion list.
    assert second.recommendation.tmdb_id == first.recommendation.tmdb_id


@pytest.mark.asyncio
async def test_orchestrator_surfaces_no_candidate_error():
    orchestrator = WatchThisOrchestrator.build_default()

    with pytest.raises(ValueError, match="No candidates found"):
        await orchestrator.recommend(
            RecommendationRequest(
                mood_input="anything",
                filters=UserFilters(format="tv", length="epic"),
            )
        )
