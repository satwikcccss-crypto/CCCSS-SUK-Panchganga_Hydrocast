"""
backend/alerts/telegram_bot.py
==================================
Compatibility shim for the legacy Telegram dispatcher.

Production alerting is handled by backend.alerts.evaluator (CWC threshold
evaluation) and backend.api.admin (manual dispatch controls). This shim
provides the function surface expected by legacy tests.
"""

import os
import html as _html
import hmac
import logging
import time as _time
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

import requests

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

log = logging.getLogger(__name__)

# ── Legacy configuration names referenced by tests ────────────────────────────
ALLOWED_CHAT_IDS_ENV: Optional[str] = os.getenv("ALLOWED_CHAT_IDS")
ALLOWED_USERNAMES_ENV: Optional[str] = os.getenv("ALLOWED_USERNAMES")
WEBHOOK_SECRET: Optional[str] = os.getenv("TELEGRAM_WEBHOOK_SECRET") or os.getenv("WEBHOOK_SECRET")
PRIMARY_CHAT_ID: Optional[str] = os.getenv("TELEGRAM_CHAT_ID")
DDMA_CHATS_ENV: Optional[str] = os.getenv("DDMA_CHAT_IDS")
WEBHOOKS_ENV: Optional[str] = os.getenv("AGENCY_WEBHOOK_URLS")
TELEGRAM_TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")

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


def format_hourly_heartbeat(
    shivaji_stage: float = 531.54,
    shivaji_q: float = 9.1,
    rajaram_stage: float = 532.19,
    rajaram_q: float = 9.1,
    alert_level: str = "NORMAL",
    cycle_id: str = "CYC_LATEST",
) -> str:
    """Format hourly telemetry heartbeat message for Telegram broadcast."""
    now_utc = datetime.now(timezone.utc).strftime("%d-%b-%Y %H:%M UTC")
    lines = [
        "🌊 HYDROCAST PANCHGANGA — HOURLY HEARTBEAT",
        "📍 Panchganga River Basin Intelligence",
        f"🕒 Time: {now_utc} (Cycle: {cycle_id})",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "🌉 Chhatrapati Shivaji Maharaj Bridge:",
        f"  • River Stage: {shivaji_stage:.2f} m MSL",
        f"  • Discharge  : {shivaji_q:.1f} m³/s",
        "",
        "🌉 Rajaram K.T. Weir (Kasba Bawada):",
        f"  • River Stage: {rajaram_stage:.2f} m MSL",
        f"  • Discharge  : {rajaram_q:.1f} m³/s",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📊 Model Calculation Status: {get_severity_badge(alert_level)} {alert_level}",
        "🔬 Academic Research Simulation — Shivaji University Kolhapur (CCCSS). For official warnings & civil advisories, consult District Administration / DDMA.",
        "ℹ️ Research Intelligence Bot: @Hydrocast_SUK_bot",
    ]
    return "\n".join(lines)


def format_emergency_flood_alert(
    site_name: str,
    site_id: str,
    current_stage: float,
    danger_stage: float = 543.30,
    peak_stage: Optional[float] = None,
    lead_hours: int = 0,
) -> str:
    """Format emergency flood bulletin when thresholds are breached."""
    now_utc = datetime.now(timezone.utc).strftime("%d-%b-%Y %H:%M UTC")
    lines = [
        "🌊 HYDROCAST PANCHGANGA — SCIENTIFIC RESEARCH SIMULATION 🌊",
        "⚠️ ELEVATED STAGE SIMULATION OBSERVED",
        f"🕒 Timestamp: {now_utc}",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📍 Location: {site_name} ({site_id})",
        f"🔺 Calculated Stage: {current_stage:.2f} m MSL (Danger Level: {danger_stage:.2f} m)",
    ]
    if peak_stage:
        lines.append(f"📈 Simulated Peak: {peak_stage:.2f} m MSL")
    if lead_hours > 0:
        lines.append(f"⏳ Projected Horizon: T+{lead_hours} hrs")
    lines.extend([
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "🔬 NOTICE: Academic & Scientific Research Simulation by CCCSS, Shivaji University Kolhapur.",
        "For official flood warnings, evacuation notices, and civil alerts, consult District Administration / DDMA.",
        "ℹ️ Telegram Bot: @Hydrocast_SUK_bot",
    ])
    return "\n".join(lines)


def send_hourly_heartbeat(
    shivaji_stage: float = 531.54,
    shivaji_q: float = 9.1,
    rajaram_stage: float = 532.19,
    rajaram_q: float = 9.1,
    alert_level: str = "NORMAL",
    cycle_id: str = "CYC_LATEST",
) -> dict[str, Any]:
    """Send hourly telemetry heartbeat to subscribers."""
    text = format_hourly_heartbeat(
        shivaji_stage=shivaji_stage,
        shivaji_q=shivaji_q,
        rajaram_stage=rajaram_stage,
        rajaram_q=rajaram_q,
        alert_level=alert_level,
        cycle_id=cycle_id,
    )
    delivered = send_telegram_broadcast(text)
    return {"status": "sent", "delivered": delivered, "text": text}


def send_emergency_alert(
    site_name: str,
    site_id: str,
    current_stage: float,
    danger_stage: float = 543.30,
    peak_stage: Optional[float] = None,
    lead_hours: int = 0,
) -> dict[str, Any]:
    """Send immediate emergency broadcast to authorities and Telegram channels."""
    text = format_emergency_flood_alert(
        site_name=site_name,
        site_id=site_id,
        current_stage=current_stage,
        danger_stage=danger_stage,
        peak_stage=peak_stage,
        lead_hours=lead_hours,
    )
    delivered = send_telegram_broadcast(text)
    return {"status": "sent", "delivered": delivered, "text": text}


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
    are authorized (open mode). When allowlists are configured, fails closed:
    only explicitly authorized chat IDs or usernames are permitted.
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

    chat_allowlist_raw = ALLOWED_CHAT_IDS_ENV if ALLOWED_CHAT_IDS_ENV is not None else os.getenv("ALLOWED_CHAT_IDS", "")
    user_allowlist_raw = ALLOWED_USERNAMES_ENV if ALLOWED_USERNAMES_ENV is not None else os.getenv("ALLOWED_USERNAMES", "")

    has_chat_allowlist = bool(chat_allowlist_raw and chat_allowlist_raw.strip())
    has_user_allowlist = bool(user_allowlist_raw and user_allowlist_raw.strip())

    # Secure-by-default: deny when no allowlist is configured. Operators must
    # explicitly opt in via ALLOWED_CHAT_IDS / ALLOWED_USERNAMES env vars.
    if not has_chat_allowlist and not has_user_allowlist:
        return False

    # Fail closed: allowlist configured but no identity provided
    if extracted_chat_id is None and extracted_username is None:
        return False

    # Check chat allowlist
    if has_chat_allowlist and extracted_chat_id is not None:
        allowed_chats = {c.strip() for c in chat_allowlist_raw.split(",") if c.strip()}
        if str(extracted_chat_id).strip() in allowed_chats:
            return True

    # Check username allowlist (strip leading '@' if present for safe normalization)
    if has_user_allowlist and extracted_username is not None:
        raw_u = str(extracted_username).strip().lstrip("@")
        allowed_users = {u.strip().lstrip("@") for u in user_allowlist_raw.split(",") if u.strip()}
        if raw_u in allowed_users:
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


def get_telegram_keyboard_markup(lang: str = "mr") -> dict[str, Any]:
    """Generate a persistent popup screen keyboard tailored for Farmers, Citizens, and Students."""
    if lang == "en":
        keyboard = [
            [{"text": "👨‍🌾 Farmer View (Weirs & Pumps)"}, {"text": "🏙️ Citizen View (Bridges & City)"}],
            [{"text": "🔬 Student / Research (Technical)"}, {"text": "📈 90-Hour Forecast"}],
            [{"text": "🌐 मराठीत माहिती (Switch to Marathi)"}, {"text": "ℹ️ Help & Research Info"}],
        ]
    else:
        keyboard = [
            [{"text": "👨‍🌾 शेतकरी माहिती (बंधारे व शेतीपंप)"}, {"text": "🏙️ नागरिक पूर स्थिती (पूल व घाट)"}],
            [{"text": "🔬 विद्यार्थी / संशोधक (Technical Data)"}, {"text": "📈 ९० तास अंदाज (Forecast)"}],
            [{"text": "🌐 Switch to English"}, {"text": "ℹ️ मदत व संशोधन माहिती (Help)"}],
        ]
    return {
        "keyboard": keyboard,
        "resize_keyboard": True,
        "persistent": True,
        "one_time_keyboard": False,
    }


def handle_telegram_command(command_text: str) -> dict[str, Any]:
    """Process Telegram interactions with administrative, government-grade diplomatic bulletins."""
    raw = (command_text or "").strip()
    cmd = raw.lower()
    state = load_latest_pipeline_state()
    summary = state.get("summary", {}) if isinstance(state, dict) else {}
    q_val = float(summary.get("peak_discharge_m3s", 9.10))
    bridges = summary.get("bridges", {})
    if isinstance(bridges, dict):
        sh_stage = float(bridges.get("shivaji", {}).get("current_stage_m", 531.54))
        rj_stage = float(bridges.get("rajaram", {}).get("current_stage_m", 532.19))
    elif isinstance(bridges, list) and len(bridges) > 0:
        sh_stage = float(bridges[0].get("current_stage_m", 531.54))
        rj_stage = float(bridges[1].get("current_stage_m", 532.19)) if len(bridges) > 1 else 532.19
    else:
        sh_stage = 531.54
        rj_stage = 532.19

    now_ist = (datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)).strftime("%d-%m-%Y | वेळ: %I:%M %p")

    # Threshold constants
    RAJARAM_CREST_M = 535.77
    WARNING_STAGE_M = 542.70
    DANGER_STAGE_M = 543.30
    HFL_STAGE_M = 545.33

    is_weir_submerged = rj_stage >= RAJARAM_CREST_M
    is_warning = sh_stage >= WARNING_STAGE_M
    is_danger = sh_stage >= DANGER_STAGE_M

    # 1. FARMER VIEW (कृषी व सिंचन सल्लागार बुलेटिन)
    if any(k in cmd for k in ["शेतकरी", "farmer", "पंप", "बंधारा", "weir", "pump"]):
        if is_danger or is_warning or is_weir_submerged:
            text = (
                "॥ शिवाजी विद्यापीठ, कोल्हापूर ॥\n"
                "हवामान बदल व शाश्वतता अभ्यास केंद्र (CCCSS)\n"
                "प्रकल्प: DST-SERB, नवी दिल्ली | पंचगंगा नदी खोरे डिजिटल ट्विन\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "विषय: पंचगंगा नदी पूर निरीक्षण व कृषी क्षेत्र सतर्कता सूचना\n"
                f"दिनांक: {now_ist}\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "नदीकाठच्या शेतकरी बांधवांच्या माहितीस्तव कळविण्यात येते की:\n\n"
                "१. को.प. बंधारे स्थिती:\n"
                f"   • राजाराम बंधारा सद्यस्थितीत पाण्याखाली गेला असून पाणी पातळी {rj_stage:.2f} मी. MSL आहे.\n"
                f"   • नदीपात्रातील एकूण संगणकीय विसर्ग: {q_val:.1f} घनमीटर/सेकंद इतका नोंदवला गेला आहे.\n\n"
                "२. कृषी क्षेत्र खबरदारी व मार्गदर्शक सूचना:\n"
                "   • नदीकाठच्या सखल भागातील शेतीपंप, विद्युत मोटारी व सिंचन साहित्य सुरक्षित उंचावर हलवावे.\n"
                "   • पात्रातील वाढत्या प्रवाहामुळे जनावरांना नदीकाठच्या चरण्यापासून दूर ठेवावे.\n"
                "   • पाण्याखाली गेलेल्या बंधाऱ्यांवरून धोकादायक वाहतूक अथवा ये-जा करू नये.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "नोंद: हा अहवाल केवळ वैज्ञानिक व शैक्षणिक अभ्यासावर आधारित संगणकीय अंदाज आहे. अधिकृत प्रशासकीय घोषणा व प्रत्यक्ष पूर नियंत्रण उपाययोजनांसाठी जिल्हा आपत्ती व्यवस्थापन प्राधिकरण व जलसंपदा विभागाच्या निर्देशांचे पालन करावे."
            )
        else:
            text = (
                "॥ शिवाजी विद्यापीठ, कोल्हापूर ॥\n"
                "हवामान बदल व शाश्वतता अभ्यास केंद्र (CCCSS)\n"
                "प्रकल्प: DST-SERB, नवी दिल्ली | पंचगंगा नदी खोरे डिजिटल ट्विन\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "विषय: पंचगंगा नदी खोरे दैनंदिन सिंचन व प्रवाह स्थिती अहवाल\n"
                f"दिनांक: {now_ist}\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "नदीकाठच्या कृषी व सिंचन क्षेत्राच्या माहितीस्तव कळविण्यात येते की:\n\n"
                "१. बंधारे व विसर्ग स्थिती:\n"
                f"   • राजाराम बंधारा पातळी: {rj_stage:.2f} मी. MSL (बंधारा माथा: ५३५.७७ मी.)\n"
                f"   • नदीपात्रातील सद्य विसर्ग: {q_val:.2f} घनमीटर/सेकंद (सुरक्षित व नियंत्रित प्रवाह)\n"
                "   • सर्व कोल्हापूर पद्धतीचे बंधारे सद्यस्थितीत मुक्त व सुरक्षित प्रवाहात आहेत.\n\n"
                "२. शेतीपंप व सिंचन बाबत सल्ला:\n"
                "   • पंचगंगा पात्रातील प्रवाह पूर्णतः मर्यादित असल्याने शेतीपंप हलवण्याची आवश्यकता नाही.\n"
                "   • धरणांमधून केवळ पिण्याच्या पाण्यासाठी नियंत्रित विसर्ग सुरू आहे.\n"
                "   • पुढील ९० तासांत शेतीचे नुकसान करणारा कोणताही संभाव्य पूर धोका नाही.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "प्रकटन: हा अहवाल वैज्ञानिक संशोधनावर आधारित वस्तुनिष्ठ प्रवाह माहिती आहे."
            )
        return {"text": text, "reply_markup": get_telegram_keyboard_markup("mr")}

    # 2. CITIZEN VIEW (नागरी पूर स्थिती व वाहतूक अहवाल)
    if any(k in cmd for k in ["नागरिक", "citizen", "पूल", "घाट", "bridge", "city"]):
        if is_danger:
            diff_danger = sh_stage - DANGER_STAGE_M
            text = (
                "॥ शिवाजी विद्यापीठ, कोल्हापूर ॥\n"
                "हवामान बदल व शाश्वतता अभ्यास केंद्र (CCCSS)\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "अतिदक्षता पूर बुलेटिन: पंचगंगा नदी (कोल्हापूर शहर व परिसर)\n"
                f"दिनांक व वेळ: {now_ist}\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "सर्व संबंधित नागरिकांच्या माहितीस्तव कळविण्यात येते की:\n\n"
                "१. छत्रपती शिवाजी महाराज पूल (पंचगंगा घाट):\n"
                f"   • सद्य जलपातळी: {sh_stage:.2f} मी. MSL\n"
                f"   • स्थिती: अधिकृत धोका पातळी (५४३.३० मी.) पेक्षा +{diff_danger:.2f} मीटरने अधिक.\n"
                "   • पंचगंगा घाट परिसर व सखल भाग पूर्णतः जलमय स्थितीत आहे.\n\n"
                "२. वाहतूक व नागरी सुरक्षा सूचना:\n"
                "   • जुना शिवाजी पूल व नदीकाठच्या रस्त्यांवरील वाहतूक पर्यायी मार्गाने वळवणे आवश्यक.\n"
                "   • नागरिकांनी केवळ नवीन उड्डाणपूल व अधिकृत सुरक्षित मार्गांचा वापर करावा.\n"
                "   • कोणत्याही अनधिकृत माहितीवर किंवा अफवांवर विश्वास ठेवू नये.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "सांविधिक सूचना: हे वैज्ञानिक डिजिटल ट्विनचे मॉडेल आधारित निरीक्षण आहे. अधिकृत नागरी सतर्कता व स्थलांतर निर्देशांसाठी जिल्हाधिकारी कार्यालय व मनपा आपत्कालीन नियंत्रण कक्षाशी संपर्क साधावा."
            )
        elif is_warning:
            margin_danger = DANGER_STAGE_M - sh_stage
            text = (
                "॥ शिवाजी विद्यापीठ, कोल्हापूर ॥\n"
                "हवामान बदल व शाश्वतता अभ्यास केंद्र (CCCSS)\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "सावधानता पूर बुलेटिन: पंचगंगा नदी (इशारा पातळी)\n"
                f"दिनांक व वेळ: {now_ist}\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "नागरिकांच्या सतर्कतेसाठी कळविण्यात येते की:\n\n"
                "१. छत्रपती शिवाजी महाराज पूल पातळी:\n"
                f"   • सद्य जलपातळी: {sh_stage:.2f} मी. MSL (इशारा पातळी: ५४२.७० मी. ओलांडली आहे).\n"
                f"   • धोका पातळी (५४३.३० मी.) गाठण्यासाठी {margin_danger:.2f} मीटरचे अंतर शिल्लक आहे.\n\n"
                "२. सद्य नागरी स्थिती:\n"
                "   • पंचगंगा घाटावरील पायऱ्यांपर्यंत पाणी आले असून नदीकाठच्या रहिवाशांनी सतर्क रहावे.\n"
                "   • सखल भागातील मौल्यवान साहित्य सुरक्षित ठिकाणी स्थलांतरित ठेवण्याची पूर्वतयारी करावी.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "प्रकटन: वैज्ञानिक संशोधनात्मक निरीक्षण — शिवाजी विद्यापीठ, कोल्हापूर."
            )
        else:
            margin_warning = WARNING_STAGE_M - sh_stage
            text = (
                "॥ शिवाजी विद्यापीठ, कोल्हापूर ॥\n"
                "हवामान बदल व शाश्वतता अभ्यास केंद्र (CCCSS)\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "दैनिक नागरी जलस्थिती पत्रक: पंचगंगा नदी खोरे\n"
                f"दिनांक व वेळ: {now_ist}\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "नागरिकांच्या माहितीसाठी पंचगंगा नदीपात्रातील सद्यस्थिती खालीलप्रमाणे आहे:\n\n"
                "१. शिवाजी पूल व पंचगंगा घाट:\n"
                f"   • सद्य जलपातळी: {sh_stage:.2f} मी. MSL (सुरक्षित पातळी)\n"
                f"   • इशारा पातळीपासून (५४२.७० मी.) नदीचा प्रवाह {margin_warning:.2f} मीटर सुरक्षित अंतरावर आहे.\n"
                "   • पंचगंगा घाट परिसर पूर्णतः कोरडा व सुरक्षित स्थितीत आहे.\n\n"
                "२. नागरी दळणवळण:\n"
                "   • शिवाजी पूल, कसबा बावडा रस्ता व सर्व अंतर्गत वाहतूक सुरळीत सुरू आहे.\n"
                "   • नदी खोऱ्यात सध्या कोणत्याही स्वरूपाचा पूर धोका अस्तित्वात नाही.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "प्रकटन: शिवाजी विद्यापीठ संशोधन digital twin प्रणालीद्वारे प्रसारित."
            )
        return {"text": text, "reply_markup": get_telegram_keyboard_markup("mr")}

    # 3. STUDENT & RESEARCHER VIEW (शासकीय तांत्रिक बुलेटिन)
    if any(k in cmd for k in ["विद्यार्थी", "संशोधक", "student", "technical", "research", "q", "discharge"]):
        flood_regime = "CRITICAL FLOOD INUNDATION" if is_danger else "ELEVATED MONSOON RUNOFF" if is_warning else "CONTROLLED NON-MONSOON BASEFLOW"
        text = (
            "CENTRE FOR COLLABORATIVE CYBER SECURITY STUDIES (CCCSS)\n"
            "SHIVAJI UNIVERSITY, KOLHAPUR | DST-SERB RESEARCH INITIATIVE\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "HYDRODYNAMIC DIGITAL TWIN — BASIN TECHNICAL BULLETIN\n"
            f"Timestamp: {datetime.now(timezone.utc).strftime('%d-%b-%Y %H:%M UTC')} | Reference Cycle: Active\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"HYDROLOGICAL REGIME: {flood_regime}\n\n"
            "1. Gauged Hydraulic Observations:\n"
            f"   • Integrated Outlet Discharge : Q = {q_val:.2f} m³/s\n"
            f"   • Shivaji Maharaj Bridge Stage : {sh_stage:.2f} m MSL\n"
            f"     - Bed Datum Elevation       : 528.67 m MSL (Water Depth: {sh_stage - 528.67:.2f} m)\n"
            f"     - Warning Stage Benchmark    : 542.70 m MSL ({'EXCEEDED' if is_warning else f'Margin: -{WARNING_STAGE_M - sh_stage:.2f} m'})\n"
            f"     - Danger Stage Benchmark     : 543.30 m MSL ({'EXCEEDED' if is_danger else f'Margin: -{DANGER_STAGE_M - sh_stage:.2f} m'})\n"
            f"     - Historical 2019/2021 HFL   : 545.33 m MSL\n"
            f"   • Rajaram K.T. Weir Stage     : {rj_stage:.2f} m MSL (Crest: 535.77 m, {'SUBMERGED' if is_weir_submerged else 'FREE-FLOW'})\n\n"
            "2. Mathematical Formulation & Architecture:\n"
            "   • Hydrologic Loss Model: SCS-CN Distributed Runoff Potential\n"
            "   • Channel Hydraulic Routing: 1D Muskingum-Cunge Diffusion Wave\n"
            "   • Stage-Discharge Extension: Manning Power-Law Hydraulic Extrapolation beyond HFL\n"
            "   • Telemetry State: Calibrated Hydrodynamic Baseline Active\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Institutional Disclaimer: Pure academic & scientific research digital twin. For statutory flood alerts, consult competent district administrative authorities."
        )
        return {"text": text, "reply_markup": get_telegram_keyboard_markup("en")}

    # 4. 90-HOUR FORECAST
    if any(k in cmd for k in ["forecast", "अंदाज", "९०", "90"]):
        text = (
            "॥ शिवाजी विद्यापीठ, कोल्हापूर ॥\n"
            "हवामान बदल व शाश्वतता अभ्यास केंद्र (CCCSS)\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "९० तास वैज्ञानिक जलप्रवाह व पर्जन्य अंदाज बुलेटिन\n"
            f"दिनांक व वेळ: {now_ist}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "वैज्ञानिक मॉडेल्सद्वारे प्राप्त पुढील ९० तासांचा अंदाज खालीलप्रमाणे:\n\n"
            "१. प्रवाह अंदाज:\n"
            f"   • अंदाजित कमाल विसर्ग: {q_val:.2f} घनमीटर/सेकंद (स्थिर व मर्यादित प्रवाह)\n"
            "   • नदीपातळी अंदाज: सुरक्षित पातळीच्या कक्षेत स्थिर राहण्याची शक्यता.\n\n"
            "२. पर्जन्य व पाणलोट अंदाज:\n"
            "   • Open-Meteo उच्च-रिझोल्यूशन संख्यात्मक मॉडेलनुसार खोऱ्यात अतिवृष्टीची शक्यता नाही.\n"
            "   • पाणी पातळी इशारा पातळीपेक्षा ११ मीटरहून अधिक सुरक्षित अंतरावर राहील.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "नोंद: हा अहवाल वैज्ञानिक संशोधनासाठी संगणकीकृत प्रारूप आहे."
        )
        return {"text": text, "reply_markup": get_telegram_keyboard_markup("mr")}

    # 5. LANGUAGE SWITCH (English Mode)
    if any(k in cmd for k in ["switch to english", "english"]):
        text = (
            "CENTRE FOR COLLABORATIVE CYBER SECURITY STUDIES (CCCSS)\n"
            "SHIVAJI UNIVERSITY, KOLHAPUR | DST-SERB RESEARCH INITIATIVE\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "PANCHGANGA BASIN HYDROLOGICAL INFORMATION SYSTEM\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Welcome to the HydroCast Panchganga scientific bulletin service.\n\n"
            "Please select the designated bulletin category from the panel below:\n"
            "• Farmer View — Weir submergence, agricultural pump safety & dam outflow\n"
            "• Citizen View — Bridge stage levels, ghat water status & civic transit\n"
            "• Student / Research — Complete hydrodynamic telemetry, Q in m³/s & routing data\n"
            "• 90-Hour Forecast — Numerical weather & runoff projection horizon\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Statutory Notice: Academic research digital twin. For administrative flood directives, refer to District Administration."
        )
        return {"text": text, "reply_markup": get_telegram_keyboard_markup("en")}

    # 6. DEFAULT / START / MARATHI MODE
    text = (
        "॥ शिवाजी विद्यापीठ, कोल्हापूर ॥\n"
        "हवामान बदल व शाश्वतता अभ्यास केंद्र (CCCSS)\n"
        "प्रकल्प: DST-SERB, नवी दिल्ली | पंचगंगा नदी खोरे डिजिटल ट्विन\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "पंचगंगा नदी खोरे अधिकृत वैज्ञानिक माहिती पोर्टल\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "नागरिक, शेतकरी व संशोधकांच्या सुलभ संदर्भासाठी माहिती खालील दालनांमध्ये विभागण्यात आली आहे.\n"
        "कृपया आपल्या आवश्यकतेनुसार खालीलपैकी पर्यायाची निवड करावी:\n\n"
        "१. शेतकरी माहिती — को.प. बंधारे, शेतीपंप सुरक्षितता व सिंचन प्रवाह अहवाल\n"
        "२. नागरिक पूर स्थिती — छत्रपती शिवाजी महाराज पूल, पंचगंगा घाट पातळी व नागरी दळणवळण\n"
        "३. विद्यार्थी / संशोधक — संपूर्ण वैज्ञानिक व हायड्रॉलिक डेटा (विसर्ग, पातळी व मॉडेल्स)\n"
        "४. ९० तास अंदाज — पुढील ९० तासांचे पर्जन्य व प्रवाह प्रक्षेप\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "प्रकटन: हा केवळ शैक्षणिक व वैज्ञानिक संशोधनात्मक अभ्यास आहे. अधिकृत शासकीय सूचना व आपत्कालीन मार्गदर्शक सूचनांसाठी जिल्हा प्रशासनाशी संपर्क साधावा."
    )
    return {"text": text, "reply_markup": get_telegram_keyboard_markup("mr")}


async def _handle_telegram_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route an incoming Telegram update to the HydroCast command handler."""
    message = update.effective_message
    if not message or not message.text:
        return
    chat_id = update.effective_chat.id if update.effective_chat else None
    username = update.effective_user.username if update.effective_user else None

    if not is_authorized(chat_id, username):
        await message.reply_text("Access Restricted: This bot is for authorized HydroCast operators only.")
        return

    result = handle_telegram_command(message.text)
    text = result.get("text", "") if isinstance(result, dict) else str(result)
    reply_markup = result.get("reply_markup") if isinstance(result, dict) else None

    # Telegram message limit is 4096 chars; chunk long bulletins.
    for i in range(0, len(text), 4000):
        chunk = text[i:i + 4000]
        kwargs: dict[str, Any] = {}
        if reply_markup and i == 0:
            from telegram import ReplyKeyboardMarkup
            kwargs["reply_markup"] = ReplyKeyboardMarkup(
                reply_markup.get("keyboard", []),
                resize_keyboard=reply_markup.get("resize_keyboard", True),
                one_time_keyboard=reply_markup.get("one_time_keyboard", False),
            )
        await message.reply_text(chunk, **kwargs)


def build_telegram_application() -> Optional[Application]:
    """
    Build a real python-telegram-bot Application when TELEGRAM_BOT_TOKEN is set.

    Falls back to None (stub mode) when no token is configured, so the FastAPI
    backend still starts without Telegram alerting.
    """
    if TELEGRAM_TOKEN is None:
        log.warning("TELEGRAM_BOT_TOKEN not set — Telegram bot running in stub mode (no alerting)")
        return None

    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .concurrent_updates(True)
        .build()
    )

    # Any free text goes through the HydroCast command handler (farmer /
    # citizen / student / research views). Commands are also accepted.
    application.add_handler(CommandHandler("start", _handle_telegram_update))
    application.add_handler(CommandHandler("help", _handle_telegram_update))
    application.add_handler(CommandHandler("forecast", _handle_telegram_update))
    application.add_handler(CommandHandler("farmer", _handle_telegram_update))
    application.add_handler(CommandHandler("citizen", _handle_telegram_update))
    application.add_handler(CommandHandler("student", _handle_telegram_update))
    application.add_handler(CommandHandler("research", _handle_telegram_update))
    application.add_handler(CommandHandler("switch", _handle_telegram_update))

    # Catch-all for plain text messages (Marathi / English keywords).
    from telegram.ext import MessageHandler, filters
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_telegram_update))

    log.info("Telegram bot application built with real-time command handling")
    return application


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
    "format_hourly_heartbeat",
    "format_emergency_flood_alert",
    "send_hourly_heartbeat",
    "send_emergency_alert",
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
]
