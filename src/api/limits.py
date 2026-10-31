"""
src/api/limits.py
=================
Shared slowapi rate limiter.

Extracted so both ``main.py`` (public reads) and ``admin.py`` (login) can use the
same limiter instance. ``app.state.limiter`` is set in ``main.py``.
"""

import os

from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.util import get_remote_address

load_dotenv()  # local dev: pick up .env before reading limits

# Public read budget per client IP.
RATE_LIMIT_PUBLIC = os.getenv("RATE_LIMIT_PUBLIC", "100/minute")
# Login is deliberately much tighter to blunt password brute-forcing.
RATE_LIMIT_LOGIN = os.getenv("RATE_LIMIT_LOGIN", "5/minute")

limiter = Limiter(key_func=get_remote_address, default_limits=[RATE_LIMIT_PUBLIC])
