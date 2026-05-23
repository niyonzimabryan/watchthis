from __future__ import annotations

import importlib

from fastapi.testclient import TestClient

from api.cast_manager import CastManager


def _reload_server_app():
    import api.server as server

    importlib.reload(server)
    return server.app


def test_app_uses_lifespan_instead_of_deprecated_startup_handlers():
    app = _reload_server_app()

    assert app.router.on_startup == []


def test_lifespan_initializes_cast_manager():
    app = _reload_server_app()

    assert not hasattr(app.state, "cast_manager")
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert isinstance(app.state.cast_manager, CastManager)
