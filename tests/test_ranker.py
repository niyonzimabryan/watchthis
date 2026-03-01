from __future__ import annotations

import pytest

from clients.anthropic_client import AnthropicClient
from core.ranker import Ranker
from data.models import Candidate, UserFilters


@pytest.mark.asyncio
async def test_ranker_handles_single_candidate():
    ranker = Ranker(AnthropicClient())
    only = Candidate(tmdb_id=1, media_type="movie", title="Only One", vote_average=7.0)

    selected, ranked = await ranker.rank(
        user_mood="cozy",
        filters=UserFilters(),
        candidates=[only],
        is_roulette=False,
    )

    assert selected.tmdb_id == 1
    assert ranked.selected_tmdb_id == 1


@pytest.mark.asyncio
async def test_ranker_pitch_is_four_sentences_or_less():
    ranker = Ranker(AnthropicClient())
    candidates = [
        Candidate(tmdb_id=1, media_type="movie", title="A", vote_average=7.0),
        Candidate(tmdb_id=2, media_type="movie", title="B", vote_average=8.2),
    ]

    _, ranked = await ranker.rank(
        user_mood="dark and twisty",
        filters=UserFilters(),
        candidates=candidates,
        is_roulette=False,
    )

    sentences = [chunk for chunk in ranked.pitch.split(".") if chunk.strip()]
    assert len(sentences) <= 4


def test_rank_payload_normalizer_handles_missing_selected_id():
    candidates = [
        Candidate(tmdb_id=100, media_type="movie", title="One", vote_average=7.0, vote_count=1000),
        Candidate(tmdb_id=200, media_type="movie", title="Two", vote_average=8.5, vote_count=5000),
    ]
    payload = {"selected_tmdb_id": None, "pitch": " ", "confidence": None, "reasoning": ""}

    normalized = AnthropicClient._normalize_rank_payload(
        payload,
        candidates,
        user_mood="cozy",
        is_roulette=False,
    )

    assert normalized["selected_tmdb_id"] == 200
    assert isinstance(normalized["pitch"], str) and normalized["pitch"]
    assert 0.0 <= normalized["confidence"] <= 1.0
    assert isinstance(normalized["reasoning"], str) and normalized["reasoning"]


def test_rank_payload_normalizer_rejects_unknown_selected_id():
    candidates = [
        Candidate(tmdb_id=100, media_type="movie", title="One", vote_average=7.0, vote_count=1000),
        Candidate(tmdb_id=200, media_type="movie", title="Two", vote_average=8.5, vote_count=5000),
    ]
    payload = {"selected_tmdb_id": 999, "pitch": "ok", "confidence": 0.5, "reasoning": "ok"}

    normalized = AnthropicClient._normalize_rank_payload(
        payload,
        candidates,
        user_mood=None,
        is_roulette=True,
    )

    assert normalized["selected_tmdb_id"] == 200
