"""Compatibility shim: re-export backend.api public names."""

from backend.api import *  # noqa: F401,F403
from backend.api.main import *  # noqa: F401,F403
from backend.api.admin import *  # noqa: F401,F403
from backend.api.security import *  # noqa: F401,F403
from backend.api.keys import *  # noqa: F401,F403
from backend.api.limits import *  # noqa: F401,F403

__all__ = [
    "main",
    "admin",
    "security",
    "keys",
    "limits",
]
