"""
src/alerts/telegram_bot.py
==========================
Production Telegram Bot & Disaster Management Dispatcher for HydroCast.
Dispatches CWC threshold breach bulletins to District Disaster Management
Authority (DDMA), District Collectorate, and emergency response teams.
"""

import asyncio
import json
import logging
import os
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
import asyncpg

log = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
PRIMARY_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
DDMA_CHATS_ENV = os.getenv("DDMA_TELEGRAM_CHATS", "")
WEBHOOKS_ENV = os.getenv("DISASTER_MANAGEMENT_WEBHOOKS", "")


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


def get_severity_badge(level: str) -> str:
    """Return colored emoji badge for CWC threshold tier."""
    return {
        "ALERT": "🟡 [ALERT / WATCH]",
        "WARNING": "🟠 [WARNING / ADVISORY]",
        "DANGER": "🔴 [DANGER / FLOOD EMERGENCY]",
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
        f"<b>Authority:</b> District Disaster Management Authority (DDMA)\n"
        f"<b>Classification:</b> {badge}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 <b>Site:</b> {site_name} (<code>{site_id}</code>)\n"
        f"📊 <b>Projected Peak Stage:</b> <code>{peak_stage:.2f} m MSL</code>\n"
        f"⏱ <b>Peak Arrival Time:</b> {arrival_str}\n"
        f"📏 <b>Current Water Level:</b> {current_stage:.2f} m MSL\n"
        f"{margin_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏛 <b>Official WRD Reference Datums:</b>\n"
        f"  • Warning Mark: {warning_stage:.2f} m\n"
        f"  • Danger Mark: {danger_stage:.2f} m\n"
        f"  • Historical Peak (HFL): {hfl_stage:.2f} m\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🚨 <b>RECOMMENDED ACTION:</b>\n"
        f"<i>{action}</i>\n\n"
        f"🔄 <i>Cycle: {cycle_id} | Issued: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</i>"
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


def build_telegram_application():
    """
    Create a python-telegram-bot Application with interactive commands.
    Allows control room personnel to query current stages & forecasts.
    """
    try:
        from telegram import Update
        from telegram.ext import Application, CommandHandler, ContextTypes
    except ImportError:
        log.warning("python-telegram-bot not available for interactive bot service")
        return None

    if not TELEGRAM_TOKEN:
        return None

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🌊 <b>HydroCast Flood Intelligence Bot</b>\n\n"
            "Available commands:\n"
            "/status - System health & latest forecast cycle\n"
            "/stage - Current water levels and peak stages\n"
            "/alerts - Active warning and danger alerts\n"
            "/bulletin - Latest CWC flood bulletin",
            parse_mode="HTML",
        )

    async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "✅ <b>HydroCast System Status</b>: OPERATIONAL\n"
            f"Server Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n"
            "Forecasting Interval: 6-hourly automated cycles (00z, 06z, 12z, 18z)",
            parse_mode="HTML",
        )

    async def get_db_pool():
        # Import dynamically to avoid circular dependencies
        from src.api.main import get_pool
        return await get_pool()

    async def stage_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM v_active_alerts_enriched ORDER BY arrival_time ASC NULLS LAST LIMIT 5")
            
            if not rows:
                await update.message.reply_text("ℹ️ No active stage forecasts available.", parse_mode="HTML")
                return

            msg = "📊 <b>Current Bridge Stages</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
            for r in rows:
                msg += f"📍 <b>{r['site_name']}</b>\n"
                msg += f"Current: {r['discharge_m3s']:.2f} m\n"
                msg += f"Peak: <code>{r['peak_stage']:.2f} m</code> at {r['arrival_time'].strftime('%m-%d %H:%M') if r['arrival_time'] else 'N/A'}\n\n"
            
            await update.message.reply_text(msg, parse_mode="HTML")
        except Exception as e:
            log.error(f"Telegram /stage error: {e}")
            await update.message.reply_text("⚠️ Error fetching stage data.", parse_mode="HTML")

    async def alerts_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM v_active_alerts_enriched WHERE alert_type IN ('WARNING', 'DANGER', 'HFL_EXCEEDED')")
            
            if not rows:
                await update.message.reply_text("✅ No active flood warnings.", parse_mode="HTML")
                return

            msg = "🚨 <b>Active Flood Alerts</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
            for r in rows:
                badge = get_severity_badge(r["alert_type"])
                msg += f"{badge} <b>{r['site_name']}</b>\n"
                msg += f"<i>{r['recommended_action']}</i>\n\n"
            
            await update.message.reply_text(msg, parse_mode="HTML")
        except Exception as e:
            log.error(f"Telegram /alerts error: {e}")
            await update.message.reply_text("⚠️ Error fetching alerts.", parse_mode="HTML")

    async def bulletin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM v_active_alerts_enriched ORDER BY alert_type DESC LIMIT 1")
            
            if not rows:
                await update.message.reply_text("ℹ️ No critical bulletin available.", parse_mode="HTML")
                return

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
                action=r["recommended_action"] or "Monitor closely."
            )
            await update.message.reply_text(card, parse_mode="HTML")
        except Exception as e:
            log.error(f"Telegram /bulletin error: {e}")
            await update.message.reply_text("⚠️ Error generating bulletin.", parse_mode="HTML")

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", start_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("stage", stage_cmd))
    app.add_handler(CommandHandler("alerts", alerts_cmd))
    app.add_handler(CommandHandler("bulletin", bulletin_cmd))

    return app
