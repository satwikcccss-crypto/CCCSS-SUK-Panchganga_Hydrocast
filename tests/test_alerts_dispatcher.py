"""
tests/test_alerts_dispatcher.py
================================
Unit tests for the DDMA multi-channel Telegram dispatcher and disaster webhooks.
"""

import unittest
from unittest.mock import patch, MagicMock

from src.alerts.telegram_bot import (
    format_telegram_alert,
    get_severity_badge,
    send_telegram_broadcast,
    dispatch_agency_webhooks,
    get_target_chat_ids,
    get_webhook_urls,
)


class TestAlertsDispatcher(unittest.TestCase):

    def test_severity_badges(self):
        self.assertIn("🟡", get_severity_badge("ALERT"))
        self.assertIn("🟠", get_severity_badge("WARNING"))
        self.assertIn("🔴", get_severity_badge("DANGER"))
        self.assertIn("🚨", get_severity_badge("HFL_EXCEEDED"))

    def test_format_telegram_alert_content(self):
        card = format_telegram_alert(
            site_id="SHIVAJI_BRIDGE",
            site_name="Shivaji Bridge",
            level="DANGER",
            peak_stage=543.85,
            current_stage=533.20,
            warning_stage=542.70,
            danger_stage=543.30,
            hfl_stage=545.33,
            arrival_str="2026-09-10 18:00 UTC",
            cycle_id="CYC_20260910_1200",
            action="Evacuate low-lying riverside areas immediately.",
        )
        self.assertIn("HYDROCAST FLOOD BULLETIN", card)
        self.assertIn("Shivaji Bridge", card)
        self.assertIn("543.85 m MSL", card)
        self.assertIn("Exceeds Danger by:", card)
        self.assertIn("Evacuate low-lying", card)

    @patch("src.alerts.telegram_bot.PRIMARY_CHAT_ID", "-100111")
    @patch("src.alerts.telegram_bot.DDMA_CHATS_ENV", "-100222,-100333")
    def test_get_target_chat_ids(self):
        chats = get_target_chat_ids()
        self.assertEqual(chats, ["-100111", "-100222", "-100333"])

    @patch("src.alerts.telegram_bot.WEBHOOKS_ENV", "https://hook1.gov.in, https://hook2.gov.in")
    def test_get_webhook_urls(self):
        urls = get_webhook_urls()
        self.assertEqual(urls, ["https://hook1.gov.in", "https://hook2.gov.in"])

    @patch("requests.post")
    @patch("src.alerts.telegram_bot.get_target_chat_ids", return_value=["-100111", "-100222"])
    @patch("src.alerts.telegram_bot.TELEGRAM_TOKEN", "mock_bot_token")
    def test_send_telegram_broadcast(self, mock_get_chats, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        delivered = send_telegram_broadcast("Test Alert")
        self.assertEqual(delivered, 2)
        self.assertEqual(mock_post.call_count, 2)

    @patch("requests.post")
    @patch("src.alerts.telegram_bot.get_webhook_urls", return_value=["https://agency.gov.in/alert"])
    def test_dispatch_agency_webhooks(self, mock_get_urls, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        payload = {"alert_id": "ALT-001", "level": "DANGER"}
        success = dispatch_agency_webhooks(payload)
        self.assertEqual(success, 1)
        mock_post.assert_called_once()



if __name__ == "__main__":
    unittest.main()
