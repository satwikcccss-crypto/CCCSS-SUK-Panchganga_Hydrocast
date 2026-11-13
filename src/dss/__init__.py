"""Compatibility shim: re-export backend.dss public names."""

from backend.dss import *  # noqa: F401,F403
from backend.dss.writer import *  # noqa: F401,F403

__all__ = ["writer"]
