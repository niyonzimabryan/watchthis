from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any


def compute_query_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def get_tmdb_discover_cache(conn: sqlite3.Connection, query_hash: str) -> list[dict[str, Any]] | None:
    row = conn.execute(
        "SELECT response_json, expires_at FROM tmdb_discover_cache WHERE query_hash = ?",
        (query_hash,),
    ).fetchone()
    if not row:
        return None

    expires_at = datetime.fromisoformat(row["expires_at"])
    if _utc_now() > expires_at:
        conn.execute("DELETE FROM tmdb_discover_cache WHERE query_hash = ?", (query_hash,))
        return None

    try:
        return json.loads(row["response_json"])
    except json.JSONDecodeError:
        return None


def set_tmdb_discover_cache(
    conn: sqlite3.Connection,
    query_hash: str,
    data: list[dict[str, Any]],
    ttl_hours: int,
) -> None:
    expires_at = _utc_now() + timedelta(hours=ttl_hours)
    conn.execute(
        """
        INSERT INTO tmdb_discover_cache (query_hash, response_json, expires_at)
        VALUES (?, ?, ?)
        ON CONFLICT(query_hash) DO UPDATE SET
            response_json = excluded.response_json,
            cached_at = CURRENT_TIMESTAMP,
            expires_at = excluded.expires_at
        """,
        (query_hash, json.dumps(data, ensure_ascii=True), _iso(expires_at)),
    )


def get_title_cache(conn: sqlite3.Connection, tmdb_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM title_cache WHERE tmdb_id = ?",
        (tmdb_id,),
    ).fetchone()
    if not row:
        return None

    parsed = dict(row)
    for key in ("tmdb_data", "omdb_data", "watchmode_data"):
        try:
            parsed[key] = json.loads(parsed[key]) if parsed.get(key) else None
        except json.JSONDecodeError:
            parsed[key] = None
    return parsed


def upsert_title_cache(
    conn: sqlite3.Connection,
    tmdb_id: int,
    media_type: str,
    tmdb_data: dict[str, Any],
    omdb_data: dict[str, Any] | None = None,
    watchmode_data: list[dict[str, Any]] | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO title_cache (
            tmdb_id,
            media_type,
            tmdb_data,
            omdb_data,
            watchmode_data,
            tmdb_cached_at,
            omdb_cached_at,
            watchmode_cached_at
        ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT(tmdb_id) DO UPDATE SET
            media_type = excluded.media_type,
            tmdb_data = excluded.tmdb_data,
            omdb_data = COALESCE(excluded.omdb_data, title_cache.omdb_data),
            watchmode_data = COALESCE(excluded.watchmode_data, title_cache.watchmode_data),
            tmdb_cached_at = CURRENT_TIMESTAMP,
            omdb_cached_at = CASE
                WHEN excluded.omdb_data IS NULL THEN title_cache.omdb_cached_at
                ELSE CURRENT_TIMESTAMP
            END,
            watchmode_cached_at = CASE
                WHEN excluded.watchmode_data IS NULL THEN title_cache.watchmode_cached_at
                ELSE CURRENT_TIMESTAMP
            END
        """,
        (
            tmdb_id,
            media_type,
            json.dumps(tmdb_data, ensure_ascii=True),
            json.dumps(omdb_data, ensure_ascii=True) if omdb_data is not None else None,
            json.dumps(watchmode_data, ensure_ascii=True) if watchmode_data is not None else None,
        ),
    )
