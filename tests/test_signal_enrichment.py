from __future__ import annotations

import json

import pytest

from clients.omdb_client import OMDbClient
from core.signal_enrichment import SignalEnricher
from data.database import managed_connection
from data.models import Candidate


@pytest.mark.asyncio
async def test_signal_enrichment_applies_reddit_boost_cap():
    with managed_connection() as conn:
        for _ in range(4):
            conn.execute(
                """
                INSERT INTO reddit_recommendations (
                    source_title,
                    recommended_title,
                    recommended_tmdb_id,
                    mood_tags,
                    subreddit,
                    post_score,
                    comment_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "source",
                    "Inception",
                    27205,
                    json.dumps(["dark", "mind-bending"]),
                    "MovieSuggestions",
                    200,
                    50,
                ),
            )

    enricher = SignalEnricher(OMDbClient())
    candidate = Candidate(
        tmdb_id=27205,
        media_type="movie",
        title="Inception",
        vote_average=8.3,
        imdb_id="tt1375666",
    )

    enriched = await enricher.enrich([candidate], mood_tags=["dark", "mind-bending"])

    assert enriched[0].reddit_boost == 3.0
    assert "dark" in enriched[0].reddit_mood_match


@pytest.mark.asyncio
async def test_signal_enrichment_handles_missing_omdb():
    enricher = SignalEnricher(OMDbClient())
    candidate = Candidate(
        tmdb_id=13,
        media_type="movie",
        title="Forrest Gump",
        vote_average=8.5,
        imdb_id=None,
    )

    enriched = await enricher.enrich([candidate], mood_tags=[])

    assert enriched[0].rt_score is None
    assert enriched[0].imdb_rating is None
