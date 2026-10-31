"""
src/api/keys.py
===============
Scoped API keys for read-only external consumers.

HydroCast has two key classes:

* **Master key** (``API_KEY``) — full public + admin fallback (newsroom / ops).
* **Consumer keys** — read-only public reads only. They are *never* accepted by
  the admin router. This lets an external model (Hydrosim / HEC-RAS) pull water
  levels without holding the master credential.

``HYDROCAST_READONLY_KEY`` is the named read-only key for an external flood
model (Hydrosim / HEC-RAS). The older name ``HYDROSIM_API_KEY`` is still
accepted as an alias, so existing setups do not break.
``CONSUMER_API_KEYS`` is a comma-separated list for zero-downtime rotation:
add the new key, deploy the consumer with it, then remove the old one.

Every comparison is constant-time, and all configured keys are compared even
after a match so timing does not disclose how many keys exist.
"""

from __future__ import annotations

import hmac
import os

from dotenv import load_dotenv

load_dotenv()  # local dev: pick up .env before reading keys


def _split(value: str) -> tuple[str, ...]:
    return tuple(k.strip() for k in value.split(",") if k.strip())


# Read at import; callers load .env first (src/api/main.py, src/orchestrator.py).
HYDROCAST_READONLY_KEY = os.getenv("HYDROCAST_READONLY_KEY", "")
# Legacy alias: earlier builds used HYDROSIM_API_KEY for the same read-only key.
HYDROSIM_API_KEY = os.getenv("HYDROSIM_API_KEY", "")
_CONSUMER_KEYS = _split(os.getenv("CONSUMER_API_KEYS", ""))


def consumer_keys() -> tuple[str, ...]:
    """All configured consumer keys, de-duplicated, order preserved."""
    keys = [HYDROCAST_READONLY_KEY, HYDROSIM_API_KEY, *_CONSUMER_KEYS]
    return tuple(dict.fromkeys(k for k in keys if k))


def verify_consumer_key(supplied: str | None) -> bool:
    """True if *supplied* matches any consumer key. Always fail-closed."""
    if not supplied:
        return False
    matched = False
    for key in consumer_keys():
        matched |= hmac.compare_digest(supplied.encode("utf-8"), key.encode("utf-8"))
    return matched


def verify_public_key(supplied: str | None, master_key: str) -> bool:
    """True for the master key or any consumer key (public reads only)."""
    if not supplied:
        return False
    matched = bool(master_key) and hmac.compare_digest(
        supplied.encode("utf-8"), master_key.encode("utf-8")
    )
    for key in consumer_keys():
        matched |= hmac.compare_digest(supplied.encode("utf-8"), key.encode("utf-8"))
    return matched
