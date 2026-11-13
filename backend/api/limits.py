"""
backend/api/limits.py
=====================
Shared slowapi rate limiter.

Extracted so both ``main.py`` (public reads) and ``admin.py`` (login) can use the
same limiter instance. ``app.state.limiter`` is set in ``main.py``.
"""

import ipaddress
import logging
import os

from dotenv import load_dotenv
from slowapi import Limiter
from starlette.requests import Request

load_dotenv()  # local dev: pick up .env before reading limits

log = logging.getLogger(__name__)

# Public read budget per client IP. 60/minute is the recommended public-tier
# setting from the Open-Meteo-style access ADR; override for your deployment.
RATE_LIMIT_PUBLIC = os.getenv("RATE_LIMIT_PUBLIC", "60/minute")
# Optional short-window burst guard (e.g. ``10/second``). Empty disables it.
RATE_LIMIT_BURST = os.getenv("RATE_LIMIT_BURST", "")
# Login is deliberately much tighter to blunt password brute-forcing.
RATE_LIMIT_LOGIN = os.getenv("RATE_LIMIT_LOGIN", "5/minute")

_default_limits = [RATE_LIMIT_PUBLIC]
if RATE_LIMIT_BURST:
    _default_limits.append(RATE_LIMIT_BURST)


def _parse_trusted_proxies(raw: str) -> set[ipaddress._BaseNetwork]:
    """Parse a comma-separated CIDR list, ignoring malformed entries."""
    networks: set[ipaddress._BaseNetwork] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            networks.add(ipaddress.ip_network(part, strict=False))
        except ValueError:
            log.warning("Ignoring invalid trusted-proxy CIDR: %s", part)
    return networks


# Default-deny: only a loopback reverse proxy is trusted out of the box.
# Deployments behind Caddy/nginx must opt in explicitly, e.g.
#   HYDROCAST_TRUSTED_PROXIES=127.0.0.1/32,172.18.0.0/16
_TRUSTED_PROXIES = _parse_trusted_proxies(
    os.getenv("HYDROCAST_TRUSTED_PROXIES", "127.0.0.1/32,::1/128")
)


def _to_ip(value: str) -> ipaddress._BaseAddress | None:
    try:
        return ipaddress.ip_address(value)
    except ValueError:
        return None


def _is_trusted_proxy(ip: ipaddress._BaseAddress) -> bool:
    return any(ip in network for network in _TRUSTED_PROXIES)


def get_real_client_ip(request: Request) -> str:
    """Return the client IP, honouring proxy headers only from trusted peers.

    The forwarding chain is walked right-to-left; the first address that is not
    itself a trusted proxy is the real client. This prevents a client-supplied
    ``X-Forwarded-For`` prefix from choosing its own rate-limit bucket.
    """
    direct_raw = request.client.host if request.client else "127.0.0.1"
    direct_ip = _to_ip(direct_raw)
    if direct_ip is None or not _is_trusted_proxy(direct_ip):
        return direct_raw

    forwarded = request.headers.get("X-Forwarded-For", "")
    chain = [part.strip() for part in forwarded.split(",") if part.strip()]
    if not chain:
        real_ip = _to_ip(request.headers.get("X-Real-IP", "").strip())
        if real_ip is not None and not _is_trusted_proxy(real_ip):
            return str(real_ip)
        return str(direct_ip)

    parsed = [ip for ip in (_to_ip(item) for item in chain) if ip is not None]
    for candidate in reversed(parsed):
        if not _is_trusted_proxy(candidate):
            return str(candidate)

    # Every hop in the chain is trusted; fall back to the leftmost valid address.
    return str(parsed[0]) if parsed else str(direct_ip)


limiter = Limiter(key_func=get_real_client_ip, default_limits=_default_limits)
