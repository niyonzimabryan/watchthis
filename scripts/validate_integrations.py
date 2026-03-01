from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from clients.anthropic_client import AnthropicClient
from clients.omdb_client import OMDbClient
from clients.tmdb_client import TMDBClient
from clients.watchmode_client import WatchmodeClient
from config import get_settings
from core.errors import DependencyUnavailableError


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


async def check_tmdb() -> CheckResult:
    settings = get_settings()
    if not (settings.tmdb_api_key or settings.tmdb_read_access_token):
        return CheckResult("TMDB", False, "Missing TMDB_API_KEY or TMDB_READ_ACCESS_TOKEN")

    client = TMDBClient(settings)
    try:
        rows = await client.trending("movie", "week")
        return CheckResult("TMDB", True, f"ok ({len(rows)} trending rows)")
    except Exception as exc:
        return CheckResult("TMDB", False, f"request failed: {exc}")


async def check_omdb() -> CheckResult:
    settings = get_settings()
    if not settings.omdb_api_key:
        return CheckResult("OMDb", False, "Missing OMDB_API_KEY")

    client = OMDbClient(settings)
    try:
        payload = await client.get_by_imdb_id("tt1375666")
        if not payload:
            return CheckResult("OMDb", False, "no payload for tt1375666")
        return CheckResult("OMDb", True, "ok")
    except Exception as exc:
        return CheckResult("OMDb", False, f"request failed: {exc}")


async def check_watchmode() -> CheckResult:
    settings = get_settings()
    if not settings.watchmode_api_key:
        return CheckResult("Watchmode", False, "Missing WATCHMODE_API_KEY")

    client = WatchmodeClient(settings)
    try:
        sources = await client.get_sources_for_tmdb_id(27205, media_type="movie")
        return CheckResult("Watchmode", True, f"ok ({len(sources)} sources for Inception)")
    except Exception as exc:
        return CheckResult("Watchmode", False, f"request failed: {exc}")


async def check_anthropic() -> CheckResult:
    settings = get_settings()
    if not settings.anthropic_api_key:
        return CheckResult("Anthropic", False, "Missing ANTHROPIC_API_KEY")

    client = AnthropicClient(settings)
    try:
        mood = await client.interpret_mood("cozy comfort comedy")
        if not mood.genres:
            return CheckResult("Anthropic", False, "interpretation returned empty genres")
        return CheckResult("Anthropic", True, "ok")
    except DependencyUnavailableError as exc:
        return CheckResult("Anthropic", False, str(exc))
    except Exception as exc:
        return CheckResult("Anthropic", False, f"request failed: {exc}")


async def main() -> None:
    checks = await asyncio.gather(
        check_tmdb(),
        check_omdb(),
        check_watchmode(),
        check_anthropic(),
    )

    failures = 0
    for check in checks:
        mark = "OK" if check.ok else "FAIL"
        print(f"[{mark}] {check.name}: {check.detail}")
        if not check.ok:
            failures += 1

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
