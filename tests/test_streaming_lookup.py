from __future__ import annotations

import pytest

from clients.watchmode_client import WatchmodeClient
from core.streaming_lookup import StreamingLookup
from data.models import StreamingSource


@pytest.mark.asyncio
async def test_streaming_lookup_graceful_without_api_key():
    lookup = StreamingLookup(WatchmodeClient())
    sources = await lookup.get_sources(27205, "movie", "Inception", 2010)

    assert len(sources) == 1
    assert sources[0].name == "JustWatch"
    assert "justwatch.com" in (sources[0].web_url or "")


def test_watchmode_sort_priority():
    sources = [
        StreamingSource(name="RentService", type="rent"),
        StreamingSource(name="SubService", type="sub"),
        StreamingSource(name="FreeService", type="free"),
    ]

    sorted_sources = sorted(sources, key=WatchmodeClient._sort_priority)

    assert [source.type for source in sorted_sources] == ["sub", "free", "rent"]
