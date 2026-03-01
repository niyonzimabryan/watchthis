from __future__ import annotations

from reddit.extractor import RecommendationExtractor


def test_recommendation_extractor_pair_pattern():
    extractor = RecommendationExtractor()

    pairs = extractor.extract_pairs("If you like Inception -> watch The Prestige")

    assert pairs
    assert pairs[0]["source_title"].lower().startswith("if you like inception".split()[0])
    assert "recommended_title" in pairs[0]


def test_recommendation_extractor_fallback_for_recommend_posts():
    extractor = RecommendationExtractor()

    pairs = extractor.extract_pairs("Can you recommend something cozy and funny?")

    assert pairs
    assert pairs[0]["mood_tags"]
