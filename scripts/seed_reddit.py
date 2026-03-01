from __future__ import annotations

import anyio

from reddit.cron import run_weekly_scrape


if __name__ == "__main__":
    anyio.run(run_weekly_scrape)
