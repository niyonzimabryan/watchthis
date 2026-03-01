from __future__ import annotations

import pytest

from clients.tmdb_client import TMDBClient
from core.candidate_retrieval import CandidateRetriever
from data.models import LengthFilter, MoodInterpretation, UserFilters


@pytest.mark.asyncio
async def test_candidate_retrieval_quick_applies_runtime_bounds():
    retriever = CandidateRetriever(TMDBClient())
    interpretation = MoodInterpretation(genres=[35], mood_tags=["funny"])
    filters = UserFilters(format="any", length=LengthFilter.QUICK)

    candidates = await retriever.retrieve(interpretation, filters)

    assert candidates
    for candidate in candidates:
        if candidate.media_type == "movie":
            assert 60 <= (candidate.runtime or 0) <= 95
        else:
            assert (candidate.runtime or 0) <= 30


@pytest.mark.asyncio
async def test_candidate_retrieval_epic_prefers_movies():
    retriever = CandidateRetriever(TMDBClient())
    interpretation = MoodInterpretation(genres=[18], mood_tags=["slow"])
    filters = UserFilters(format="any", length=LengthFilter.EPIC)

    candidates = await retriever.retrieve(interpretation, filters)

    assert candidates
    assert all(candidate.media_type == "movie" for candidate in candidates)
    assert all((candidate.runtime or 0) >= 120 for candidate in candidates)


@pytest.mark.asyncio
async def test_candidate_retrieval_respects_exclusions():
    retriever = CandidateRetriever(TMDBClient())
    interpretation = MoodInterpretation(genres=[35], mood_tags=["comfort"])
    filters = UserFilters()

    initial = await retriever.retrieve(interpretation, filters)
    excluded = [initial[0].tmdb_id]

    rerolled = await retriever.retrieve(interpretation, filters, excluded_tmdb_ids=excluded)

    assert rerolled
    assert all(candidate.tmdb_id not in excluded for candidate in rerolled)


@pytest.mark.asyncio
async def test_candidate_retrieval_applies_year_cutoff():
    retriever = CandidateRetriever(TMDBClient())
    interpretation = MoodInterpretation(genres=[18], mood_tags=["drama"], year_range=(1900, 1950))
    filters = UserFilters(format="movie", length=LengthFilter.ANY)

    candidates = await retriever.retrieve(interpretation, filters)

    assert candidates == []


@pytest.mark.asyncio
async def test_candidate_retrieval_includes_poster_url():
    retriever = CandidateRetriever(TMDBClient())
    interpretation = MoodInterpretation(genres=[35], mood_tags=["comfort"])
    filters = UserFilters()

    candidates = await retriever.retrieve(interpretation, filters)

    assert candidates
    assert candidates[0].poster_url
    assert candidates[0].poster_url.startswith("https://image.tmdb.org/t/p/w780/")
