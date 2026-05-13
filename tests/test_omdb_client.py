from __future__ import annotations

from clients.omdb_client import OMDbClient


def test_parse_awards_oscar_winner():
    payload = {"Awards": "Won 4 Oscars. 159 wins & 220 nominations total"}
    raw, badge = OMDbClient.parse_awards(payload)
    assert raw == "Won 4 Oscars. 159 wins & 220 nominations total"
    assert badge == "Oscar Winner"


def test_parse_awards_oscar_nominee():
    payload = {"Awards": "Nominated for 3 Oscars. 12 wins & 24 nominations total"}
    _, badge = OMDbClient.parse_awards(payload)
    assert badge == "Oscar Nominee"


def test_parse_awards_emmy_winner_outranked_by_oscar():
    # If both appear, Oscar wins (priority order)
    payload = {"Awards": "Won 1 Oscar and 2 Primetime Emmys. 5 wins."}
    _, badge = OMDbClient.parse_awards(payload)
    assert badge == "Oscar Winner"


def test_parse_awards_primetime_emmy_winner():
    payload = {"Awards": "Won 1 Primetime Emmy. 9 wins & 19 nominations total"}
    _, badge = OMDbClient.parse_awards(payload)
    assert badge == "Emmy Winner"


def test_parse_awards_generic_wins_no_badge():
    # Plenty of wins but none for tracked prestige awards — no badge.
    payload = {"Awards": "10 wins & 16 nominations total"}
    raw, badge = OMDbClient.parse_awards(payload)
    assert raw == "10 wins & 16 nominations total"
    assert badge is None


def test_parse_awards_na():
    raw, badge = OMDbClient.parse_awards({"Awards": "N/A"})
    assert raw is None
    assert badge is None


def test_parse_awards_missing_payload():
    raw, badge = OMDbClient.parse_awards(None)
    assert raw is None
    assert badge is None


def test_parse_awards_missing_field():
    raw, badge = OMDbClient.parse_awards({})
    assert raw is None
    assert badge is None
