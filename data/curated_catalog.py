from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from data.models import Candidate


@dataclass(frozen=True)
class CuratedEntry:
    title: str
    media_type: str | None
    year: int | None


class CuratedCatalog:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._entries: set[CuratedEntry] = set()
        self._title_index: set[str] = set()
        self._loaded = False

    def contains(self, candidate: Candidate) -> bool:
        self._load_if_needed()
        title_key = self._normalize_title(candidate.title)
        if title_key not in self._title_index:
            return False

        key = CuratedEntry(
            title=title_key,
            media_type=(candidate.media_type or "").strip().lower() or None,
            year=candidate.year,
        )
        if key in self._entries:
            return True

        # Fallback matches if the list omitted media type/year granularity.
        return CuratedEntry(title=title_key, media_type=None, year=None) in self._entries

    def count(self) -> int:
        self._load_if_needed()
        return len(self._entries)

    def _load_if_needed(self) -> None:
        if self._loaded:
            return
        self._loaded = True

        if not self.path.exists():
            return

        text = self.path.read_text(encoding="utf-8")
        lines = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
        if not lines:
            return

        header_line = lines[0]
        headers = [cell.strip().lower() for cell in header_line.strip("|").split("|")]
        header_idx = {name: idx for idx, name in enumerate(headers)}

        title_idx = header_idx.get("title")
        media_type_idx = header_idx.get("media_type")
        year_idx = header_idx.get("year")
        if title_idx is None:
            return

        for line in lines[1:]:
            if set(line.replace("|", "").strip()) <= {"-", ":"}:
                continue
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if title_idx >= len(cells):
                continue

            title = self._normalize_title(cells[title_idx])
            if not title:
                continue

            media_type: str | None = None
            if media_type_idx is not None and media_type_idx < len(cells):
                media = cells[media_type_idx].strip().lower()
                media_type = media if media in {"movie", "tv"} else None

            year: int | None = None
            if year_idx is not None and year_idx < len(cells):
                try:
                    year = int(cells[year_idx])
                except ValueError:
                    year = None

            entry = CuratedEntry(title=title, media_type=media_type, year=year)
            self._entries.add(entry)
            self._title_index.add(title)

            if media_type is None and year is None:
                self._entries.add(CuratedEntry(title=title, media_type=None, year=None))

    @staticmethod
    def _normalize_title(title: str) -> str:
        folded = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
        folded = folded.replace("&", " and ")
        return " ".join(re.sub(r"[^a-z0-9]+", " ", folded.lower()).split())
