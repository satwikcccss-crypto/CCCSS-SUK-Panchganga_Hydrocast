"""Compatibility shim: re-export backend.api.main."""

from backend.api.main import *  # noqa: F401,F403

__all__ = ["app"]
