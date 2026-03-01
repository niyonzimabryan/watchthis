from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from dotenv import load_dotenv


def main() -> int:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")

    parser = argparse.ArgumentParser(description="Inspect request_log traces from watchthis.db")
    parser.add_argument("--db", default="data/watchthis.db", help="Path to SQLite DB")
    parser.add_argument("--request-id", default=None, help="Request ID to inspect")
    parser.add_argument("--latest", action="store_true", help="Show latest request")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"DB not found: {db_path}")
        return 1

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    if args.request_id:
        row = conn.execute("SELECT * FROM request_log WHERE id = ?", (args.request_id,)).fetchone()
    else:
        row = conn.execute("SELECT * FROM request_log ORDER BY timestamp DESC LIMIT 1").fetchone()

    if not row:
        print("No request log rows found")
        return 1

    data = dict(row)
    mood = data.get("mood_interpretation")
    if mood:
        try:
            data["mood_interpretation"] = json.loads(mood)
        except json.JSONDecodeError:
            pass

    print(json.dumps(data, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
