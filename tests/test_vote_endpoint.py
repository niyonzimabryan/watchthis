from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.server import app
from data.database import insert_request_log, managed_connection


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def seeded_request_id():
    request_id = "req-test-001"
    with managed_connection() as conn:
        insert_request_log(
            conn,
            {
                "id": request_id,
                "session_id": "sess-tester-A",
                "mood_input": "cozy comedy",
                "format_filter": "any",
                "length_filter": "any",
                "mood_interpretation": {"keywords": ["cozy"]},
                "candidates_count": 5,
                "selected_tmdb_id": 999,
                "selected_title": "Test Title",
                "pitch": "test pitch",
                "confidence": 0.9,
                "reasoning": "because",
                "latency_ms": 100,
                "is_roulette": False,
                "is_reroll": False,
            },
        )
    return request_id


def test_vote_404_when_request_id_unknown(client):
    body = {
        "request_id": "does-not-exist",
        "vote": 1,
        "session_id": "sess-tester-A",
        "reason": None,
    }
    response = client.post("/vote", json=body)
    assert response.status_code == 404
    assert "couldn't find" in response.json()["detail"].lower()


def test_vote_persists_and_stats_reflects_it(client, seeded_request_id):
    response = client.post(
        "/vote",
        json={
            "request_id": seeded_request_id,
            "vote": 1,
            "session_id": "sess-tester-A",
            "reason": "made me smile",
        },
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}

    stats = client.get("/vote-stats").json()
    assert stats["upvotes"] == 1
    assert stats["downvotes"] == 0
    assert stats["total"] == 1
    assert stats["with_reason"] == 1
    assert stats["distinct_sessions"] == 1


def test_vote_upsert_replaces_prior_vote(client, seeded_request_id):
    client.post(
        "/vote",
        json={"request_id": seeded_request_id, "vote": 1, "session_id": "sess-A", "reason": "good"},
    )
    flip = client.post(
        "/vote",
        json={"request_id": seeded_request_id, "vote": -1, "session_id": "sess-A", "reason": "actually bad"},
    )
    assert flip.status_code == 200

    stats = client.get("/vote-stats").json()
    # Same (request_id, session_id) → one row, now downvote.
    assert stats["upvotes"] == 0
    assert stats["downvotes"] == 1
    assert stats["total"] == 1


def test_two_sessions_voting_on_same_request_both_count(client, seeded_request_id):
    for session_id, vote in [("sess-A", 1), ("sess-B", -1)]:
        client.post(
            "/vote",
            json={"request_id": seeded_request_id, "vote": vote, "session_id": session_id, "reason": None},
        )
    stats = client.get("/vote-stats").json()
    assert stats["upvotes"] == 1
    assert stats["downvotes"] == 1
    assert stats["total"] == 2
    assert stats["distinct_sessions"] == 2


def test_vote_rejects_invalid_value(client, seeded_request_id):
    response = client.post(
        "/vote",
        json={"request_id": seeded_request_id, "vote": 5, "session_id": "sess-A", "reason": None},
    )
    assert response.status_code == 422
    assert "vote must be" in response.json()["detail"].lower()


def test_vote_rejects_overlong_reason(client, seeded_request_id):
    response = client.post(
        "/vote",
        json={
            "request_id": seeded_request_id,
            "vote": 1,
            "session_id": "sess-A",
            "reason": "x" * 600,
        },
    )
    assert response.status_code == 422


def test_vote_rejects_missing_session_id(client, seeded_request_id):
    response = client.post(
        "/vote",
        json={"request_id": seeded_request_id, "vote": 1, "reason": None},
    )
    assert response.status_code == 422


def test_vote_stats_empty_db_returns_zeros(client):
    stats = client.get("/vote-stats").json()
    assert stats == {
        "upvotes": 0,
        "downvotes": 0,
        "total": 0,
        "with_reason": 0,
        "distinct_sessions": 0,
    }
