from __future__ import annotations

import os
from pathlib import Path

import pytest

from config import get_settings
from data.database import init_db


@pytest.fixture(autouse=True)
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "watchthis_test.db"
    monkeypatch.setenv("WATCHTHIS_DB_PATH", str(db_path))
    monkeypatch.setenv("TMDB_API_KEY", "")
    monkeypatch.setenv("TMDB_READ_ACCESS_TOKEN", "")
    monkeypatch.setenv("WATCHMODE_API_KEY", "")
    monkeypatch.setenv("OMDB_API_KEY", "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("WATCHTHIS_ALLOW_HEURISTIC_FALLBACK", "true")

    get_settings.cache_clear()
    init_db(get_settings())
    yield
    get_settings.cache_clear()


@pytest.fixture
def test_db_path() -> Path:
    return Path(os.environ["WATCHTHIS_DB_PATH"])
