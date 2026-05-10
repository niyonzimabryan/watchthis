from __future__ import annotations

import importlib
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.rate_limit import FixedWindowLimiter, Window, reset_limiter
from config import get_settings


def test_limiter_allows_under_burst():
    limiter = FixedWindowLimiter([Window(max_count=3, seconds=60)])
    for _ in range(3):
        allowed, retry_after = limiter.check("ip-a", now=1000.0)
        assert allowed is True
        assert retry_after == 0


def test_limiter_blocks_over_burst_returns_retry_after():
    # All three calls land in the same fixed window [960, 1020).
    limiter = FixedWindowLimiter([Window(max_count=2, seconds=60)])
    assert limiter.check("ip-a", now=961.0) == (True, 0)
    assert limiter.check("ip-a", now=970.0) == (True, 0)
    allowed, retry_after = limiter.check("ip-a", now=980.0)
    assert allowed is False
    assert retry_after > 0
    assert retry_after <= 60


def test_limiter_separates_keys():
    limiter = FixedWindowLimiter([Window(max_count=1, seconds=60)])
    assert limiter.check("ip-a", now=961.0) == (True, 0)
    assert limiter.check("ip-b", now=961.0) == (True, 0)
    assert limiter.check("ip-a", now=970.0)[0] is False


def test_limiter_window_rolls_over():
    limiter = FixedWindowLimiter([Window(max_count=1, seconds=60)])
    assert limiter.check("ip-a", now=961.0) == (True, 0)
    assert limiter.check("ip-a", now=970.0)[0] is False
    assert limiter.check("ip-a", now=2000.0) == (True, 0)


def test_limiter_atomic_across_windows():
    """Hourly cap shouldn't be consumed by a request that the burst cap rejects."""
    # Hourly window for ts=3601..7200. Burst windows of 60s land inside it.
    limiter = FixedWindowLimiter([Window(max_count=1, seconds=60), Window(max_count=10, seconds=3600)])
    assert limiter.check("ip-a", now=3610.0) == (True, 0)
    assert limiter.check("ip-a", now=3620.0)[0] is False  # burst rejects, hourly should NOT consume
    # Across the next 9 burst windows (still inside the same hour), each first
    # request should succeed because hourly has 9 left.
    for n in range(9):
        ts = 3661.0 + n * 60  # one request per fresh burst window
        allowed, _ = limiter.check("ip-a", now=ts)
        assert allowed is True, f"hourly cap consumed by rejected requests; failed at iter {n}"


def _reload_app() -> Any:
    import api.server as server

    importlib.reload(server)
    return server.app


@pytest.fixture
def client_with_tight_limit(monkeypatch):
    monkeypatch.setenv("WATCHTHIS_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("WATCHTHIS_RATE_LIMIT_BURST_PER_MIN", "1")
    monkeypatch.setenv("WATCHTHIS_RATE_LIMIT_HOURLY", "100")
    get_settings.cache_clear()
    reset_limiter()
    app = _reload_app()
    yield TestClient(app)
    reset_limiter()


@pytest.fixture
def client_with_disabled_limit(monkeypatch):
    monkeypatch.setenv("WATCHTHIS_RATE_LIMIT_ENABLED", "false")
    get_settings.cache_clear()
    reset_limiter()
    app = _reload_app()
    yield TestClient(app)
    reset_limiter()


def test_recommend_returns_429_after_burst_exceeded(client_with_tight_limit):
    payload = {"mood_input": "cozy comfort comedy"}
    # First request: rate-limit dep allows; orchestrator may 5xx because no API
    # keys in test env. We don't assert status, just that we got past the limiter.
    first = client_with_tight_limit.post("/recommend", json=payload)
    assert first.status_code != 429

    second = client_with_tight_limit.post("/recommend", json=payload)
    assert second.status_code == 429
    body = second.json()
    assert "Too many" in body["detail"]
    retry_after = second.headers.get("retry-after")
    assert retry_after is not None and int(retry_after) > 0


def test_roulette_uses_same_limiter_bucket(client_with_tight_limit):
    """A burst on /recommend should also throttle /roulette — both protect LLM calls."""
    client_with_tight_limit.post("/recommend", json={"mood_input": "anything"})
    second = client_with_tight_limit.post("/roulette", json={})
    assert second.status_code == 429


def test_disabled_flag_lets_traffic_through(client_with_disabled_limit):
    for _ in range(5):
        response = client_with_disabled_limit.post("/recommend", json={"mood_input": "ping"})
        assert response.status_code != 429
