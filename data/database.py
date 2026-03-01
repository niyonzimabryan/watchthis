from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

from config import Settings, get_settings

MIGRATION_PATH = Path(__file__).parent / "migrations" / "001_initial.sql"


def _to_json(data: Any) -> str:
    return json.dumps(data, separators=(",", ":"), ensure_ascii=True)


def _from_json(payload: str | None) -> Any:
    if not payload:
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


def create_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    settings = get_settings()
    target = Path(db_path) if db_path else settings.db_path_obj
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def managed_connection(db_path: str | Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    conn = create_connection(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(settings: Settings | None = None) -> None:
    cfg = settings or get_settings()
    with managed_connection(cfg.db_path_obj) as conn:
        run_migrations(conn)


def run_migrations(conn: sqlite3.Connection) -> None:
    migration_sql = MIGRATION_PATH.read_text(encoding="utf-8")
    conn.executescript(migration_sql)

    columns = {row["name"] for row in conn.execute("PRAGMA table_info(request_log)").fetchall()}
    if "session_id" not in columns:
        conn.execute("ALTER TABLE request_log ADD COLUMN session_id TEXT")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_request_log_session ON request_log(session_id)")


def insert_request_log(conn: sqlite3.Connection, row: dict[str, Any]) -> None:
    payload = dict(row)
    payload["mood_interpretation"] = _to_json(payload.get("mood_interpretation"))
    columns = ", ".join(payload.keys())
    placeholders = ", ".join(f":{key}" for key in payload.keys())
    conn.execute(
        f"INSERT INTO request_log ({columns}) VALUES ({placeholders})",
        payload,
    )


def update_request_error(conn: sqlite3.Connection, request_id: str, error: str) -> None:
    conn.execute(
        "UPDATE request_log SET error = ? WHERE id = ?",
        (error, request_id),
    )


def get_recent_selected_ids(
    conn: sqlite3.Connection,
    session_id: str | None,
    mood_input: str | None,
    limit: int = 5,
) -> list[int]:
    if not session_id:
        return []

    query = """
        SELECT selected_tmdb_id
        FROM request_log
        WHERE session_id = ? AND selected_tmdb_id IS NOT NULL
    """
    params: list[Any] = [session_id]
    if mood_input:
        query += " AND mood_input = ?"
        params.append(mood_input)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, tuple(params)).fetchall()
    return [int(row["selected_tmdb_id"]) for row in rows]


def get_recent_selected_titles(conn: sqlite3.Connection, session_id: str | None, limit: int = 25) -> list[str]:
    if not session_id:
        return []

    rows = conn.execute(
        """
        SELECT selected_title
        FROM request_log
        WHERE session_id = ?
          AND selected_title IS NOT NULL
          AND error IS NULL
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (session_id, limit),
    ).fetchall()
    return [str(row["selected_title"]) for row in rows if row["selected_title"]]


def get_title_selection_counts(conn: sqlite3.Connection, limit: int = 500) -> dict[str, int]:
    rows = conn.execute(
        """
        SELECT selected_title, COUNT(*) AS freq
        FROM request_log
        WHERE selected_title IS NOT NULL
          AND error IS NULL
        GROUP BY selected_title
        ORDER BY freq DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    return {str(row["selected_title"]): int(row["freq"]) for row in rows if row["selected_title"]}


def get_request_log(conn: sqlite3.Connection, request_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM request_log WHERE id = ?",
        (request_id,),
    ).fetchone()
    if not row:
        return None

    data = dict(row)
    data["mood_interpretation"] = _from_json(data.get("mood_interpretation"))
    return data
