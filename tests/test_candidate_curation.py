from __future__ import annotations

from pathlib import Path

from config import get_settings
from core.candidate_curation import CandidateCurator
from data.database import insert_request_log, managed_connection
from data.models import Candidate


def _candidate(
    tmdb_id: int,
    title: str,
    rt_score: str,
    country: str | None = "US",
    vote_average: float = 8.0,
    vote_count: int = 5000,
) -> Candidate:
    return Candidate(
        tmdb_id=tmdb_id,
        media_type="movie",
        title=title,
        year=2015,
        primary_country=country,
        original_language="en",
        genres=["Comedy"],
        overview=f"{title} overview",
        vote_average=vote_average,
        vote_count=vote_count,
        keywords=["feel-good", "comfort"],
        rt_score=rt_score,
        imdb_rating=7.8,
        metacritic=72,
    )


def test_curation_prefers_rt_floor_candidates(monkeypatch):
    monkeypatch.setenv("WATCHTHIS_SHORTLIST_SIZE", "4")
    monkeypatch.setenv("WATCHTHIS_RT_MIN_SCORE", "75")
    monkeypatch.setenv("WATCHTHIS_RT_FALLBACK_SCORE", "70")
    get_settings.cache_clear()

    curator = CandidateCurator(get_settings())
    candidates = [
        _candidate(1, "Strong One", "91%"),
        _candidate(2, "Strong Two", "88%"),
        _candidate(3, "Strong Three", "85%"),
        _candidate(4, "Strong Four", "83%"),
        _candidate(5, "Weak Link", "72%"),
    ]

    curated = curator.curate(candidates, user_mood="cozy and funny", mood_tags=["cozy"], session_id="s1")
    titles = {row.title for row in curated}

    assert "Weak Link" not in titles
    assert len(curated) == 4


def test_curation_allows_curated_exception(monkeypatch, tmp_path: Path):
    curated_file = tmp_path / "curated.md"
    curated_file.write_text(
        "\n".join(
            [
                "| title | media_type | year |",
                "|---|---|---|",
                "| Exception Pick | movie | 2015 |",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("WATCHTHIS_SHORTLIST_SIZE", "2")
    monkeypatch.setenv("WATCHTHIS_RT_MIN_SCORE", "75")
    monkeypatch.setenv("WATCHTHIS_CURATED_CATALOG_PATH", str(curated_file))
    monkeypatch.setenv("WATCHTHIS_CURATED_CATALOG_ENABLED", "true")
    get_settings.cache_clear()

    curator = CandidateCurator(get_settings())
    candidates = [
        _candidate(10, "Top Rated", "90%"),
        _candidate(11, "Exception Pick", "40%"),
    ]

    curated = curator.curate(candidates, user_mood="fun", mood_tags=[], session_id="s1")
    titles = {row.title for row in curated}

    assert "Top Rated" in titles
    assert "Exception Pick" in titles


def test_curation_filters_disallowed_country(monkeypatch):
    monkeypatch.setenv("WATCHTHIS_SHORTLIST_SIZE", "4")
    monkeypatch.setenv("WATCHTHIS_ALLOWED_COUNTRIES", "US,GB,KR,JP,FR")
    get_settings.cache_clear()

    curator = CandidateCurator(get_settings())
    candidates = [
        _candidate(21, "US Title", "92%", country="US"),
        _candidate(22, "German Title", "95%", country="DE"),
    ]

    curated = curator.curate(candidates, user_mood="feel good", mood_tags=[], session_id="s1")
    titles = {row.title for row in curated}

    assert "US Title" in titles
    assert "German Title" not in titles


def test_curation_penalizes_recent_repeats(monkeypatch):
    monkeypatch.setenv("WATCHTHIS_SHORTLIST_SIZE", "1")
    get_settings.cache_clear()
    settings = get_settings()

    with managed_connection(settings.db_path_obj) as conn:
        insert_request_log(
            conn,
            {
                "id": "req-1",
                "session_id": "repeat-session",
                "mood_input": "cozy",
                "format_filter": "any",
                "length_filter": "any",
                "mood_interpretation": {},
                "candidates_count": 10,
                "selected_tmdb_id": 31,
                "selected_title": "Repeat Pick",
                "pitch": "p",
                "confidence": 0.8,
                "reasoning": "r",
                "latency_ms": 10,
                "latency_mood_ms": 1,
                "latency_tmdb_ms": 1,
                "latency_enrichment_ms": 1,
                "latency_ranking_ms": 1,
                "latency_streaming_ms": 1,
                "is_roulette": False,
                "is_reroll": False,
                "reroll_of": None,
                "error": None,
            },
        )

    curator = CandidateCurator(settings)
    candidates = [
        _candidate(31, "Repeat Pick", "94%", vote_average=8.8),
        _candidate(32, "Fresh Pick", "88%", vote_average=8.7),
    ]

    curated = curator.curate(candidates, user_mood="cozy", mood_tags=["cozy"], session_id="repeat-session")

    assert curated[0].title == "Fresh Pick"


def test_curation_allows_unknown_country(monkeypatch):
    monkeypatch.setenv("WATCHTHIS_SHORTLIST_SIZE", "2")
    get_settings.cache_clear()

    curator = CandidateCurator(get_settings())
    candidates = [_candidate(41, "No Country", "86%", country=None)]

    curated = curator.curate(candidates, user_mood="chill", mood_tags=[], session_id="s1")

    assert len(curated) == 1
    assert curated[0].title == "No Country"
