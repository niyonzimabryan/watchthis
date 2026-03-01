from __future__ import annotations

import re

from clients.anthropic_client import AnthropicClient
from data.models import MoodInterpretation


class MoodInterpreter:
    def __init__(self, anthropic_client: AnthropicClient) -> None:
        self.anthropic_client = anthropic_client

    async def interpret(self, mood_input: str | None, is_roulette: bool = False) -> MoodInterpretation:
        if is_roulette:
            return self.anthropic_client.roulette_defaults()

        if not mood_input or not mood_input.strip():
            # Empty moods degrade to roulette-like behavior to keep UX decisive.
            return self.anthropic_client.roulette_defaults()

        interpreted = await self.anthropic_client.interpret_mood(mood_input)
        return self._apply_explicit_constraints(mood_input, interpreted)

    @staticmethod
    def _apply_explicit_constraints(mood_input: str, interpreted: MoodInterpretation) -> MoodInterpretation:
        text = mood_input.lower()

        if any(token in text for token in ("english", "english-language", "english language", "no subtitles", "no subtitle")):
            interpreted.original_language = "en"

        if any(token in text for token in ("no anime", "not anime", "without anime", "no animation", "not animation")):
            if 16 not in interpreted.exclude_genres:
                interpreted.exclude_genres.append(16)
            if "anime" not in interpreted.exclude_keywords:
                interpreted.exclude_keywords.append("anime")

        range_match = re.search(r"(?:after|since|from)\s+(19\d{2}|20\d{2})", text)
        if range_match:
            start_year = int(range_match.group(1))
            if interpreted.year_range is None:
                interpreted.year_range = (start_year, 2100)
            else:
                interpreted.year_range = (max(start_year, interpreted.year_range[0]), interpreted.year_range[1])

        before_match = re.search(r"(?:before|earlier than|older than)\s+(19\d{2}|20\d{2})", text)
        if before_match:
            end_year = int(before_match.group(1))
            if interpreted.year_range is None:
                interpreted.year_range = (1900, end_year)
            else:
                interpreted.year_range = (interpreted.year_range[0], min(end_year, interpreted.year_range[1]))

        if interpreted.year_range is not None and interpreted.year_range[0] > interpreted.year_range[1]:
            interpreted.year_range = (interpreted.year_range[1], interpreted.year_range[0])

        interpreted.exclude_genres = sorted(set(interpreted.exclude_genres))
        interpreted.exclude_keywords = sorted(set(interpreted.exclude_keywords))
        return interpreted
