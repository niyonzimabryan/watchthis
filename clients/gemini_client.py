from __future__ import annotations

import json
import logging
import re
from typing import Any

from config import Settings, get_settings
from data.models import MoodInterpretation

logger = logging.getLogger("watchthis.gemini")


class GeminiClient:
    """Gemini API client for mood interpretation (Flash-Lite) and search enrichment (Pro)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self.settings.gemini_api_key)
        return self._client

    # ── Mood Interpretation (Gemini 3.1 Flash-Lite) ──

    async def interpret_mood(self, mood_text: str) -> MoodInterpretation:
        """Parse free-text mood into structured search parameters using Flash-Lite."""
        if not self.settings.gemini_api_key:
            raise ValueError("Missing GEMINI_API_KEY")

        client = self._get_client()

        prompt = (
            "Return strict JSON with keys: genres, genre_operator, keywords, mood_tags, "
            "exclude_genres, exclude_keywords, min_vote_average, min_vote_count, year_range, original_language, tone. "
            "Use TMDB genre ids. Keep year_range null unless explicitly requested. "
            f"Mood input: {mood_text}"
        )

        response = client.models.generate_content(
            model=self.settings.gemini_flash_model,
            contents=prompt,
            config={
                "system_instruction": "You convert mood text into recommendation filters. Output only JSON.",
                "temperature": 0,
                "max_output_tokens": 300,
            },
        )

        payload = self._extract_json(response.text or "{}")
        normalized = self._normalize_mood_payload(payload)
        return MoodInterpretation(**normalized)

    # ── Search Enrichment (Gemini 3.1 Pro + Google Search) ──

    async def search_recommendations(
        self,
        mood_text: str | None,
        mood_tags: list[str],
        format_filter: str = "any",
    ) -> list[dict[str, Any]]:
        """Search the web for community-recommended titles matching the mood."""
        if not self.settings.gemini_api_key:
            return []

        client = self._get_client()
        from google.genai import types

        media_type = "movies and TV shows"
        if format_filter == "movie":
            media_type = "movies"
        elif format_filter in ("tv", "episode"):
            media_type = "TV shows"

        mood_desc = mood_text or ", ".join(mood_tags) or "something good"
        tags_str = ", ".join(mood_tags[:6]) if mood_tags else ""

        prompt = (
            f"Find 8-10 highly recommended {media_type} that match this mood: \"{mood_desc}\". "
            f"{'Mood tags: ' + tags_str + '. ' if tags_str else ''}"
            "Search Reddit (r/MovieSuggestions, r/televisionsuggestions), Letterboxd, "
            "and film community discussions for titles people genuinely recommend for this vibe. "
            "Include hidden gems alongside popular picks. "
            "For each title return: title, year, media_type (movie or tv), "
            "why it matches the mood (1 sentence), and any community sentiment you find. "
            "Return strict JSON array."
        )

        try:
            response = client.models.generate_content(
                model=self.settings.gemini_pro_model,
                contents=prompt,
                config={
                    "temperature": 0.3,
                    "max_output_tokens": 1500,
                    "tools": [types.Tool(google_search=types.GoogleSearch())],
                },
            )
            return self._extract_json_array(response.text or "[]")
        except Exception:
            logger.exception("Gemini search_recommendations failed")
            return []

    async def enrich_candidate(
        self,
        title: str,
        year: int | None,
        media_type: str,
    ) -> dict[str, Any]:
        """Search for streaming availability, ratings, and cultural context for a title."""
        if not self.settings.gemini_api_key:
            return {}

        client = self._get_client()
        from google.genai import types

        year_str = f" ({year})" if year else ""
        prompt = (
            f"For the {media_type} \"{title}\"{year_str}: "
            "1. Where can I stream it in the US right now? (List service names and whether it's subscription, rent, or buy) "
            "2. What are the current Rotten Tomatoes score, Metacritic score, and IMDb rating? "
            "3. Any recent buzz — awards, trending status, notable reviews? "
            "Return strict JSON with keys: streaming_sources (array of {{name, type}}), "
            "rt_score (string like '92%'), metacritic (int), imdb_rating (float), buzz (string, 1 sentence)."
        )

        try:
            response = client.models.generate_content(
                model=self.settings.gemini_pro_model,
                contents=prompt,
                config={
                    "temperature": 0,
                    "max_output_tokens": 500,
                    "tools": [types.Tool(google_search=types.GoogleSearch())],
                },
            )
            return self._extract_json(response.text or "{}")
        except Exception:
            logger.exception("Gemini enrich_candidate failed for %s", title)
            return {}

    async def enrich_candidates_batch(
        self,
        candidates: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        """Enrich multiple candidates in a single search call for efficiency."""
        if not self.settings.gemini_api_key or not candidates:
            return {}

        client = self._get_client()
        from google.genai import types

        titles = [f"- {c['title']} ({c.get('year', '?')}, {c.get('media_type', '?')})" for c in candidates[:8]]
        titles_str = "\n".join(titles)

        prompt = (
            f"For each of these titles:\n{titles_str}\n\n"
            "Search for current US streaming availability and latest ratings. "
            "Return strict JSON object where each key is the title and value has: "
            "streaming_sources (array of {{name, type: sub|rent|buy|free}}), "
            "rt_score (string like '92%'), metacritic (int), imdb_rating (float), "
            "buzz (string, 1 sentence of recent cultural context if any)."
        )

        try:
            response = client.models.generate_content(
                model=self.settings.gemini_pro_model,
                contents=prompt,
                config={
                    "temperature": 0,
                    "max_output_tokens": 2000,
                    "tools": [types.Tool(google_search=types.GoogleSearch())],
                },
            )
            return self._extract_json(response.text or "{}")
        except Exception:
            logger.exception("Gemini batch enrichment failed")
            return {}

    # ── Helpers ──

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        text = text.strip()
        if not text:
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return {}

    @staticmethod
    def _extract_json_array(text: str) -> list[dict[str, Any]]:
        text = text.strip()
        if not text:
            return []
        try:
            result = json.loads(text)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass
        match = re.search(r"\[.*\]", text, flags=re.DOTALL)
        if match:
            try:
                result = json.loads(match.group(0))
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass
        return []

    @staticmethod
    def _normalize_mood_payload(payload: dict[str, Any]) -> dict[str, Any]:
        """Same normalization as AnthropicClient — keeps compatibility."""
        normalized = dict(payload)
        operator = str(normalized.get("genre_operator", "OR")).upper()
        normalized["genre_operator"] = "AND" if operator == "AND" else "OR"

        for key in ("genres", "exclude_genres"):
            values = normalized.get(key)
            if not isinstance(values, list):
                normalized[key] = []
                continue
            normalized[key] = [int(v) for v in values if str(v).isdigit()]

        for key in ("keywords", "mood_tags", "exclude_keywords"):
            values = normalized.get(key)
            if not isinstance(values, list):
                normalized[key] = []
                continue
            normalized[key] = [str(v) for v in values if str(v).strip()]

        if "min_vote_average" in normalized:
            try:
                normalized["min_vote_average"] = float(normalized["min_vote_average"])
            except (TypeError, ValueError):
                normalized.pop("min_vote_average", None)

        if "min_vote_count" in normalized:
            try:
                normalized["min_vote_count"] = int(normalized["min_vote_count"])
            except (TypeError, ValueError):
                normalized.pop("min_vote_count", None)

        year_range = normalized.get("year_range")
        if isinstance(year_range, (list, tuple)) and len(year_range) == 2:
            try:
                s, e = int(year_range[0]), int(year_range[1])
                normalized["year_range"] = (min(s, e), max(s, e))
            except (TypeError, ValueError):
                normalized["year_range"] = None
        else:
            normalized["year_range"] = None

        language = normalized.get("original_language")
        normalized["original_language"] = language.strip().lower() if isinstance(language, str) and language.strip() else None

        return normalized
