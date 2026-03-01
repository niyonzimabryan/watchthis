from __future__ import annotations

import pytest

from clients.anthropic_client import AnthropicClient
from config import get_settings
from core.errors import DependencyUnavailableError
from core.mood_interpreter import MoodInterpreter


@pytest.mark.asyncio
async def test_mood_interpreter_parses_common_mood():
    interpreter = MoodInterpreter(AnthropicClient())
    result = await interpreter.interpret("I want a dark psychological thriller")

    assert 53 in result.genres
    assert "dark" in result.mood_tags
    assert result.min_vote_average >= 6.0


@pytest.mark.asyncio
async def test_mood_interpreter_handles_empty_input():
    interpreter = MoodInterpreter(AnthropicClient())
    result = await interpreter.interpret("")

    assert result.tone == "roulette"
    assert result.genres


@pytest.mark.asyncio
async def test_mood_interpreter_maps_exclusions():
    interpreter = MoodInterpreter(AnthropicClient())
    result = await interpreter.interpret("something dark but not too violent")

    assert 27 in result.exclude_genres
    assert "gore" in result.exclude_keywords


@pytest.mark.asyncio
async def test_mood_interpreter_applies_explicit_constraints():
    interpreter = MoodInterpreter(AnthropicClient())
    result = await interpreter.interpret(
        "I want an English-language comfort movie, no anime, no subtitles, made after 2000"
    )

    assert result.original_language == "en"
    assert 16 in result.exclude_genres
    assert "anime" in result.exclude_keywords
    assert result.year_range is not None
    assert result.year_range[0] >= 2000


@pytest.mark.asyncio
async def test_mood_interpreter_requires_anthropic_when_fallback_disabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("WATCHTHIS_ALLOW_HEURISTIC_FALLBACK", "false")
    get_settings.cache_clear()

    interpreter = MoodInterpreter(AnthropicClient())
    with pytest.raises(DependencyUnavailableError, match="ANTHROPIC_API_KEY"):
        await interpreter.interpret("cozy comfort comedy")


def test_mood_payload_normalizer_handles_partial_year_range():
    payload = {
        "genres": [35],
        "genre_operator": "or",
        "keywords": ["comfort"],
        "mood_tags": ["cozy"],
        "exclude_genres": [],
        "exclude_keywords": [],
        "year_range": [2000, None],
    }

    normalized = AnthropicClient._normalize_mood_payload(payload)
    assert normalized["year_range"] is None


def test_mood_payload_normalizer_handles_valid_year_range():
    payload = {
        "genres": [35],
        "genre_operator": "OR",
        "keywords": ["comfort"],
        "mood_tags": ["cozy"],
        "exclude_genres": [],
        "exclude_keywords": [],
        "year_range": [2023, 2001],
    }

    normalized = AnthropicClient._normalize_mood_payload(payload)
    assert normalized["year_range"] == (2001, 2023)
