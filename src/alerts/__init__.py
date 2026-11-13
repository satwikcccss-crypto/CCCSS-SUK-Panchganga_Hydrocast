"""Compatibility shim: re-export backend.alerts public names."""

from backend.alerts import *  # noqa: F401,F403
from backend.alerts.evaluator import *  # noqa: F401,F403
from backend.alerts.telegram_bot import *  # noqa: F401,F403

__all__ = ["evaluator", "telegram_bot"]
