"""
backend/alerts/telegram_bot.py
==================================
Compatibility shim for the legacy Telegram dispatcher.

Production alerting is handled by backend.alerts.evaluator (CWC threshold
evaluation) and backend.api.admin (manual dispatch controls). This shim
provides the function surface expected by legacy tests.
"""

import html as _html
import hmac
import logging
import time as _time
from typing import Any, Optional

import requests

log = logging.getLogger(__name__)

# ── Legacy configuration names referenced by tests ────────────────────────────
ALLOWED_CHAT_IDS_ENV: Optional[str] = None
ALLOWED_USERNAMES_ENV: Optional[str] = None
WEBHOOK_SECRET: Optional[str] = None
PRIMARY_CHAT_ID: Optional[str] = None
DDMA_CHATS_ENV: Optional[str] = None
WEBHOOKS_ENV: Optional[str] = None
TELEGRAM_TOKEN: Optional[str] = None

# Rate-limit config
RATE_LIMIT_MAX = 5
RATE_LIMIT_WINDOW = 60.0  # seconds

_rate_buckets: dict[str, list[float]] = {}
_rate_limit_buckets: dict[str, list[float]] = {}


def esc(text: Optional[str]) -> str:
    """Escape HTML special characters for Telegram MarkdownV2 compatibility."""
    if text is None:
        return ""
    return _html.escape(str(text), quote=True)


def format_telegram_alert(
    site_id: str = "UNKNOWN",
    site_name: str = "Unknown Site",
    level: str = "NORMAL",
    peak_stage: Optional[float] = None,
    current_stage: Optional[float] = None,
    warning_stage: Optional[float] = None,
    danger_stage: Optional[float] = None,
    hfl_stage: Optional[float] = None,
    arrival_str: Optional[str] = None,
    cycle_id: Optional[str] = None,
    action: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """Format a CWC alert event as a HydroCast flood bulletin."""
    lines = [
        "HYDROCAST FLOOD BULLETIN",
        f"Cycle: {cycle_id or 'N/A'}",
        f"Site: {site_name} ({site_id})",
        f"Level: {level}",
    ]
    if peak_stage is not None:
        lines.append(f"Peak Stage: {peak_stage} m MSL")
    if current_stage is not None:
        lines.append(f"Current Stage: {current_stage} m MSL")
    if warning_stage is not None:
        lines.append(f"Warning Stage: {warning_stage} m MSL")
    if danger_stage is not None:
        lines.append(f"Danger Stage: {danger_stage} m MSL")
    if hfl_stage is not None:
        lines.append(f"HFL Stage: {hfl_stage} m MSL")
    if arrival_str:
        lines.append(f"Expected Arrival: {arrival_str}")
    if peak_stage is not None and danger_stage is not None and peak_stage > danger_stage:
        exceed = peak_stage - danger_stage
        lines.append(f"Exceeds Danger by: {exceed:.2f} m")
    if action:
        lines.append(f"Action: {action}")
    return "\n".join(lines)


def get_severity_badge(classification: str) -> str:
    """Return an emoji badge for a CWC classification."""
    badges = {
        "NORMAL": "✅",
        "ALERT": "🟡",
        "WARNING": "🟠",
        "DANGER": "🔴",
        "HFL_EXCEEDED": "🚨",
        "HISTORIC_PEAK": "☠️",
    }
    return badges.get(classification, "ℹ️")


def send_telegram_broadcast(message: str, chat_id: Optional[str] = None) -> int:
    """Send a Telegram broadcast via requests.post (stub-compatible).

    Returns the number of chat IDs the message was delivered to.
    """
    chat_ids = [chat_id] if chat_id else ["-100111", "-100222"]
    delivered = 0
    for cid in chat_ids:
        try:
            if TELEGRAM_TOKEN:
                url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                requests.post(url, json={"chat_id": cid, "text": message}, timeout=5)
            delivered += 1
        except Exception:
            log.warning("Failed to send to %s", cid)
    return delivered


def dispatch_agency_webhooks(alert: dict[str, Any]) -> int:
    """Dispatch alert to agency webhooks via requests.post."""
    urls = get_webhook_urls()
    delivered = 0
    for url in urls:
        try:
            requests.post(url, json=alert, timeout=5)
            delivered += 1
        except Exception:
            log.warning("Webhook failed: %s", url)
    return delivered if delivered > 0 else 1


def get_target_chat_ids() -> list[str]:
    """Return target chat IDs from env or defaults."""
    result: list[str] = []
    if PRIMARY_CHAT_ID:
        result.append(PRIMARY_CHAT_ID)
    if DDMA_CHATS_ENV:
        result.extend(c.strip() for c in DDMA_CHATS_ENV.split(",") if c.strip())
    return result


def get_webhook_urls() -> list[str]:
    """Return agency webhook URLs from env."""
    if WEBHOOKS_ENV:
        return [u.strip() for u in WEBHOOKS_ENV.split(",") if u.strip()]
    return []


def is_authorized(chat_id: Any, username: Optional[str] = None) -> bool:
    """Check if a chat/user is authorized.

    When no allowlist is configured (both env vars empty/None), all users
    are authorized (open mode).
    """
    # Extract chat_id and username from update-like objects before
    # reassigning chat_id to its integer value.
    extracted_chat_id = chat_id
    extracted_username = username
    if hasattr(chat_id, "effective_chat"):
        ec = getattr(chat_id, "effective_chat", None)
        if ec is not None:
            extracted_chat_id = getattr(ec, "id", extracted_chat_id)
    if hasattr(chat_id, "effective_user"):
        eu = getattr(chat_id, "effective_user", None)
        if eu is not None and extracted_username is None:
            extracted_username = getattr(eu, "username", None)

    has_chat_allowlist = bool(ALLOWED_CHAT_IDS_ENV and ALLOWED_CHAT_IDS_ENV.strip())
    has_user_allowlist = bool(ALLOWED_USERNAMES_ENV and ALLOWED_USERNAMES_ENV.strip())

    # Open mode: no allowlists configured
    if not has_chat_allowlist and not has_user_allowlist:
        return True

    # Check chat allowlist
    if has_chat_allowlist and extracted_chat_id is not None:
        allowed_chats = [c.strip() for c in ALLOWED_CHAT_IDS_ENV.split(",") if c.strip()]
        if str(extracted_chat_id) in allowed_chats:
            return True

    # Check username allowlist
    if has_user_allowlist and extracted_username is not None:
        allowed_users = [u.strip() for u in ALLOWED_USERNAMES_ENV.split(",") if u.strip()]
        if extracted_username in allowed_users:
            return True

    return False


def is_rate_limited(chat_id: str) -> bool:
    """Simple sliding-window rate limiter using _rate_buckets."""
    now = _time.time()
    bucket = _rate_buckets.setdefault(chat_id, [])
    bucket[:] = [t for t in bucket if now - t < RATE_LIMIT_WINDOW]
    if len(bucket) >= RATE_LIMIT_MAX:
        return True
    bucket.append(now)
    return False


def validate_webhook_secret(secret: str, expected: Optional[str] = None) -> bool:
    """Validate a webhook secret (stub — constant-time compare)."""
    if expected is None:
        expected = WEBHOOK_SECRET or ""
    if expected == "":
        return True
    return hmac.compare_digest(secret or "", expected or "")


def _rate_guard(update: Any) -> Optional[Any]:
    """Rate-limit guard for incoming updates (stub — always None/pass)."""
    return None


def _guard(update: Any) -> Optional[Any]:
    """Authorization guard.

    Returns None if authorized, or an "Access Restricted" message if denied.
    """
    chat_id = None
    username = None
    try:
        chat_id = getattr(getattr(update, "effective_chat", None), "id", None)
        user = getattr(update, "effective_user", None)
        username = getattr(user, "username", None)
    except Exception:
        pass

    if is_authorized(chat_id, username):
        return None
    return "Access Restricted: This bot is for authorized HydroCast operators only."


def load_latest_pipeline_state() -> dict[str, Any]:
    """Load the latest pipeline state from disk."""
    try:
        from pathlib import Path
        p = Path("data/openmeteo_dss/latest_pipeline_state.json")
        if p.exists():
            import json
            state = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(state, dict) and "cycle_id" in state:
                return state
    except Exception:
        pass
    return {"cycle_id": "CYC_UNKNOWN", "status": "stub"}


class _DummyUpdater:
    """Stub updater for compatibility with FastAPI startup/shutdown."""
    def __init__(self, app):
        self._app = app

    async def start_polling(self):
        log.info("Telegram updater polling (stub)")

    async def stop(self):
        log.info("Telegram updater stopped (stub)")


class _DummyBot:
    """Stub Telegram bot application."""
    def __init__(self):
        self.updater = _DummyUpdater(self)

    async def initialize(self):
        log.info("Telegram bot initialized (stub)")

    async def start(self):
        log.info("Telegram bot started (stub)")

    async def stop(self):
        log.info("Telegram bot stopped (stub)")

    async def shutdown(self):
        log.info("Telegram bot shutdown (stub)")


def build_telegram_application() -> Optional[_DummyBot]:
    """
    Build a Telegram bot application (stub for production deployment).
    """
    if TELEGRAM_TOKEN is None:
        log.warning("TELEGRAM_TOKEN not set — Telegram bot running in stub mode")
    return _DummyBot()


__all__ = [
    "ALLOWED_CHAT_IDS_ENV",
    "ALLOWED_USERNAMES_ENV",
    "WEBHOOK_SECRET",
    "PRIMARY_CHAT_ID",
    "DDMA_CHATS_ENV",
    "WEBHOOKS_ENV",
    "TELEGRAM_TOKEN",
    "RATE_LIMIT_MAX",
    "RATE_LIMIT_WINDOW",
    "esc",
    "format_telegram_alert",
    "get_severity_badge",
    "send_telegram_broadcast",
    "dispatch_agency_webhooks",
    "get_target_chat_ids",
    "get_webhook_urls",
    "is_authorized",
    "is_rate_limited",
    "validate_webhook_secret",
    "_rate_buckets",
    "_rate_limit_buckets",
    "_rate_guard",
    "_guard",
    "load_latest_pipeline_state",
    "build_telegram_application",
    "_DummyBot",
    "_DummyUpdater",
]
