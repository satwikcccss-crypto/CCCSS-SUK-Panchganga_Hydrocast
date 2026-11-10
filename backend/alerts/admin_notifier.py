"""
backend/alerts/admin_notifier.py
================================
100% Free, Zero-Subscription Admin Notification & Alert System.

Features:
  1. Security & Crash Alerts: Instant dispatch on suspicious logins, DB drop, or pipeline error.
  2. 5-Day Periodic Review Digest: Automated health audit of runs, backups, and river stages.
  3. Password Reset Dispatcher: Cryptographic time-limited link sent directly to admin inbox.

Target Recipients:
  - Lead Developer: satwikcccss@gmail.com
  - Plus any configured secondary admin emails.
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta

log = logging.getLogger(__name__)

# Lead Developer & Admin configuration
LEAD_ADMIN_EMAIL = os.environ.get("LEAD_ADMIN_EMAIL", "satwikcccss@gmail.com")
ADMIN_EMAILS = [
    email.strip() for email in os.environ.get(
        "ADMIN_EMAILS",
        f"{LEAD_ADMIN_EMAIL},admin@unishivaji.ac.in"
    ).split(",") if email.strip()
]

# SMTP Configuration (Standard Free Gmail or University Server)
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")  # Free 16-character Google App Password


def _send_email_smtp(to_addrs: list[str], subject: str, html_body: str) -> bool:
    """Send an HTML email via standard Python smtplib with STARTTLS."""
    if not SMTP_USER or not SMTP_PASSWORD:
        log.warning(
            "SMTP credentials not configured (SMTP_USER/SMTP_PASSWORD empty). "
            "Email to %s was logged but not dispatched over SMTP.",
            to_addrs
        )
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"HydroCast SUK Alerts <{SMTP_USER}>"
    msg["To"] = ", ".join(to_addrs)

    part = MIMEText(html_body, "html")
    msg.attach(part)

    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, to_addrs, msg.as_string())
        server.quit()
        log.info("Successfully sent admin notification email to %s", to_addrs)
        return True
    except Exception as e:
        log.error("Failed to send admin notification email: %s", e)
        return False


def send_security_alert(
    event_type: str,
    details: str,
    client_ip: str = "Unknown",
    severity: str = "HIGH",
) -> dict:
    """Send an urgent security or system crash alert to the 5 admins."""
    now_ist = (datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)).strftime("%d-%b-%Y %I:%M %p IST")
    subject = f"🚨 [HydroCast Security] {severity}: {event_type}"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f8fafc; padding: 20px; color: #1e293b;">
        <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
            <div style="background: #dc2626; color: white; padding: 16px 24px;">
                <h2 style="margin: 0; font-size: 18px; font-weight: 700;">HydroCast Security & System Alert</h2>
                <div style="font-size: 12px; opacity: 0.9;">Shivaji University Kolhapur · CCCSS Research Infrastructure</div>
            </div>
            <div style="padding: 24px;">
                <p style="font-size: 14px; margin-top: 0;">An anomaly or critical event was detected by the HydroCast server:</p>
                <div style="background: #fef2f2; border-left: 4px solid #ef4444; padding: 12px 16px; border-radius: 4px; margin-bottom: 20px;">
                    <div style="font-weight: 700; color: #991b1b; font-size: 15px;">{event_type}</div>
                    <div style="color: #7f1d1d; font-size: 13px; margin-top: 4px;">{details}</div>
                </div>
                <table style="width: 100%; font-size: 13px; border-collapse: collapse;">
                    <tr><td style="padding: 6px 0; color: #64748b;">Timestamp:</td><td style="padding: 6px 0; font-weight: 600;">{now_ist}</td></tr>
                    <tr><td style="padding: 6px 0; color: #64748b;">Source / IP:</td><td style="padding: 6px 0; font-weight: 600; font-family: monospace;">{client_ip}</td></tr>
                    <tr><td style="padding: 6px 0; color: #64748b;">Severity Level:</td><td style="padding: 6px 0; font-weight: 700; color: #dc2626;">{severity}</td></tr>
                </table>
                <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #64748b;">
                    Admin Console: <a href="http://localhost:3001" style="color: #0284c7; text-decoration: none;">http://localhost:3001</a><br>
                    Lead Developer: {LEAD_ADMIN_EMAIL}
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    delivered = _send_email_smtp(ADMIN_EMAILS, subject, html)
    return {"status": "dispatched" if delivered else "logged", "recipients": ADMIN_EMAILS, "event": event_type}


def send_periodic_review_digest(
    total_runs_5d: int = 120,
    successful_runs: int = 120,
    current_q_m3s: float = 9.10,
    shivaji_stage_m: float = 531.54,
    last_backup_time: str = "Recent",
) -> dict:
    """Send 5-day operational review and health audit digest to admins."""
    now_ist = (datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)).strftime("%d-%b-%Y %I:%M %p IST")
    subject = "📊 [HydroCast Digest] 5-Day System Review & Operational Health"

    uptime_pct = (successful_runs / max(1, total_runs_5d)) * 100.0

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f8fafc; padding: 20px; color: #1e293b;">
        <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
            <div style="background: #0284c7; color: white; padding: 16px 24px;">
                <h2 style="margin: 0; font-size: 18px; font-weight: 700;">HydroCast 5-Day Operational Digest</h2>
                <div style="font-size: 12px; opacity: 0.9;">Panchganga Basin Digital Twin · CCCSS Shivaji University</div>
            </div>
            <div style="padding: 24px;">
                <p style="font-size: 14px; margin-top: 0;">Here is the 5-day automated health summary of the HydroCast server:</p>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px;">
                    <div style="background: #f0fdf4; border: 1px solid #bbf7d0; padding: 12px; border-radius: 8px;">
                        <div style="font-size: 11px; color: #166534; font-weight: 600; text-transform: uppercase;">Pipeline Health</div>
                        <div style="font-size: 20px; font-weight: 800; color: #15803d;">{uptime_pct:.1f}%</div>
                        <div style="font-size: 11px; color: #4ade80;">{successful_runs}/{total_runs_5d} cycles OK</div>
                    </div>
                    <div style="background: #f0f9ff; border: 1px solid #bae6fd; padding: 12px; border-radius: 8px;">
                        <div style="font-size: 11px; color: #075985; font-weight: 600; text-transform: uppercase;">Baseflow Regime</div>
                        <div style="font-size: 20px; font-weight: 800; color: #0284c7;">{current_q_m3s:.2f} m³/s</div>
                        <div style="font-size: 11px; color: #38bdf8;">Stage: {shivaji_stage_m:.2f} m MSL</div>
                    </div>
                </div>
                <table style="width: 100%; font-size: 13px; border-collapse: collapse;">
                    <tr style="border-bottom: 1px solid #f1f5f9;"><td style="padding: 8px 0; color: #64748b;">Report Date:</td><td style="padding: 8px 0; font-weight: 600;">{now_ist}</td></tr>
                    <tr style="border-bottom: 1px solid #f1f5f9;"><td style="padding: 8px 0; color: #64748b;">Last DB Backup:</td><td style="padding: 8px 0; font-weight: 600;">{last_backup_time}</td></tr>
                    <tr style="border-bottom: 1px solid #f1f5f9;"><td style="padding: 8px 0; color: #64748b;">IoT Sensor Status:</td><td style="padding: 8px 0; font-weight: 600; color: #0284c7;">Seasonal Standby (Nov–May)</td></tr>
                    <tr><td style="padding: 8px 0; color: #64748b;">Primary Admin:</td><td style="padding: 8px 0; font-weight: 600;">{LEAD_ADMIN_EMAIL}</td></tr>
                </table>
                <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #64748b;">
                    HydroCast Research Portal: <a href="http://localhost:3000" style="color: #0284c7; text-decoration: none;">http://localhost:3000</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    delivered = _send_email_smtp(ADMIN_EMAILS, subject, html)
    return {"status": "dispatched" if delivered else "logged", "recipients": ADMIN_EMAILS}


def send_password_reset_email(to_email: str, reset_token: str, admin_name: str = "Admin") -> bool:
    """Send a secure 1-click password reset token link to an admin."""
    reset_url = f"http://localhost:3001/auth/reset-password?token={reset_token}"
    subject = "🔑 [HydroCast] Admin Password Reset Request"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f8fafc; padding: 20px; color: #1e293b;">
        <div style="max-width: 500px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
            <div style="background: #0f172a; color: white; padding: 16px 24px;">
                <h2 style="margin: 0; font-size: 16px; font-weight: 700;">HydroCast Admin Password Reset</h2>
            </div>
            <div style="padding: 24px;">
                <p style="font-size: 14px; margin-top: 0;">Hello <strong>{admin_name}</strong>,</p>
                <p style="font-size: 13px; color: #475569;">A request was received to reset the password for your HydroCast Admin Console account.</p>
                <div style="text-align: center; margin: 24px 0;">
                    <a href="{reset_url}" style="background: #0284c7; color: white; text-decoration: none; padding: 10px 20px; border-radius: 6px; font-weight: 600; font-size: 14px; display: inline-block;">Reset My Password</a>
                </div>
                <p style="font-size: 12px; color: #64748b;">This reset link will expire in <strong>15 minutes</strong>. If you did not request this, please contact the Lead Developer ({LEAD_ADMIN_EMAIL}) immediately.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return _send_email_smtp([to_email], subject, html)

