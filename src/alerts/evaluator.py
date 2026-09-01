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


def evaluate_and_notify(conn, cycle_id: str, bridge_forecasts: dict) -> int:
    """
    For each bridge site, check if peak_level warrants an alert.
    Returns count of alerts issued.
    """
    issued = 0
    for site_id, forecast in bridge_forecasts.items():
        level      = forecast["peak_level"]
        peak_stage = forecast["peak_stage"]
        arrival    = forecast["arrival_time"]

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
            log.info("Alert already active for %s [%s] — skipping", site_id, level)
            continue

        # Build alert message
        msg = _build_message(site_id, level, peak_stage, arrival, cycle_id)
        alert_id = f"ALT_{cycle_id}_{site_id}_{level}"

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

        _send_telegram(msg["subject"], msg["body"])
        _send_email(msg["subject"], msg["body"])
        issued += 1
        log.info("Alert issued: %s [%s] at %s", site_id, level, alert_id)

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
