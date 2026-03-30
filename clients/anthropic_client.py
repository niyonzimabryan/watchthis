from __future__ import annotations

import json
import math
import random
import re
from typing import Any

from config import Settings, get_settings
from core.constants import DEFAULT_ROULETTE_GENRES, KEYWORD_HINTS
from core.errors import DependencyUnavailableError
from data.models import Candidate, MoodInterpretation, RankedRecommendation, UserFilters


class AnthropicClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def interpret_mood(self, mood_text: str) -> MoodInterpretation:
        if not mood_text.strip():
            return self.roulette_defaults()

        if not self.settings.anthropic_api_key:
            if self.settings.allow_heuristic_fallback:
                return self._heuristic_interpretation(mood_text)
            raise DependencyUnavailableError("Missing ANTHROPIC_API_KEY. Recommendations are unavailable.")

        try:
            return await self._api_interpret_mood(mood_text)
        except Exception as exc:
            if self.settings.allow_heuristic_fallback:
                return self._heuristic_interpretation(mood_text)
            raise DependencyUnavailableError(f"Anthropic mood interpretation failed: {exc}") from exc

    async def rank_candidates(
        self,
        user_mood: str | None,
        filters: UserFilters,
        candidates: list[Candidate],
        is_roulette: bool,
    ) -> RankedRecommendation:
        if not candidates:
            raise ValueError("No candidates available for ranking")

        if not self.settings.anthropic_api_key:
            if self.settings.allow_heuristic_fallback:
                return self._heuristic_rank(user_mood, candidates, is_roulette=is_roulette)
            raise DependencyUnavailableError("Missing ANTHROPIC_API_KEY. Recommendations are unavailable.")

        try:
            return await self._api_rank(user_mood, filters, candidates, is_roulette)
        except Exception as exc:
            if self.settings.allow_heuristic_fallback:
                return self._heuristic_rank(user_mood, candidates, is_roulette=is_roulette)
            raise DependencyUnavailableError(f"Anthropic ranking failed: {exc}") from exc

    def roulette_defaults(self) -> MoodInterpretation:
        return self._heuristic_roulette_interpretation()

    async def _api_interpret_mood(self, mood_text: str) -> MoodInterpretation:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        prompt = (
            "Return strict JSON with keys: genres, genre_operator, keywords, mood_tags, "
            "exclude_genres, exclude_keywords, min_vote_average, min_vote_count, year_range, original_language, tone. "
            "Use TMDB genre ids. Keep year_range null unless explicitly requested. "
            f"Mood input: {mood_text}"
        )
        message = await client.messages.create(
            model=self.settings.haiku_model,
            max_tokens=300,
            temperature=0,
            system="You convert mood text into recommendation filters. Output only JSON.",
            messages=[{"role": "user", "content": prompt}],
        )
        text = self._extract_text(message)
        payload = self._extract_json(text)
        normalized = self._normalize_mood_payload(payload)
        return MoodInterpretation(**normalized)

    async def _api_rank(
        self,
        user_mood: str | None,
        filters: UserFilters,
        candidates: list[Candidate],
        is_roulette: bool,
    ) -> RankedRecommendation:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        trimmed = [candidate.model_dump() for candidate in candidates[:10]]
        prompt_payload = {
            "user_mood": user_mood,
            "user_filters": filters.model_dump(),
            "is_roulette": is_roulette,
            "candidates": trimmed,
        }

        model_name = self.settings.opus_model
        prompt = (
            "Pick exactly one candidate and return strict JSON with keys selected_tmdb_id, pitch, confidence, reasoning. "
            "Pitch must be 2-4 sentences, spoiler-free, and read like a sharp personal recommendation from a friend with great taste. "
            "Reasoning should briefly explain the strongest mood match and quality signals. "
            "CRITICAL: You MUST respect the user's format and length filters. "
            "If format is 'movie', only pick movies. If format is 'tv', only pick TV shows. "
            "If length is 'quick', pick something short (movies under 95min, TV episodes under 35min). "
            "If length is 'long', pick something long (movies over 100min, prestige TV over 50min). "
            "Optimize for this order: filter compliance, mood fit, quality/acclaim, subtle surprise, then familiarity as a tiebreaker. "
            "Avoid obvious repeats unless they are clearly the best fit."
            f"\nInput: {json.dumps(prompt_payload, ensure_ascii=True)}"
        )
        message = await client.messages.create(
            model=model_name,
            max_tokens=520,
            temperature=0.35,
            system="You are an expert entertainment curator. Output only JSON.",
            messages=[{"role": "user", "content": prompt}],
        )
        text = self._extract_text(message)
        payload = self._extract_json(text)
        normalized = self._normalize_rank_payload(payload, candidates, user_mood=user_mood, is_roulette=is_roulette)
        return RankedRecommendation(**normalized)

    def _heuristic_interpretation(self, mood_text: str) -> MoodInterpretation:
        text = mood_text.lower()
        genres: set[int] = set()
        exclude_genres: set[int] = set()
        keywords: set[str] = set()
        exclude_keywords: set[str] = set()
        mood_tags: set[str] = set()

        for hint, (words, hint_genres, banned_words, banned_genres) in KEYWORD_HINTS.items():
            if hint in text:
                keywords.update(words)
                mood_tags.add(hint)
                genres.update(hint_genres)
                exclude_keywords.update(banned_words)
                exclude_genres.update(banned_genres)

        if not genres:
            genres.update([35, 18])
            mood_tags.add("balanced")
            keywords.update(["well-rated", "engaging"])

        tone = "-".join(sorted(mood_tags))[:60] if mood_tags else "balanced"
        return MoodInterpretation(
            genres=sorted(genres),
            genre_operator="OR",
            keywords=sorted(keywords),
            mood_tags=sorted(mood_tags),
            exclude_genres=sorted(exclude_genres),
            exclude_keywords=sorted(exclude_keywords),
            tone=tone,
        )

    def _heuristic_roulette_interpretation(self) -> MoodInterpretation:
        chosen = random.choice(DEFAULT_ROULETTE_GENRES)
        return MoodInterpretation(
            genres=[chosen],
            genre_operator="OR",
            keywords=["trending", "popular"],
            mood_tags=["roulette"],
            min_vote_average=6.8,
            min_vote_count=300,
            tone="roulette",
        )

    def _heuristic_rank(
        self,
        user_mood: str | None,
        candidates: list[Candidate],
        is_roulette: bool,
    ) -> RankedRecommendation:
        lowered = (user_mood or "").lower()

        def score(candidate: Candidate) -> float:
            keyword_hits = sum(1 for kw in candidate.keywords if kw.lower() in lowered) if lowered else 0
            mood_hits = sum(1 for tag in candidate.reddit_mood_match if tag.lower() in lowered) if lowered else 0
            quality_vote = candidate.vote_average * 11
            quality_imdb = (candidate.imdb_rating or 0.0) * 1.8
            quality_meta = (candidate.metacritic or 0) / 6
            quality_rt = self._parse_percent(candidate.rt_score) / 10
            taste_signal = candidate.reddit_boost * 9 + keyword_hits * 7 + mood_hits * 6
            popularity = math.log10(max(1, candidate.vote_count))
            runtime_bonus = 0.8 if candidate.runtime and 20 <= candidate.runtime <= 180 else 0.0
            return (
                quality_vote
                + quality_imdb
                + quality_meta
                + quality_rt
                + taste_signal
                + popularity
                + runtime_bonus
            )

        selected = max(candidates, key=score)
        confidence = min(0.97, max(0.55, score(selected) / 140))

        if is_roulette:
            pitch = (
                f"{selected.title} is trending and strongly rated, with the right mix of momentum and payoff. "
                "If you want zero analysis and a confident pick, start this one now."
            )
            reasoning = "High aggregate quality signals and broad audience momentum"
        else:
            mood = (user_mood or "your current vibe").strip()
            pitch = (
                f"Based on '{mood}', {selected.title} fits because it matches the tone without overcomplicating your night. "
                "It is a high-confidence choice with strong audience consensus."
            )
            reasoning = "Best blend of ratings, mood keyword overlap, and community signal"

        return RankedRecommendation(
            selected_tmdb_id=selected.tmdb_id,
            pitch=pitch,
            confidence=round(confidence, 2),
            reasoning=reasoning,
        )

    @staticmethod
    def _parse_percent(value: str | None) -> float:
        if not value:
            return 0.0
        stripped = value.strip().replace("%", "")
        try:
            return float(stripped)
        except ValueError:
            return 0.0

    @staticmethod
    def _extract_text(message: Any) -> str:
        content = getattr(message, "content", [])
        if not content:
            return "{}"

        fragments: list[str] = []
        for block in content:
            text = getattr(block, "text", None)
            if text:
                fragments.append(text)
        return "\n".join(fragments) if fragments else "{}"

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
        if not match:
            return {}

        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _normalize_mood_payload(payload: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(payload)
        operator = str(normalized.get("genre_operator", "OR")).upper()
        normalized["genre_operator"] = "AND" if operator == "AND" else "OR"

        for key in ("genres", "exclude_genres"):
            values = normalized.get(key)
            if not isinstance(values, list):
                normalized[key] = []
                continue
            casted: list[int] = []
            for value in values:
                try:
                    casted.append(int(value))
                except (TypeError, ValueError):
                    continue
            normalized[key] = casted

        for key in ("keywords", "mood_tags", "exclude_keywords"):
            values = normalized.get(key)
            if not isinstance(values, list):
                normalized[key] = []
                continue
            normalized[key] = [str(value) for value in values if str(value).strip()]

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
        normalized["year_range"] = AnthropicClient._normalize_year_range(year_range)

        language = normalized.get("original_language")
        if isinstance(language, str) and language.strip():
            normalized["original_language"] = language.strip().lower()
        else:
            normalized["original_language"] = None

        return normalized

    @staticmethod
    def _normalize_year_range(value: Any) -> tuple[int, int] | None:
        if value is None:
            return None

        start = None
        end = None

        if isinstance(value, (list, tuple)) and len(value) == 2:
            start, end = value
        elif isinstance(value, dict):
            start = value.get("start")
            end = value.get("end")
        else:
            return None

        try:
            start_i = int(start)
            end_i = int(end)
        except (TypeError, ValueError):
            return None

        if start_i > end_i:
            start_i, end_i = end_i, start_i

        return (start_i, end_i)

    @staticmethod
    def _normalize_rank_payload(
        payload: dict[str, Any],
        candidates: list[Candidate],
        user_mood: str | None,
        is_roulette: bool,
    ) -> dict[str, Any]:
        if not candidates:
            raise ValueError("Cannot normalize rank payload without candidates")

        valid_ids = {candidate.tmdb_id for candidate in candidates}
        default_candidate = max(candidates, key=lambda row: (row.vote_average, row.vote_count))

        selected_tmdb_id = payload.get("selected_tmdb_id")
        try:
            selected_tmdb_id = int(selected_tmdb_id)
        except (TypeError, ValueError):
            selected_tmdb_id = default_candidate.tmdb_id
        if selected_tmdb_id not in valid_ids:
            selected_tmdb_id = default_candidate.tmdb_id

        pitch = payload.get("pitch")
        if not isinstance(pitch, str) or not pitch.strip():
            mood = (user_mood or "your vibe").strip()
            if is_roulette:
                pitch = (
                    f"{default_candidate.title} is a strong roulette pick with reliable quality signals. "
                    "Start here if you want a confident one-click choice."
                )
            else:
                pitch = (
                    f"{default_candidate.title} is a fit for '{mood}' with strong quality signals and an accessible tone. "
                    "It is a confident recommendation for tonight."
                )
        pitch = pitch.strip()

        confidence = payload.get("confidence")
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.75
        confidence = max(0.0, min(1.0, confidence))

        reasoning = payload.get("reasoning")
        if not isinstance(reasoning, str) or not reasoning.strip():
            reasoning = "Selected from candidate set using taste fit and quality signals."
        reasoning = reasoning.strip()

        return {
            "selected_tmdb_id": selected_tmdb_id,
            "pitch": pitch,
            "confidence": confidence,
            "reasoning": reasoning,
        }
