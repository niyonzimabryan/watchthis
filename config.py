from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    tmdb_api_key: str | None = Field(default=None, alias="TMDB_API_KEY")
    tmdb_read_access_token: str | None = Field(default=None, alias="TMDB_READ_ACCESS_TOKEN")
    watchmode_api_key: str | None = Field(default=None, alias="WATCHMODE_API_KEY")
    omdb_api_key: str | None = Field(default=None, alias="OMDB_API_KEY")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    allow_heuristic_fallback: bool = Field(default=False, alias="WATCHTHIS_ALLOW_HEURISTIC_FALLBACK")

    db_path: str = Field(default="data/watchthis.db", alias="WATCHTHIS_DB_PATH")
    log_level: str = Field(default="INFO", alias="WATCHTHIS_LOG_LEVEL")
    http_timeout_seconds: float = Field(default=12.0, alias="WATCHTHIS_HTTP_TIMEOUT_SECONDS")

    haiku_model: str = Field(default="claude-haiku-4-5-20251001", alias="WATCHTHIS_HAIKU_MODEL")
    sonnet_model: str = Field(default="claude-sonnet-4-6", alias="WATCHTHIS_SONNET_MODEL")
    opus_model: str = Field(default="claude-opus-4-6", alias="WATCHTHIS_OPUS_MODEL")
    use_opus_for_ranking: bool = Field(default=True, alias="WATCHTHIS_USE_OPUS_FOR_RANKING")

    gemini_flash_model: str = Field(default="gemini-3.1-flash-lite-preview", alias="WATCHTHIS_GEMINI_FLASH_MODEL")
    gemini_pro_model: str = Field(default="gemini-3.1-pro-preview", alias="WATCHTHIS_GEMINI_PRO_MODEL")

    tmdb_discover_ttl_hours: int = 6
    title_cache_ttl_hours: int = 24
    omdb_cache_ttl_days: int = 7
    watchmode_cache_ttl_hours: int = 48
    watch_region: str = Field(default="US", alias="WATCHTHIS_WATCH_REGION")
    min_release_year: int = Field(default=1960, alias="WATCHTHIS_MIN_RELEASE_YEAR")
    quality_vote_count_floor: int = Field(default=500, alias="WATCHTHIS_QUALITY_VOTE_COUNT_FLOOR")

    rt_min_score: int = Field(default=75, alias="WATCHTHIS_RT_MIN_SCORE")
    rt_fallback_score: int = Field(default=70, alias="WATCHTHIS_RT_FALLBACK_SCORE")
    shortlist_size: int = Field(default=15, alias="WATCHTHIS_SHORTLIST_SIZE")
    allowed_countries_csv: str = Field(default="US,GB,KR,JP,FR", alias="WATCHTHIS_ALLOWED_COUNTRIES")
    curated_catalog_path: str = Field(default="data/curated_exceptions.md", alias="WATCHTHIS_CURATED_CATALOG_PATH")
    curated_catalog_enabled: bool = Field(default=True, alias="WATCHTHIS_CURATED_CATALOG_ENABLED")

    omdb_enrichment_limit: int = Field(default=20, alias="WATCHTHIS_OMDB_ENRICHMENT_LIMIT")

    @property
    def db_path_obj(self) -> Path:
        return Path(self.db_path)

    @property
    def allowed_countries(self) -> list[str]:
        return [chunk.strip().upper() for chunk in self.allowed_countries_csv.split(",") if chunk.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
