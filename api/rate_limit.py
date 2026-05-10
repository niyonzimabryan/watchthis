from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Iterable

from fastapi import HTTPException, Request

from config import get_settings


@dataclass(frozen=True)
class Window:
    """One fixed-window bucket: at most ``max_count`` events per ``seconds`` per key."""

    max_count: int
    seconds: int


class FixedWindowLimiter:
    """In-memory fixed-window rate limiter.

    Single-replica only — Railway runs one container per service for WatchThis,
    so per-process state is the right granularity. Switch to Redis if/when we
    horizontally scale. Stale buckets are pruned lazily on access plus a
    coarse opportunistic sweep so a long-lived process doesn't grow unbounded.
    """

    def __init__(self, windows: Iterable[Window]):
        self._windows = tuple(windows)
        self._buckets: dict[tuple[int, str], tuple[int, int]] = {}
        self._lock = threading.Lock()
        self._last_sweep = 0.0

    def check(self, key: str, *, now: float | None = None) -> tuple[bool, int]:
        """Record an event. Returns (allowed, retry_after_seconds).

        retry_after_seconds is 0 when allowed; otherwise the seconds remaining in
        the most-restrictive window that rejected the request. Atomic across all
        windows: if any window rejects, no window's count is incremented.
        """
        ts = int(now if now is not None else time.time())

        with self._lock:
            self._maybe_sweep(ts)

            snapshots: list[tuple[tuple[int, str], int, int, Window]] = []
            retry_after = 0
            blocked = False

            for idx, window in enumerate(self._windows):
                bucket_key = (idx, key)
                window_start = ts - (ts % window.seconds)
                stored_start, stored_count = self._buckets.get(bucket_key, (window_start, 0))
                if stored_start != window_start:
                    stored_start, stored_count = window_start, 0

                if stored_count >= window.max_count:
                    blocked = True
                    seconds_left = window.seconds - (ts - stored_start)
                    retry_after = max(retry_after, seconds_left)

                snapshots.append((bucket_key, stored_start, stored_count, window))

            if blocked:
                return False, retry_after

            for bucket_key, stored_start, stored_count, _ in snapshots:
                self._buckets[bucket_key] = (stored_start, stored_count + 1)

        return True, 0

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()
            self._last_sweep = 0.0

    def _maybe_sweep(self, ts: int) -> None:
        # Cheap eviction: every 5 minutes drop buckets whose windows have
        # already rolled over. Keeps memory bounded under churn.
        if ts - self._last_sweep < 300:
            return
        self._last_sweep = ts
        max_window = max(w.seconds for w in self._windows)
        cutoff = ts - max_window
        stale = [k for k, (start, _) in self._buckets.items() if start < cutoff]
        for k in stale:
            self._buckets.pop(k, None)


# Module-level singleton. Built lazily so config env reads are deferred until
# first request (lets pytest monkeypatch env before app boot).
_LIMITER: FixedWindowLimiter | None = None


def _build_limiter() -> FixedWindowLimiter:
    settings = get_settings()
    return FixedWindowLimiter(
        windows=(
            Window(max_count=settings.rate_limit_burst_per_min, seconds=60),
            Window(max_count=settings.rate_limit_hourly, seconds=3600),
        )
    )


def get_limiter() -> FixedWindowLimiter:
    global _LIMITER
    if _LIMITER is None:
        _LIMITER = _build_limiter()
    return _LIMITER


def reset_limiter() -> None:
    """Test hook: drop the singleton so the next call rebuilds with current env."""
    global _LIMITER
    _LIMITER = None


def _client_key(request: Request) -> str:
    # uvicorn --proxy-headers populates request.client.host from X-Forwarded-For,
    # so this is the real client IP behind Railway's proxy. Falls back to the
    # raw socket peer for direct (non-proxied) connections like local dev.
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


async def enforce_recommend_rate_limit(request: Request) -> None:
    """FastAPI dependency: throttle expensive LLM-backed endpoints by client IP."""
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return

    key = _client_key(request)
    allowed, retry_after = get_limiter().check(key)
    if allowed:
        return

    raise HTTPException(
        status_code=429,
        detail=(
            "Too many recommendations from your network in a short window. "
            f"Try again in about {retry_after} second{'s' if retry_after != 1 else ''}."
        ),
        headers={"Retry-After": str(retry_after)},
    )
