"""
src/alerts/evaluator.py
========================
Evaluates CWC thresholds at each bridge site for the current cycle.
Issues alert_events, sends Telegram + email notifications.
"""

import logging
import os
import smtplib
import json
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import requests

log = logging.getLogger(__name__)

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
SMTP_HOST        = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT        = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER        = os.getenv("SMTP_USER", "")
SMTP_PASS        = os.getenv("SMTP_PASS", "")
ALERT_EMAILS     = os.getenv("ALERT_EMAILS", "").split(",")


from src.alerts.telegram_bot import (
    format_telegram_alert,
    send_telegram_broadcast,
    dispatch_agency_webhooks,
)


def _get_bridge_metadata(conn, site_id: str) -> dict:
    """Retrieve official CWC/WRD datums from database with robust defaults."""
    defaults = {
        "SHIVAJI_BRIDGE": {"name": "Shivaji Bridge (Panchganga Ghat)", "warning": 542.70, "danger": 543.30, "hfl": 545.33},
        "RAJARAM_BRIDGE": {"name": "Rajaram K.T. Weir (Kasba Bawada)", "warning": 542.07, "danger": 543.30, "hfl": 545.33},
    }
    meta = defaults.get(site_id, {"name": site_id, "warning": 542.0, "danger": 543.0, "hfl": 545.0})
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT site_name, warning_stage_m, danger_stage_m, hfl_m
                FROM bridge_sites WHERE site_id=%s
            """, (site_id,))
            row = cur.fetchone()
            if row:
                meta = {
                    "name": row[0] or site_id,
                    "warning": float(row[1] or meta["warning"]),
                    "danger": float(row[2] or meta["danger"]),
                    "hfl": float(row[3] or meta["hfl"]),
                }
    except Exception as e:
        log.warning("Could not query bridge_sites for %s (using defaults): %s", site_id, e)
    return meta


def evaluate_and_notify(conn, cycle_id: str, bridge_forecasts: dict) -> int:
    """
    For each bridge site, check if peak_level warrants an alert.
    Issues alert_events, broadcasts to DDMA Telegram channels, and dispatches webhooks.
    Returns count of alerts issued.
    """
    issued = 0
    for site_id, forecast in bridge_forecasts.items():
        level      = forecast.get("peak_level", "NORMAL")

        peak_stage = float(forecast.get("peak_stage", 0.0))
        arrival    = forecast.get("arrival_time")

        forecast_rows = forecast.get("forecast", [])
        if forecast_rows and isinstance(forecast_rows[0], (list, tuple)) and len(forecast_rows[0]) >= 3:
            current_stage = float(forecast_rows[0][2])
        elif forecast_rows and isinstance(forecast_rows[0], dict) and "stage_m" in forecast_rows[0]:
            current_stage = float(forecast_rows[0]["stage_m"])
        else:
            current_stage = float(forecast.get("current_stage", peak_stage))

        if level == "NORMAL":

            continue

        # Check if same-or-higher alert already active for this site
        with conn.cursor() as cur:
            cur.execute("""
                SELECT alert_id FROM alert_events
                WHERE basin_id=%s
                  AND status='active'
                  AND alert_type >= %s
                ORDER BY issued_at DESC LIMIT 1
            """, (site_id, _cwc_to_alert_type(level)))
            existing = cur.fetchone()

        if existing:
            log.info("Alert already active for %s [%s] — skipping duplicate", site_id, level)
            continue

        meta = _get_bridge_metadata(conn, site_id)
        msg = _build_message(site_id, level, peak_stage, arrival, cycle_id)
        alert_id = f"ALT_{cycle_id}_{site_id}_{level}"
        arr_str = arrival.strftime("%Y-%m-%d %H:%M UTC") if arrival else "within 90 hours"

        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO alert_events
                    (alert_id, basin_id, run_id, alert_type, trigger_type,
                     stage_m, time_of_peak_forecast, issued_at, triggered_at,
                     status, alert_message, recommended_action)
                VALUES (%s, %s, %s, %s, 'threshold', %s, %s, NOW(), NOW(),
                        'active', %s, %s)
                ON CONFLICT (alert_id) DO NOTHING
            """, (
                alert_id, site_id, cycle_id,
                _cwc_to_alert_type(level),
                round(peak_stage, 2),
                arrival,
                msg["body"],
                msg["action"],
            ))
        conn.commit()

        # Format official DDMA HTML card and broadcast to Telegram channels
        tg_html = format_telegram_alert(
            site_id=site_id,
            site_name=meta["name"],
            level=level,
            peak_stage=peak_stage,
            current_stage=current_stage,
            warning_stage=meta["warning"],
            danger_stage=meta["danger"],
            hfl_stage=meta["hfl"],
            arrival_str=arr_str,
            cycle_id=cycle_id,
            action=msg["action"],
        )
        send_telegram_broadcast(tg_html, parse_mode="HTML")

        # Dispatch webhook to external disaster management agency APIs
        webhook_payload = {
            "alert_id": alert_id,
            "cycle_id": cycle_id,
            "site_id": site_id,
            "site_name": meta["name"],
            "alert_level": level,
            "peak_stage_m": round(peak_stage, 2),
            "warning_stage_m": meta["warning"],
            "danger_stage_m": meta["danger"],
            "hfl_stage_m": meta["hfl"],
            "arrival_time": arr_str,
            "recommended_action": msg["action"],
            "issued_at": datetime.now(timezone.utc).isoformat(),
        }
        dispatch_agency_webhooks(webhook_payload)

        # Email dispatch
        _send_email(msg["subject"], msg["body"])

        issued += 1
        log.info("Alert issued and broadcast: %s [%s] at %s", site_id, level, alert_id)

    return issued



def _cwc_to_alert_type(level: str) -> str:
    return {"ALERT": "watch", "WARNING": "warning", "DANGER": "emergency",
            "HFL_EXCEEDED": "emergency"}.get(level, "watch")


def _build_message(site_id, level, stage, arrival, cycle_id) -> dict:
    arr_str = arrival.strftime("%Y-%m-%d %H:%M UTC") if arrival else "within 90 hours"
    action = {
        "ALERT":        "Increase monitoring frequency. Alert downstream agencies.",
        "WARNING":      "Mobilise response teams. Issue public advisory.",
        "DANGER":       "Initiate evacuation of low-lying areas. Emergency services on standby.",
        "HFL_EXCEEDED": "EXTREME FLOOD. All evacuation protocols in effect. CWC to issue national bulletin.",
    }.get(level, "Monitor situation.")

    body = (
        f"HYDROCAST FLOOD ALERT\n"
        f"Site        : {site_id}\n"
        f"Alert Level : {level}\n"
        f"Peak Stage  : {stage:.2f} m\n"
        f"Arrival Time: {arr_str}\n"
        f"Cycle ID    : {cycle_id}\n\n"
        f"Action      : {action}"
    )
    return {
        "subject": f"[HYDROCAST] {level} — {site_id} — {arr_str}",
        "body":    body,
        "action":  action,
    }


def _send_telegram(subject: str, body: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        log.debug("Telegram not configured — skipping")
        return
    url  = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    text = f"*{subject}*\n\n```\n{body}\n```"
    try:
        r = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text,
                                      "parse_mode": "Markdown"}, timeout=10)
        r.raise_for_status()
        log.info("Telegram notification sent")
    except Exception as e:
        log.error("Telegram failed: %s", e)


def _send_email(subject: str, body: str):
    if not SMTP_USER or not ALERT_EMAILS or ALERT_EMAILS == [""]:
        log.debug("Email not configured — skipping")
        return
    try:
        msg = MIMEMultipart()
        msg["From"]    = SMTP_USER
        msg["To"]      = ", ".join(ALERT_EMAILS)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, ALERT_EMAILS, msg.as_string())
        log.info("Email sent to %s", ALERT_EMAILS)
    except Exception as e:
        log.error("Email failed: %s", e)
