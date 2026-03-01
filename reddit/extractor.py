from __future__ import annotations

import re
from typing import Any

PAIR_PATTERN = re.compile(r"(?P<source>[A-Za-z0-9 ':-]{2,})\s*(?:->|to|similar to)\s*(?P<rec>[A-Za-z0-9 ':-]{2,})", re.IGNORECASE)


class RecommendationExtractor:
    def extract_pairs(self, post_title: str, post_body: str = "") -> list[dict[str, Any]]:
        text = f"{post_title}\n{post_body}".strip()
        pairs: list[dict[str, Any]] = []

        for match in PAIR_PATTERN.finditer(text):
            source = match.group("source").strip()
            rec = match.group("rec").strip()
            if source.lower() == rec.lower():
                continue
            pairs.append(
                {
                    "source_title": source,
                    "recommended_title": rec,
                    "mood_tags": self._infer_mood_tags(text),
                }
            )

        if not pairs and "recommend" in text.lower():
            # Minimal fallback extraction for broad recommendation posts.
            pairs.append(
                {
                    "source_title": "unknown",
                    "recommended_title": post_title[:120],
                    "mood_tags": self._infer_mood_tags(text),
                }
            )

        return pairs

    @staticmethod
    def _infer_mood_tags(text: str) -> list[str]:
        lowered = text.lower()
        tags = []
        for token in ["cozy", "dark", "funny", "thriller", "romantic", "scary", "comfort", "mind-bending"]:
            if token in lowered:
                tags.append(token)
        return tags
