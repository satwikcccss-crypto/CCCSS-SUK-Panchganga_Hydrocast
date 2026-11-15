"""
scripts/test_admin_email.py
===========================
Diagnostic tool to test sending an email alert to the configured lead admin.

Usage:
  python scripts/test_admin_email.py
"""

import sys
import os
import logging
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT_DIR / ".env", override=True)
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("test_admin_email")

from backend.alerts.admin_notifier import (
    get_lead_admin_email,
    get_admin_emails,
    get_smtp_config,
    send_security_alert,
    _send_email_smtp,
)

def main():
    print("=" * 65)
    print("  HYDROCAST DEVELOPER EMAIL DIAGNOSTIC & TEST TOOL")
    print("=" * 65)

    lead_email = get_lead_admin_email()
    admin_emails = get_admin_emails()
    host, port, user, password = get_smtp_config()

    print(f"\n1. Target Lead Developer Email : {lead_email}")
    print(f"2. All Configured Admin Emails : {admin_emails}")
    print(f"3. SMTP Server Host            : {host}:{port}")
    print(f"4. SMTP User Configured        : {'YES (' + user + ')' if user and 'REPLACE_ME' not in user else 'NO (Empty or Placeholder)'}")
    print(f"5. SMTP Password Configured    : {'YES (***masked***)' if password and 'REPLACE_ME' not in password else 'NO (Empty or Placeholder)'}")

    if not user or not password or "REPLACE_ME" in user or "REPLACE_ME" in password:
        print("\n" + "!" * 65)
        print("  WARNING: SMTP CREDENTIALS NOT CONFIGURED IN .env!")
        print("!" * 65)
        print("\nTo receive real emails on your SMTP provider:")
        print("  1. Open your Google Account: https://myaccount.google.com/apppasswords")
        print("  2. Generate a 16-character 'App Password' for 'Mail'.")
        print("  3. Update your .env file with:")
        print("     SMTP_HOST=smtp.gmail.com")
        print("     SMTP_PORT=587")
        print(f"     SMTP_USER={lead_email}")
        print("     SMTP_PASSWORD=your_16_character_app_password")
        print("     LEAD_ADMIN_EMAIL=" + lead_email)
        print("\nAttempting dry-run email dispatch test...")
    else:
        print("\nAttempting live SMTP connection to dispatch test email...")

    result = send_security_alert(
        event_type="Manual SMTP Diagnostic Test",
        details="This is a test notification confirming email delivery to the HydroCast Lead Developer.",
        client_ip="127.0.0.1",
        severity="INFO"
    )

    print(f"\nDispatch Result: {result}")
    if result.get("status") == "dispatched":
        print("\n✓ SUCCESS: Test email was successfully sent over SMTP to " + str(admin_emails))
    else:
        print("\n⚠ NOTE: Email was logged locally because SMTP_USER/SMTP_PASSWORD is a placeholder.")
        print("  Follow the instructions above to activate real Gmail delivery.")
    print("=" * 65)

if __name__ == "__main__":
    main()

