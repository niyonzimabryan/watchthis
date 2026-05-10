from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

from config import get_settings


def _reload_server_app():
    import api.server as server

    importlib.reload(server)
    return server.app


@pytest.fixture
def client_with_force_https(monkeypatch):
    monkeypatch.setenv("WATCHTHIS_FORCE_HTTPS", "true")
    get_settings.cache_clear()
    app = _reload_server_app()
    try:
        yield TestClient(app)
    finally:
        monkeypatch.setenv("WATCHTHIS_FORCE_HTTPS", "false")
        get_settings.cache_clear()
        _reload_server_app()


@pytest.fixture
def client_without_force_https(monkeypatch):
    monkeypatch.setenv("WATCHTHIS_FORCE_HTTPS", "false")
    get_settings.cache_clear()
    app = _reload_server_app()
    yield TestClient(app)


def test_force_https_off_serves_http_directly(client_without_force_https):
    response = client_without_force_https.get("/health", follow_redirects=False)
    assert response.status_code != 307
    assert response.status_code != 308


def test_force_https_on_redirects_http_to_https(client_with_force_https):
    response = client_with_force_https.get("/health", follow_redirects=False)
    assert response.status_code in (307, 308)
    location = response.headers.get("location", "")
    assert location.startswith("https://"), f"expected https:// redirect, got {location!r}"
