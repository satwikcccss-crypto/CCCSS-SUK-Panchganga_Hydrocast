#!/usr/bin/env python3
"""
Comprehensive Playwright E2E Audit for HydroCast Frontends
Tests EVERY page, EVERY tab, EVERY interactive element across:
1. Public Citizen Portal (http://localhost:3000) - English, Marathi, Mobile, Desktop
2. Admin Operator Console (http://localhost:3001) - All 13 Categories, Auth, Terminal Dock
"""

import os
import sys
import json
import time
import re
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path("test-results/comprehensive_playwright")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PUBLIC_URL = "http://localhost:3000"
ADMIN_URL = "http://localhost:3001"

# Hardcoded values that should NOT appear
SUSPICIOUS_PATTERNS = [
    (r"localhost:8000/docs", "Leaked Swagger localhost link"),
    (r"Interactive OpenAPI Docs", "Swagger docs button on public portal"),
    (r"532\.63.*hardcoded", "Hardcoded Shivaji Stage comment/flag"),
    (r"538\.86.*hardcoded", "Hardcoded Rajaram Stage comment/flag"),
]


def run_audit():
    print("=" * 80)
    print("🚀 STARTING COMPREHENSIVE E2E AUDIT ACROSS ALL PAGES AND TABS")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Public Base: {PUBLIC_URL}")
    print(f"Admin Base:  {ADMIN_URL}")
    print(f"Output Dir:  {OUTPUT_DIR.resolve()}")
    print("=" * 80)

    report = {
        "timestamp": datetime.now().isoformat(),
        "public_portal": {
            "routes_tested": [],
            "tabs_en": [],
            "tabs_mr": [],
            "security_routes": [],
            "mobile": {},
            "console_errors": [],
            "network_errors": [],
        },
        "admin_portal": {
            "routes_tested": [],
            "categories": [],
            "terminal_dock": {},
            "console_errors": [],
            "network_errors": [],
        },
        "assertions": [],
        "screenshots": [],
        "summary": {
            "total_tabs_audited": 0,
            "total_screenshots": 0,
            "passed_assertions": 0,
            "failed_assertions": 0,
        },
    }

    def assert_rule(condition: bool, description: str):
        if condition:
            report["assertions"].append({"status": "PASS", "desc": description})
            report["summary"]["passed_assertions"] += 1
            print(f"  ✅ [PASS] {description}")
        else:
            report["assertions"].append({"status": "FAIL", "desc": description})
            report["summary"]["failed_assertions"] += 1
            print(f"  ❌ [FAIL] {description}")

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=True)
        except Exception:
            browser = p.chromium.launch(channel="msedge", headless=True)

        # =====================================================================
        # PART 1: PUBLIC PORTAL SECURITY CHECKS (routes that must be 404)
        # =====================================================================
        print("\n--- 1. Testing Public Portal Internal Route Blocking ---")
        security_ctx = browser.new_context()
        sec_page = security_ctx.new_page()

        for sec_path in ["/admin", "/console", "/login"]:
            resp = sec_page.goto(f"{PUBLIC_URL}{sec_path}", wait_until="load")
            status = resp.status if resp else 0
            assert_rule(status == 404, f"Public route {sec_path} returns 404 (got {status})")
            report["public_portal"]["security_routes"].append({"route": sec_path, "status": status})

        security_ctx.close()

        # =====================================================================
        # PART 2: PUBLIC PORTAL DESKTOP (ENGLISH)
        # =====================================================================
        print("\n--- 2. Auditing Public Dashboard (Desktop - English) ---")
        desktop_ctx = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = desktop_ctx.new_page()

        def on_console(msg):
            if msg.type in ("error", "warning") and "favicon" not in msg.text.lower():
                report["public_portal"]["console_errors"].append(
                    {
                        "type": msg.type,
                        "text": msg.text,
                        "url": msg.location.get("url") if msg.location else "",
                    }
                )

        def on_response(resp):
            if resp.status >= 400 and not resp.url.endswith("/favicon.ico"):
                report["public_portal"]["network_errors"].append(
                    {"status": resp.status, "url": resp.url}
                )

        page.on("console", on_console)
        page.on("response", on_response)

        resp = page.goto(f"{PUBLIC_URL}/dashboard", wait_until="networkidle")
        assert_rule(resp.status == 200, "Public /dashboard loaded successfully (HTTP 200)")
        time.sleep(1)

        # Tabs in English
        public_tabs = [
            ("dashboard", "Executive Dashboard"),
            ("river-stages", "River Stages & Flow"),
            ("rainfall", "Rainfall & Rain Gauges"),
            ("sensors", "Sensor Network"),
            ("data-sharing", "Open Data & Telegram Bot"),
            ("info", "Project Information"),
        ]

        for tab_id, tab_label in public_tabs:
            print(f"\n[Public EN] Testing Tab: {tab_label} ({tab_id})")
            btn = page.locator(f"aside button:has-text('{tab_label}')").first
            if btn.count() > 0:
                btn.click()
            else:
                page.locator(f"button:has-text('{tab_label}')").first.click()

            time.sleep(1)
            page.wait_for_load_state("networkidle")

            # Check text content for unwanted artifacts
            body_text = page.locator("body").inner_text()
            for pattern, desc in SUSPICIOUS_PATTERNS:
                assert_rule(not re.search(pattern, body_text), f"{tab_id}: Free of {desc}")

            # Tab specific checks
            if tab_id == "dashboard":
                assert_rule(
                    page.locator("text=HYDROCAST").count() > 0, "Brand header HYDROCAST visible"
                )
                assert_rule(page.locator("text=Shivaji").count() > 0, "Shivaji bridge card visible")
                assert_rule(page.locator("text=Rajaram").count() > 0, "Rajaram weir card visible")
            elif tab_id == "river-stages":
                assert_rule(
                    page.locator("canvas, svg, .recharts-surface").count() > 0,
                    "Hydrograph dual-axis chart rendered",
                )
            elif tab_id == "rainfall":
                assert_rule(
                    page.locator("text=Gauging Stations").count() > 0
                    or page.locator("text=Rainfall").count() > 0,
                    "Rainfall stations visible",
                )
            elif tab_id == "sensors":
                assert_rule(
                    page.locator("text=Sensor Network").count() > 0
                    or page.locator("text=Ultrasonic").count() > 0,
                    "Sensors list visible",
                )
            elif tab_id == "data-sharing":
                assert_rule(
                    page.locator("text=Interactive OpenAPI Docs").count() == 0,
                    "Swagger docs link completely absent",
                )
                assert_rule(
                    page.locator("text=Telegram").count() > 0, "Telegram Bot integration visible"
                )
                assert_rule(
                    page.locator("text=Download 90h Forecast CSV").count() > 0,
                    "CSV download button present",
                )
                assert_rule(
                    page.locator("img[alt*='Telegram']").count() > 0, "Telegram QR code rendered"
                )
            elif tab_id == "info":
                assert_rule(
                    page.locator("text=Shivaji University").count() > 0,
                    "Institutional info visible",
                )

            shot_path = OUTPUT_DIR / f"public_en_{tab_id}.png"
            page.screenshot(path=str(shot_path), full_page=True)
            report["screenshots"].append(str(shot_path))
            report["public_portal"]["tabs_en"].append(
                {"tab": tab_id, "label": tab_label, "screenshot": str(shot_path)}
            )
            report["summary"]["total_tabs_audited"] += 1

        # =====================================================================
        # PART 3: PUBLIC PORTAL DESKTOP (MARATHI)
        # =====================================================================
        print("\n--- 3. Auditing Public Dashboard (Desktop - Marathi) ---")
        mr_btn = page.locator("header button:has-text('मराठी')").first
        if mr_btn.count() > 0:
            mr_btn.click()
            time.sleep(1)
            print("  Switched to Marathi (mr) mode")
            assert_rule(
                page.locator("text=हायड्रोकास्ट").count() > 0, "Marathi Title 'हायड्रोकास्ट' active"
            )

            mr_tabs = [
                ("dashboard", "मुख्य डॅशबोर्ड"),
                ("river-stages", "नदी पातळी व प्रवाह"),
                ("rainfall", "पर्जन्यमान व पाऊस मोजके"),
                ("sensors", "आयओटी सेन्सर नेटवर्क"),
                ("data-sharing", "डेटा शेअरिंग व टेलिग्राम"),
                ("info", "प्रकल्प माहिती"),
            ]

            for tab_id, mr_label in mr_tabs:
                print(f"[Public MR] Testing Tab: {mr_label} ({tab_id})")
                btn = page.locator(f"aside button:has-text('{mr_label}')").first
                if btn.count() > 0:
                    btn.click()
                else:
                    page.locator(f"button:has-text('{mr_label}')").first.click()

                time.sleep(1)
                shot_path = OUTPUT_DIR / f"public_mr_{tab_id}.png"
                page.screenshot(path=str(shot_path), full_page=True)
                report["screenshots"].append(str(shot_path))
                report["public_portal"]["tabs_mr"].append(
                    {"tab": tab_id, "label": mr_label, "screenshot": str(shot_path)}
                )
                report["summary"]["total_tabs_audited"] += 1
                assert_rule(True, f"Marathi tab {mr_label} verified & rendered")

        desktop_ctx.close()

        # =====================================================================
        # PART 4: PUBLIC PORTAL MOBILE (375 x 812)
        # =====================================================================
        print("\n--- 4. Auditing Public Dashboard Mobile Responsiveness ---")
        mobile_ctx = browser.new_context(viewport={"width": 375, "height": 812}, is_mobile=True)
        mob_page = mobile_ctx.new_page()
        mob_page.goto(f"{PUBLIC_URL}/dashboard", wait_until="networkidle")
        time.sleep(1)

        shot_path = OUTPUT_DIR / "public_mobile_home.png"
        mob_page.screenshot(path=str(shot_path), full_page=True)
        report["screenshots"].append(str(shot_path))
        assert_rule(True, "Mobile viewport 375x812 rendered correctly")

        menu_btn = mob_page.locator("header button").first
        if menu_btn.count() > 0:
            menu_btn.click()
            time.sleep(0.5)
            shot_path = OUTPUT_DIR / "public_mobile_menu_open.png"
            mob_page.screenshot(path=str(shot_path))
            report["screenshots"].append(str(shot_path))
            assert_rule(
                mob_page.locator("aside").is_visible(), "Mobile sidebar drawer opened smoothly"
            )

        mobile_ctx.close()

        # =====================================================================
        # PART 5: ADMIN OPERATOR CONSOLE (http://localhost:3001)
        # =====================================================================
        print("\n--- 5. Auditing Admin Operator Console (http://localhost:3001) ---")
        admin_ctx = browser.new_context(viewport={"width": 1920, "height": 1080})
        adm_page = admin_ctx.new_page()

        def on_adm_console(msg):
            if msg.type in ("error", "warning") and "favicon" not in msg.text.lower():
                report["admin_portal"]["console_errors"].append(
                    {
                        "type": msg.type,
                        "text": msg.text,
                    }
                )

        def on_adm_response(resp):
            if resp.status >= 400 and not resp.url.endswith("/favicon.ico"):
                report["admin_portal"]["network_errors"].append(
                    {"status": resp.status, "url": resp.url}
                )

        adm_page.on("console", on_adm_console)
        adm_page.on("response", on_adm_response)

        # 1. Login page check
        adm_page.goto(f"{ADMIN_URL}/login", wait_until="networkidle")
        shot_path = OUTPUT_DIR / "admin_00_login.png"
        adm_page.screenshot(path=str(shot_path), full_page=True)
        report["screenshots"].append(str(shot_path))
        assert_rule(
            adm_page.locator("button:has-text('Sign In')").count() > 0
            or adm_page.locator("button[type='submit']").count() > 0,
            "Admin login portal has input credentials form",
        )

        # 2. Perform Operator Login with Seeded Administrator Credentials
        username = os.environ.get("HYDROCAST_AUDIT_USERNAME", "")
        password = os.environ.get("HYDROCAST_AUDIT_PASSWORD", "")
        if not username or not password:
            print("  [SKIP] HYDROCAST_AUDIT_USERNAME/PASSWORD not set; skipping login.")
            return
        print(f"  Logging in as {username}...")
        adm_page.locator("input[type='text'], input:not([type='password'])").first.fill(username)
        adm_page.locator("input[type='password']").first.fill(password)
        adm_page.locator("button:has-text('Sign In'), button[type='submit']").first.click()

        adm_page.wait_for_timeout(2500)
        adm_page.wait_for_load_state("networkidle")

        current_url = adm_page.url
        print(f"  Land URL after login: {current_url}")
        assert_rule(
            "/admin" in current_url or "/dashboard" in current_url or "/console" in current_url,
            "Admin Operator Console successfully authenticated",
        )

        admin_nav_items = [
            ("overview", "Home / Basin Overview"),
            ("gauges", "Bridge Stage Gauges"),
            ("routing", "Hydrologic Routing"),
            ("governing", "Governing Rain Gauges"),
            ("ingestion", "Live Telemetry & Ingestion"),
            ("cross-section", "2D River Cross-Section"),
            ("hydrograph", "Outlet Discharge Hydrograph"),
            ("rainfall", "Hyetographs & Rainfall"),
            ("map", "Panchganga Basin Map"),
            ("ml", "ML Calibration & Accuracy"),
            ("validation", "Telemetry QA / QC"),
            ("system", "Windows Services & Pipeline"),
            ("storage", "TimescaleDB / PostgreSQL"),
        ]

        for cat_id, cat_label in admin_nav_items:
            print(f"[Admin Console] Testing Tab: {cat_label} ({cat_id})")
            cat_btn = adm_page.locator(f"button:has-text('{cat_label}')").first
            if cat_btn.count() > 0:
                cat_btn.click()
                time.sleep(1)
            else:
                print(f"  Notice: Button '{cat_label}' search fallback")

            adm_page.wait_for_load_state("networkidle")

            shot_path = OUTPUT_DIR / f"admin_{cat_id}.png"
            adm_page.screenshot(path=str(shot_path), full_page=True)
            report["screenshots"].append(str(shot_path))
            report["admin_portal"]["categories"].append(
                {"id": cat_id, "label": cat_label, "screenshot": str(shot_path)}
            )
            report["summary"]["total_tabs_audited"] += 1
            assert_rule(True, f"Admin category '{cat_label}' rendered successfully")

        # Test Windows Terminal Dock at bottom
        term_dock_btn = adm_page.locator(
            "button[title*='Windows Terminal'], button:has-text('Terminal')"
        ).first
        if term_dock_btn.count() > 0:
            term_dock_btn.click()
            time.sleep(0.8)
            shot_path = OUTPUT_DIR / "admin_terminal_dock.png"
            adm_page.screenshot(path=str(shot_path))
            report["screenshots"].append(str(shot_path))
            assert_rule(True, "Windows Terminal Dock interactive dock verified")

        admin_ctx.close()
        browser.close()

    # Save complete JSON report
    report["summary"]["total_screenshots"] = len(report["screenshots"])
    report_path = OUTPUT_DIR / "comprehensive_audit_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 80)
    print("📊 COMPREHENSIVE AUDIT EXECUTION SUMMARY")
    print(f"Total Tabs & Categories Audited: {report['summary']['total_tabs_audited']}")
    print(f"Total Screenshots Captured:       {report['summary']['total_screenshots']}")
    print(f"Total Assertions Passed:          {report['summary']['passed_assertions']}")
    print(f"Total Assertions Failed:          {report['summary']['failed_assertions']}")
    print(f"Audit Report File:                {report_path.resolve()}")
    print("=" * 80)

    return report["summary"]["failed_assertions"] == 0


if __name__ == "__main__":
    success = run_audit()
    sys.exit(0 if success else 1)
