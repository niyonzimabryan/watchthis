from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class FormatFilter(StrEnum):
    MOVIE = "movie"
    TV = "tv"
    EPISODE = "episode"
    ANY = "any"


class LengthFilter(StrEnum):
    QUICK = "quick"
    STANDARD = "standard"
    LONG = "long"
    EPIC = "epic"
    ANY = "any"


class GenreOperator(StrEnum):
    AND = "AND"
    OR = "OR"


class UserFilters(BaseModel):
    format: FormatFilter = FormatFilter.ANY
    length: LengthFilter = LengthFilter.ANY


class MoodInterpretation(BaseModel):
    genres: list[int] = Field(default_factory=list)
    genre_operator: GenreOperator = GenreOperator.OR
    keywords: list[str] = Field(default_factory=list)
    mood_tags: list[str] = Field(default_factory=list)
    exclude_genres: list[int] = Field(default_factory=list)
    exclude_keywords: list[str] = Field(default_factory=list)
    min_vote_average: float = 6.5
    min_vote_count: int = 100
    year_range: tuple[int, int] | None = None
    original_language: str | None = None
    tone: str = "balanced"

    @field_validator("min_vote_average")
    @classmethod
    def normalize_vote_average(cls, value: float) -> float:
        return max(0.0, min(10.0, value))


class StreamingSource(BaseModel):
    source_id: str | None = None
    name: str
    type: str = "sub"
    web_url: str | None = None
    format: str | None = None


class Candidate(BaseModel):
    tmdb_id: int
    media_type: str
    title: str
    year: int | None = None
    poster_url: str | None = None
    primary_country: str | None = None
    original_language: str | None = None
    genres: list[str] = Field(default_factory=list)
    overview: str = ""
    vote_average: float = 0.0
    vote_count: int = 0
    popularity: float | None = None
    runtime: int | None = None
    keywords: list[str] = Field(default_factory=list)
    top_cast: list[str] = Field(default_factory=list)
    imdb_id: str | None = None

    rt_score: str | None = None
    metacritic: int | None = None
    imdb_rating: float | None = None

    reddit_boost: float = 1.0
    reddit_mood_match: list[str] = Field(default_factory=list)

    raw: dict[str, Any] = Field(default_factory=dict, exclude=True)


class RecommendationRequest(BaseModel):
    mood_input: str | None = None
    session_id: str | None = None
    filters: UserFilters = Field(default_factory=UserFilters)
    is_roulette: bool = False
    is_reroll: bool = False
    reroll_of: str | None = None
    excluded_tmdb_ids: list[int] = Field(default_factory=list)


class RecommendationResponse(BaseModel):
    request_id: str
    recommendation: Candidate
    pitch: str
    confidence: float
    reasoning: str
    streaming_sources: list[StreamingSource] = Field(default_factory=list)


class RankedRecommendation(BaseModel):
    selected_tmdb_id: int
    pitch: str
    confidence: float
    reasoning: str


class RecommendationError(BaseModel):
    request_id: str
    error: str
