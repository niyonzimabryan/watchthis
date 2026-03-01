from __future__ import annotations


class DependencyUnavailableError(RuntimeError):
    """Raised when a required third-party dependency is unavailable."""
