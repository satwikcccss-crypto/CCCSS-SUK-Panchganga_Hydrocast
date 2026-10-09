"""
src/alerts/telegram_bot.py
==========================
Production Telegram Bot & Disaster Management Dispatcher for HydroCast.
Dispatches CWC threshold breach bulletins to District Disaster Management
Authority (DDMA), District Collectorate, and emergency response teams.
"""

import asyncio
import functools
import hmac
import html
import json
import logging
import os
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

import requests
import asyncpg

log = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
PRIMARY_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
DDMA_CHATS_ENV = os.getenv("DDMA_TELEGRAM_CHATS", "")
WEBHOOKS_ENV = os.getenv("DISASTER_MANAGEMENT_WEBHOOKS", "")

# ── Security configuration ────────────────────────────────────────────────────
# Comma-separated chat IDs / user IDs permitted to query the bot.
ALLOWED_CHAT_IDS_ENV = os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "")
# Comma-separated @usernames permitted to query the bot (alternative to IDs).
ALLOWED_USERNAMES_ENV = os.getenv("TELEGRAM_ALLOWED_USERNAMES", "")
# Secret token configured with setWebhook(); validated on any webhook ingress.
WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
# Per-principal command throttle: at most N commands per WINDOW seconds.
RATE_LIMIT_MAX = int(os.getenv("TELEGRAM_RATE_LIMIT_MAX", "20"))
RATE_LIMIT_WINDOW = int(os.getenv("TELEGRAM_RATE_LIMIT_WINDOW", "60"))


def get_target_chat_ids() -> List[str]:
    """Resolve all configured Telegram chat/channel IDs for emergency broadcast."""
    chats = []
    if PRIMARY_CHAT_ID:
        chats.append(PRIMARY_CHAT_ID.strip())
    if DDMA_CHATS_ENV:
        for c in DDMA_CHATS_ENV.split(","):
            c = c.strip()
            if c and c not in chats:
                chats.append(c)
    return chats


def get_webhook_urls() -> List[str]:
    """Resolve all external disaster management agency webhook endpoints."""
    if not WEBHOOKS_ENV:
        return []
    return [w.strip() for w in WEBHOOKS_ENV.split(",") if w.strip()]


def get_allowed_chat_ids() -> List[str]:
    """Resolve the chat/user ID allowlist for interactive bot access."""
    return [c.strip() for c in ALLOWED_CHAT_IDS_ENV.split(",") if c.strip()]


def get_allowed_usernames() -> List[str]:
    """Resolve the @username allowlist for interactive bot access."""
    return [u.strip().lstrip("@").lower() for u in ALLOWED_USERNAMES_ENV.split(",") if u.strip()]


def is_authorized(update: Any) -> bool:
    """
    Authorise an inbound Telegram interaction.

    Enforcement is fail-open ONLY while no allowlist is configured (to preserve
    backward compatibility). As soon as TELEGRAM_ALLOWED_CHAT_IDS or
    TELEGRAM_ALLOWED_USERNAMES is set, every other principal is denied.
    """
    allowed_chats = get_allowed_chat_ids()
    allowed_users = get_allowed_usernames()
    if not allowed_chats and not allowed_users:
        return True

    chat = getattr(update, "effective_chat", None)
    user = getattr(update, "effective_user", None)

    candidates = set()
    if chat is not None and chat.id is not None:
        candidates.add(str(chat.id))
    if user is not None:
        if user.id is not None:
            candidates.add(str(user.id))
        if user.username:
            candidates.add(user.username.lower())

    return any(c in allowed_chats for c in candidates) or any(
        c in allowed_users for c in candidates
    )


_rate_buckets: Dict[str, Deque[float]] = {}


def is_rate_limited(key: str) -> bool:
    """Sliding-window per-principal throttle. Records the hit when allowed."""
    if RATE_LIMIT_MAX <= 0 or RATE_LIMIT_WINDOW <= 0:
        return False
    now = time.monotonic()
    bucket = _rate_buckets.setdefault(key, deque())
    while bucket and now - bucket[0] > RATE_LIMIT_WINDOW:
        bucket.popleft()
    if len(bucket) >= RATE_LIMIT_MAX:
        return True
    bucket.append(now)
    return False


def validate_webhook_secret(header_value: Optional[str]) -> bool:
    """
    Constant-time validation of the X-Telegram-Bot-Api-Secret-Token header.
    Returns True when no secret is configured (webhook auth disabled).
    """
    if not WEBHOOK_SECRET:
        return True
    if not header_value:
        return False
    return hmac.compare_digest(header_value, WEBHOOK_SECRET)


def esc(value: Any) -> str:
    """Escape untrusted values before embedding them in Telegram HTML messages."""
    return html.escape("" if value is None else str(value), quote=False)


def _get_principal_key(update: Any) -> str:
    """Extract a consistent identifier string for rate-limiting and logging."""
    chat = getattr(update, "effective_chat", None)
    user = getattr(update, "effective_user", None)
    return (
        str(chat.id)
        if chat is not None and chat.id is not None
        else (str(user.id) if user is not None and user.id is not None else "anonymous")
    )


def _rate_guard(update: Any) -> Optional[str]:
    """Return an HTML denial message if the rate limit is exceeded."""
    key = _get_principal_key(update)
    if is_rate_limited(key):
        log.warning("Rate limit exceeded for Telegram principal %s", key)
        return (
            f"⏳ <b>Rate limit exceeded.</b> Maximum {RATE_LIMIT_MAX} commands per "
            f"{RATE_LIMIT_WINDOW}s. Please retry shortly."
        )
    return None


def _guard(update: Any) -> Optional[str]:
    """Return an HTML denial message if the interaction is not permitted for official commands."""
    key = _get_principal_key(update)
    if not is_authorized(update):
        log.warning("Rejected unauthorized official Telegram interaction from %s", key)
        return (
            "⛔ <b>Access Restricted.</b>\n"
            "This command contains sensitive hydrologic / diagnostic data restricted to "
            "authorised CCCSS, SUK, WRD, and DDMA personnel.\n\n"
            "Public users can access river stages with <code>/stage</code>, active alerts with "
            "<code>/alerts</code>, and bulletins with <code>/bulletin</code>.\n"
            "Send <code>/id</code> to your supervisor/administrator to request official access."
        )
    return _rate_guard(update)


def public_command(func):
    """Decorator permitting all users, protected by sliding-window rate limiting."""

    @functools.wraps(func)
    async def wrapper(update, context):
        denial = _rate_guard(update)
        if denial:
            try:
                await update.message.reply_text(denial, parse_mode="HTML")
            except Exception:
                pass
            return
        return await func(update, context)

    return wrapper


def official_only(func):
    """Decorator enforcing allowlist AND rate limiting for sensitive official commands."""

    @functools.wraps(func)
    async def wrapper(update, context):
        denial = _guard(update)
        if denial:
            try:
                await update.message.reply_text(denial, parse_mode="HTML")
            except Exception:
                pass
            return
        return await func(update, context)

    return wrapper


authorized_only = official_only  # Backwards compatibility alias


def get_severity_badge(level: str) -> str:
    """Return colored emoji badge for CWC threshold tier or DB alert type."""
    return {
        "ALERT": "🟡 [ALERT / WATCH]",
        "WATCH": "🟡 [ALERT / WATCH]",
        "WARNING": "🟠 [WARNING / ADVISORY]",
        "DANGER": "🔴 [DANGER / FLOOD EMERGENCY]",
        "EMERGENCY": "🔴 [DANGER / FLOOD EMERGENCY]",
        "HFL_EXCEEDED": "🚨 [EXTREME FLOOD / HFL EXCEEDED]",
    }.get(level.upper(), "⚪ [INFORMATION]")


def format_telegram_alert(
    site_id: str,
    site_name: str,
    level: str,
    peak_stage: float,
    current_stage: float,
    warning_stage: float,
    danger_stage: float,
    hfl_stage: float,
    arrival_str: str,
    cycle_id: str,
    action: str,
) -> str:
    """
    Format official Central Water Commission / DDMA flood bulletin card.
    Uses HTML formatting supported by Telegram Bot API.
    """
    badge = get_severity_badge(level)
    margin_to_danger = danger_stage - peak_stage
    margin_str = (
        f"<b>Exceeds Danger by:</b> +{abs(margin_to_danger):.2f} m"
        if margin_to_danger <= 0
        else f"<b>Buffer to Danger:</b> {margin_to_danger:.2f} m"
    )

    card = (
        f"🌊 <b>HYDROCAST FLOOD BULLETIN</b> 🌊\n"
        f"<b>Authority:</b> Center for Climate Change and Sustainability Studies, Shivaji University Kolhapur\n"
        f"<b>Classification:</b> {badge}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 <b>Site:</b> {esc(site_name)} (<code>{esc(site_id)}</code>)\n"
        f"📊 <b>Projected Peak Stage:</b> <code>{peak_stage:.2f} m MSL</code>\n"
        f"⏱ <b>Peak Arrival Time:</b> {esc(arrival_str)}\n"
        f"📏 <b>Current Water Level:</b> {current_stage:.2f} m MSL\n"
        f"{margin_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏛 <b>WRD Reference Datums:</b>\n"
        f"  • Warning Mark: {warning_stage:.2f} m\n"
        f"  • Danger Mark: {danger_stage:.2f} m\n"
        f"  • Historical Peak (HFL): {hfl_stage:.2f} m\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🚨 <b>RECOMMENDED ACTION:</b>\n"
        f"<i>{esc(action)}</i>\n\n"
        f"🔄 <i>Cycle: {esc(cycle_id)} | Issued: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</i>"
    )
    return card


def send_telegram_broadcast(text: str, parse_mode: str = "HTML") -> int:
    """
    Broadcast a message to all configured Telegram channels and DDMA groups.
    Returns count of successful deliveries.
    """
    chats = get_target_chat_ids()
    if not TELEGRAM_TOKEN or not chats:
        log.debug("Telegram credentials or chats not configured — skipping broadcast")
        return 0

    success_count = 0
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    for chat_id in chats:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }
        try:
            r = requests.post(url, json=payload, timeout=10)
            if r.status_code == 200:
                success_count += 1
                log.info("Alert dispatched to Telegram chat %s", chat_id)
            else:
                log.warning("Telegram dispatch to %s returned %d: %s", chat_id, r.status_code, r.text)
        except Exception as e:
            log.error("Failed to send Telegram message to %s: %s", chat_id, e)

    return success_count


def dispatch_agency_webhooks(alert_payload: Dict[str, Any]) -> int:
    """
    Post alert payload to external disaster management webhooks (e.g. state SDRF / NDRF portal).
    """
    webhooks = get_webhook_urls()
    if not webhooks:
        return 0

    success = 0
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "HydroCast-DDMA-Dispatcher/2.0",
        "X-Hydrocast-Event": "flood_alert",
    }

    for url in webhooks:
        try:
            r = requests.post(url, json=alert_payload, headers=headers, timeout=8)
            if 200 <= r.status_code < 300:
                success += 1
                log.info("Dispatched alert webhook to %s", url)
            else:
                log.warning("Webhook %s returned status %d", url, r.status_code)
        except Exception as e:
            log.error("Failed to send webhook to %s: %s", url, e)

    return success


def load_latest_pipeline_state() -> Optional[Dict[str, Any]]:
    """Load latest pipeline state from frontend or data directory as fallback."""
    root = Path(__file__).resolve().parent.parent.parent
    candidates = [
        root / "frontend" / "public" / "data" / "latest_pipeline_state.json",
        root / "data" / "openmeteo_dss" / "latest_pipeline_state.json",
    ]
    for p in candidates:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                log.warning("Could not parse %s: %s", p, e)
    return None


BOT_DESCRIPTION = (
    "HydroCast is an automated flood early-warning service for the Panchganga "
    "river basin around Kolhapur, Maharashtra. Developed by the Center for "
    "Climate Change and Sustainability Studies (CCCSS), Shivaji University Kolhapur.\n\n"
    "• Public users: check river stages (/stage), active alerts (/alerts), and official bulletins (/bulletin).\n"
    "• Control room officials (CCCSS, SUK, WRD, DDMA): authorized access to diagnostics (/status), "
    "catchment rainfall (/rainfall), calibration parameters (/curvenumbers), and pipeline logs (/logs)."
)

BOT_SHORT_DESCRIPTION = (
    "Panchganga flood early warnings by CCCSS Shivaji University for public & DDMA/WRD officials."
)

PUBLIC_BOT_COMMANDS = [
    ("start", "Welcome & command overview"),
    ("stage", "Current river levels & bridge stages"),
    ("alerts", "Active DDMA flood warning alerts"),
    ("bulletin", "Latest CWC / DDMA flood bulletin"),
    ("id", "Show your Telegram ID (for official access)"),
    ("help", "Public command guide & help"),
]

OFFICIAL_BOT_COMMANDS = [
    ("status", "[Official] System diagnostics & cycle health"),
    ("rainfall", "[Official] Catchment rainfall across 18 stations"),
    ("curvenumbers", "[Official] Calibrated SCS-CN & Muskingum parameters"),
    ("logs", "[Official] Recent pipeline execution logs"),
]

BOT_COMMANDS = PUBLIC_BOT_COMMANDS + OFFICIAL_BOT_COMMANDS


def configure_bot_profile() -> bool:
    """
    Publish the bot's public profile to Telegram: the description shown before a
    user presses Start, the short profile blurb, and the public command menu.
    Idempotent — safe to call on every startup.
    """
    if not TELEGRAM_TOKEN:
        return False

    base = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
    ok = True
    calls = (
        ("setMyDescription", {"description": BOT_DESCRIPTION[:512]}),
        ("setMyShortDescription", {"short_description": BOT_SHORT_DESCRIPTION[:120]}),
        (
            "setMyCommands",
            {"commands": [{"command": c, "description": d} for c, d in PUBLIC_BOT_COMMANDS]},
        ),
    )
    for method, payload in calls:
        try:
            r = requests.post(f"{base}/{method}", json=payload, timeout=10)
            if r.status_code != 200:
                ok = False
                log.warning("Telegram %s failed (%d): %s", method, r.status_code, r.text)
        except Exception as e:
            ok = False
            log.warning("Telegram %s request error: %s", method, e)

    log.info("Telegram bot profile configured: %s", ok)
    return ok


def build_telegram_application():
    """
    Create a python-telegram-bot Application with interactive commands.
    Tiered RBAC:
      - Public commands (/start, /help, /stage, /alerts, /bulletin, /id) are open to all.
      - Sensitive commands (/status, /rainfall, /curvenumbers, /logs) require allowlist authorization.
    """
    try:
        from telegram import Update
        from telegram.ext import Application, CommandHandler, ContextTypes
    except ImportError:
        log.warning("python-telegram-bot not available for interactive bot service")
        return None

    if not TELEGRAM_TOKEN:
        return None

    if not get_allowed_chat_ids() and not get_allowed_usernames():
        log.warning(
            "TELEGRAM_ALLOWED_CHAT_IDS / TELEGRAM_ALLOWED_USERNAMES are not set — "
            "official commands are OPEN to any Telegram user. Configure an allowlist "
            "in production."
        )

    # Publish public profile and public command menu
    try:
        configure_bot_profile()
    except Exception as e:
        log.warning("Bot profile configuration skipped: %s", e)

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    async def get_db_pool():
        from src.api.main import get_pool
        return await get_pool()

    # ── PUBLIC COMMANDS ─────────────────────────────────────────────────────────

    @public_command
    async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🌊 <b>HydroCast Flood Intelligence Bot</b>\n"
            "<i>Automated Panchganga Basin Flood Early Warning</i>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "Issued by the Center for Climate Change and Sustainability Studies (CCCSS), "
            "Shivaji University Kolhapur, for DDMA, WRD, and the general public.\n\n"
            "<b>📢 Public Commands (Open Access):</b>\n"
            "• /stage - Current water levels and peak stages at Shivaji &amp; Rajaram bridges\n"
            "• /alerts - Active warning and danger flood alerts\n"
            "• /bulletin - Latest official CWC / DDMA flood bulletin\n"
            "• /id - Show your Telegram Chat/User ID\n\n"
            "<b>🔒 Official Commands (CCCSS / SUK / WRD / DDMA):</b>\n"
            "• /status - System health, engine diagnostics &amp; cycle timings\n"
            "• /rainfall - Catchment precipitation hyetographs across 18 stations\n"
            "• /curvenumbers - Calibrated SCS-CN &amp; Muskingum routing parameters\n"
            "• /logs - Recent pipeline diagnostic logs &amp; warnings\n\n"
            "<i>Data source: CWC / WRD gauge datums blended with Open-Meteo NWP "
            "and IoT (ThingSpeak) telemetry. Decision-support aid.</i>",
            parse_mode="HTML",
        )

    @public_command
    async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Reveal caller's own IDs (used to request allowlist access)."""
        chat = update.effective_chat
        user = update.effective_user
        parts = [f"<b>Chat ID:</b> <code>{chat.id}</code>"]
        if user:
            parts.append(f"<b>User ID:</b> <code>{user.id}</code>")
            if user.username:
                parts.append(f"<b>Username:</b> @{esc(user.username)}")
        parts.append(
            "\n<i>Share this ID with your CCCSS / WRD administrator to request "
            "access to sensitive official commands.</i>"
        )
        await update.message.reply_text("\n".join(parts), parse_mode="HTML")

    @public_command
    async def stage_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            # Try DB pool first
            pool = None
            try:
                pool = await get_db_pool()
            except Exception:
                pool = None

            rows = []
            if pool:
                async with pool.acquire() as conn:
                    rows = await conn.fetch(
                        "SELECT * FROM v_active_alerts_enriched ORDER BY arrival_time ASC NULLS LAST LIMIT 5"
                    )

            if rows:
                msg = "📊 <b>Current Bridge Stages</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
                for r in rows:
                    msg += f"📍 <b>{esc(r['site_name'])}</b>\n"
                    msg += f"Current Level: <code>{r['discharge_m3s']:.2f} m MSL</code>\n"
                    msg += f"Projected Peak: <code>{r['peak_stage']:.2f} m</code> at {esc(r['arrival_time'].strftime('%m-%d %H:%M') if r['arrival_time'] else 'N/A')}\n\n"
                await update.message.reply_text(msg, parse_mode="HTML")
                return

            # Graceful fallback: load from latest_pipeline_state.json
            state = load_latest_pipeline_state()
            if state:
                msg = "📊 <b>Current Bridge Stages (Live Forecast)</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
                for key in ("bridgeShivaji", "bridgeRajaram"):
                    b = state.get(key, {})
                    site = b.get("site", {})
                    live = b.get("live_sensor", {})
                    peak = b.get("peak_arrival", {})
                    site_name = site.get("name") or key
                    curr_stage = live.get("stage_m") or 0.0
                    peak_stage = peak.get("peak_stage_m") or 0.0
                    arrival = peak.get("arrival_time") or "N/A"
                    warning = site.get("warning_stage_m", 535.84)
                    danger = site.get("danger_stage_m", 537.36)

                    msg += f"📍 <b>{esc(site_name)}</b>\n"
                    msg += f"Current Level: <code>{curr_stage:.2f} m MSL</code>\n"
                    msg += f"Projected Peak: <code>{peak_stage:.2f} m MSL</code>\n"
                    msg += f"Peak Arrival: {esc(arrival)}\n"
                    msg += f"Thresholds: Warning {warning:.2f}m | Danger {danger:.2f}m\n\n"
                await update.message.reply_text(msg, parse_mode="HTML")
                return

            await update.message.reply_text("ℹ️ No active stage forecasts currently available.", parse_mode="HTML")
        except Exception as e:
            log.error(f"Telegram /stage error: {e}")
            await update.message.reply_text("⚠️ Error fetching stage data.", parse_mode="HTML")

    @public_command
    async def alerts_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            pool = None
            try:
                pool = await get_db_pool()
            except Exception:
                pool = None

            rows = []
            if pool:
                async with pool.acquire() as conn:
                    rows = await conn.fetch(
                        "SELECT * FROM v_active_alerts_enriched WHERE alert_type IN ('watch', 'warning', 'emergency')"
                    )

            if rows:
                msg = "🚨 <b>Active Flood Alerts</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
                for r in rows:
                    badge = get_severity_badge(r["alert_type"])
                    msg += f"{badge} <b>{esc(r['site_name'])}</b>\n"
                    msg += f"<i>{esc(r['recommended_action'])}</i>\n\n"
                await update.message.reply_text(msg, parse_mode="HTML")
                return

            # Check pipeline state
            state = load_latest_pipeline_state()
            summary = state.get("summary", {}) if state else {}
            status = summary.get("status", "NORMAL")

            if status in ("WARNING", "DANGER", "EMERGENCY"):
                msg = f"🚨 <b>Active Flood Alert: {status}</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
                msg += f"Action: {esc(summary.get('action', 'Monitor water levels closely.'))}\n"
                await update.message.reply_text(msg, parse_mode="HTML")
            else:
                await update.message.reply_text("✅ <b>No active flood alerts.</b> River water levels are within normal limits.", parse_mode="HTML")
        except Exception as e:
            log.error(f"Telegram /alerts error: {e}")
            await update.message.reply_text("⚠️ Error fetching alerts.", parse_mode="HTML")

    @public_command
    async def bulletin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            pool = None
            try:
                pool = await get_db_pool()
            except Exception:
                pool = None

            if pool:
                async with pool.acquire() as conn:
                    rows = await conn.fetch(
                        "SELECT * FROM v_active_alerts_enriched ORDER BY alert_type DESC LIMIT 1"
                    )
                if rows:
                    r = rows[0]
                    card = format_telegram_alert(
                        site_id=r["site_id"],
                        site_name=r["site_name"],
                        level=r["alert_type"],
                        peak_stage=r["peak_stage"] or 0.0,
                        current_stage=r["discharge_m3s"] or 0.0,
                        warning_stage=r["warning_stage_m"] or 0.0,
                        danger_stage=r["danger_stage_m"] or 0.0,
                        hfl_stage=r["hfl_m"] or 0.0,
                        arrival_str=r["arrival_time"].strftime('%Y-%m-%d %H:%M UTC') if r["arrival_time"] else "N/A",
                        cycle_id=r["run_id"],
                        action=r["recommended_action"] or "Monitor closely.",
                    )
                    await update.message.reply_text(card, parse_mode="HTML")
                    return

            # Fallback to pipeline state
            state = load_latest_pipeline_state()
            if state:
                b = state.get("bridgeShivaji", {})
                site = b.get("site", {})
                live = b.get("live_sensor", {})
                peak = b.get("peak_arrival", {})
                card = format_telegram_alert(
                    site_id=site.get("id", "SHIVAJI_BRIDGE"),
                    site_name=site.get("name", "Shivaji Bridge (Kolhapur)"),
                    level="INFO",
                    peak_stage=peak.get("peak_stage_m") or 0.0,
                    current_stage=live.get("stage_m") or 0.0,
                    warning_stage=site.get("warning_stage_m", 535.84),
                    danger_stage=site.get("danger_stage_m", 537.36),
                    hfl_stage=site.get("hfl_stage_m", 545.33),
                    arrival_str=str(peak.get("arrival_time", "N/A")),
                    cycle_id=state.get("cycle_id", "LIVE"),
                    action="Normal baseflow conditions. Routine monitoring.",
                )
                await update.message.reply_text(card, parse_mode="HTML")
                return

            await update.message.reply_text("ℹ️ No bulletin available.", parse_mode="HTML")
        except Exception as e:
            log.error(f"Telegram /bulletin error: {e}")
            await update.message.reply_text("⚠️ Error generating bulletin.", parse_mode="HTML")

    # ── OFFICIAL COMMANDS (Restricted to CCCSS / SUK / WRD / DDMA) ─────────────

    @official_only
    async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        state = load_latest_pipeline_state()
        pipe = state.get("pipeline", {}) if state else {}
        comps = pipe.get("components", {})
        steps = pipe.get("steps", {})

        msg = "🔧 <b>HydroCast System Diagnostics [OFFICIAL]</b>\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"Server Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n"
        if state:
            msg += f"Active Cycle: <code>{esc(state.get('cycle_id', 'N/A'))}</code>\n"

        msg += "\n<b>Components:</b>\n"
        msg += f"• Open-Meteo NWP: {esc(comps.get('open_meteo', 'ONLINE (18 STATIONS)'))}\n"
        msg += f"• Stage Rating: {esc(comps.get('stage_rating', 'ONLINE'))}\n"
        msg += f"• HEC-HMS Engine: {esc(comps.get('hec_hms', 'CALIBRATED_RJKT'))}\n"
        msg += f"• ML Recalibration: {esc(comps.get('ml_calibration', 'BASELINE'))}\n"
        msg += f"• Database: {esc(comps.get('database', 'CONNECTED'))}\n"

        if steps:
            msg += "\n<b>Step Execution Timings:</b>\n"
            for step_k, sec in list(steps.items())[:5]:
                msg += f"  • {esc(step_k[:25])}: {sec:.1f}s\n"

        await update.message.reply_text(msg, parse_mode="HTML")

    @official_only
    async def rainfall_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        state = load_latest_pipeline_state()
        if not state:
            await update.message.reply_text("⚠️ No pipeline rainfall data available.", parse_mode="HTML")
            return

        stations = state.get("stations", [])
        if not stations:
            await update.message.reply_text("⚠️ No catchment station rainfall records found.", parse_mode="HTML")
            return

        # Sort stations by cumulative 90-hour rainfall descending
        sorted_st = sorted(stations, key=lambda s: float(s.get("cumulative_90h_mm", 0.0)), reverse=True)
        top5 = sorted_st[:5]
        mean_90h = sum(float(s.get("cumulative_90h_mm", 0.0)) for s in stations) / len(stations)

        msg = "🌧 <b>Panchganga Catchment Rainfall [OFFICIAL]</b>\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"Active Gaging Stations: <b>{len(stations)} stations</b>\n"
        msg += f"Basin Mean 90h Rainfall: <b>{mean_90h:.1f} mm</b>\n\n"
        msg += "<b>Top 5 Heaviest Rainfall Stations:</b>\n"
        for s in top5:
            st_name = s.get("station_name", s.get("station_id", "Unknown"))
            sub_id = s.get("subbasin_id", "N/A")
            elev = s.get("elevation", "")
            rain_mm = float(s.get("cumulative_90h_mm", 0.0))
            msg += f"• <b>{esc(st_name)}</b> ({esc(sub_id)}, {esc(elev)}): <code>{rain_mm:.1f} mm</code>\n"

        subbasins = state.get("subbasins", [])
        if subbasins:
            msg += f"\nMonitored Subbasins: {len(subbasins)} units (S1–S{len(subbasins)})"

        await update.message.reply_text(msg, parse_mode="HTML")

    @official_only
    async def curvenumbers_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        from src.hydrology.ml_calibration import calibrator

        cal_state = calibrator.state
        alpha_k = cal_state.get("alpha_k", 1.0)
        alpha_lag = cal_state.get("alpha_lag", 1.0)
        delta_cn = cal_state.get("delta_cn", 0.0)
        muskingum_x = cal_state.get("muskingum_x", 0.2)
        timing_offset = cal_state.get("timing_offset_hours", 0.0)
        stage_err = cal_state.get("stage_discrepancy_m", 0.0)
        peak_q_err = cal_state.get("peak_discharge_error_m3s", 0.0)
        conf = cal_state.get("confidence_pct", 95.0)
        is_tuned = cal_state.get("is_recalibrated", False)

        msg = "📐 <b>Hydrologic Calibration Parameters [OFFICIAL]</b>\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"Status: <b>{'TUNED (Levenberg–Marquardt)' if is_tuned else 'BASELINE (Physics Prior)'}</b>\n"
        msg += f"Confidence: <b>{conf:.1f}%</b>\n\n"
        msg += f"• Curve Number Offset (ΔCN): <code>{delta_cn:+.2f}</code>\n"
        msg += f"• Routing Lag Scale (α_lag): <code>{alpha_lag:.3f}</code>\n"
        msg += f"• Muskingum K Scale (α_K): <code>{alpha_k:.3f}</code>\n"
        msg += f"• Muskingum Weighting (X): <code>{muskingum_x:.3f}</code>\n\n"
        msg += "<b>Real-Time Feedback Metrics:</b>\n"
        msg += f"• Wave Timing Offset (Δt): <code>{timing_offset:+.1f} h</code>\n"
        msg += f"• Signed Stage Error (Δh): <code>{stage_err:+.3f} m</code>\n"
        msg += f"• Peak Discharge Error (ΔQ_peak): <code>{peak_q_err:+.1f} m³/s</code>\n"

        active_subs = cal_state.get("active_sub_models", {})
        if active_subs:
            msg += "\n<b>Active Subbasin Curve Numbers:</b>\n"
            for sid in sorted(active_subs.keys())[:5]:
                cn_val = active_subs[sid].get("cn", 0.0)
                msg += f"  • {sid}: CN = {cn_val:.2f}\n"

        await update.message.reply_text(msg, parse_mode="HTML")

    @official_only
    async def logs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        state = load_latest_pipeline_state()
        if not state or "logs" not in state:
            await update.message.reply_text("⚠️ No pipeline logs available.", parse_mode="HTML")
            return

        logs = state.get("logs", [])
        if not logs:
            await update.message.reply_text("ℹ️ Log buffer is empty.", parse_mode="HTML")
            return

        msg = "📜 <b>Recent Pipeline Execution Logs [OFFICIAL]</b>\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━\n"
        for item in logs[-8:]:
            level = item.get("level", "INFO")
            timestamp = item.get("timestamp", "")
            time_short = timestamp.split("T")[-1][:8] if "T" in timestamp else timestamp
            message = item.get("message", "")
            icon = "🔴" if level in ("ERROR", "CRITICAL") else "🟡" if level == "WARN" else "🟢"
            msg += f"{icon} <code>{esc(time_short)}</code> [{esc(level)}] {esc(message[:60])}\n"

        await update.message.reply_text(msg, parse_mode="HTML")

    # ── HANDLER REGISTRATIONS ──────────────────────────────────────────────────
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", start_cmd))
    app.add_handler(CommandHandler("stage", stage_cmd))
    app.add_handler(CommandHandler("alerts", alerts_cmd))
    app.add_handler(CommandHandler("bulletin", bulletin_cmd))
    app.add_handler(CommandHandler("id", id_cmd))

    # Official-only command handlers
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("rainfall", rainfall_cmd))
    app.add_handler(CommandHandler("curvenumbers", curvenumbers_cmd))
    app.add_handler(CommandHandler("calibration", curvenumbers_cmd))
    app.add_handler(CommandHandler("logs", logs_cmd))

    return app
