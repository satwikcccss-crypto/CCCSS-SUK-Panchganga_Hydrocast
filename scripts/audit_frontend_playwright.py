import os
import sys
import json
import time
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = r"E:\Hydrocast Windows Server\historical_checks\playwright_audit"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def audit_frontend():
    results = {
        "public": {"pages": [], "errors": [], "warnings": []},
        "admin": {"pages": [], "errors": [], "warnings": []}
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        
        # ══════════════════════════════════════════════════════════════
        # 1. AUDIT PUBLIC DASHBOARD (PORT 3000)
        # ══════════════════════════════════════════════════════════════
        page = context.new_page()
        public_console_errors = []
        page.on("console", lambda msg: public_console_errors.append(f"[{msg.type}] {msg.text}") if msg.type == "error" else None)
        page.on("pageerror", lambda err: public_console_errors.append(f"[UNHANDLED EXCEPTION] {err}"))

        print("\n--- AUDITING PUBLIC DASHBOARD (http://localhost:3000/dashboard) ---")
        try:
            page.goto("http://localhost:3000/dashboard", timeout=15000, wait_until="networkidle")
            time.sleep(2)
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "public_01_dashboard.png"))
            results["public"]["pages"].append({"tab": "Executive Dashboard", "status": "OK", "url": page.url})

            # Check all public navigation tabs
            tabs = [
                ("River Stages & Hydrograph", "public_02_river_stages.png"),
                ("Cross Section View", "public_03_cross_section.png"),
                ("Rainfall & Rain Gauges", "public_04_rainfall.png"),
                ("Project Information", "public_05_project_info.png")
            ]

            for tab_label, filename in tabs:
                print(f"Clicking public tab: {tab_label}")
                btn = page.locator(f"button:has-text('{tab_label}')").first
                if btn.count() > 0:
                    btn.click()
                    time.sleep(1.5)
                    page.screenshot(path=os.path.join(SCREENSHOT_DIR, filename))
                    results["public"]["pages"].append({"tab": tab_label, "status": "OK"})
                else:
                    results["public"]["pages"].append({"tab": tab_label, "status": "BUTTON_NOT_FOUND"})

        except Exception as e:
            results["public"]["errors"].append(str(e))
            print(f"Public audit error: {e}")

        results["public"]["console_errors"] = public_console_errors
        page.close()

        # ══════════════════════════════════════════════════════════════
        # 2. AUDIT OPERATOR CONSOLE (PORT 3001)
        # ══════════════════════════════════════════════════════════════
        admin_page = context.new_page()
        admin_console_errors = []
        admin_page.on("console", lambda msg: admin_console_errors.append(f"[{msg.type}] {msg.text}") if msg.type == "error" else None)
        admin_page.on("pageerror", lambda err: admin_console_errors.append(f"[UNHANDLED EXCEPTION] {err}"))

        print("\n--- AUDITING OPERATOR CONSOLE (http://localhost:3001/admin) ---")
        try:
            admin_page.goto("http://localhost:3001/admin", timeout=15000, wait_until="networkidle")
            time.sleep(2)
            admin_page.screenshot(path=os.path.join(SCREENSHOT_DIR, "admin_01_home.png"))
            results["admin"]["pages"].append({"category": "Home / Basin Overview", "status": "OK", "url": admin_page.url})

            admin_categories = [
                ("Bridge Stage Gauges", "admin_02_bridge_gauges.png"),
                ("Subbasin & Reach Routing", "admin_03_routing.png"),
                ("Governing & Rain Gauges", "admin_04_governing.png"),
                ("Live Ingestion & Telemetry", "admin_05_ingestion.png"),
                ("River Cross-Section", "admin_06_cross_section.png"),
                ("Hydrograph & Stage", "admin_07_hydrograph.png"),
                ("ML Recalibration", "admin_08_ml.png"),
                ("Run Ledger & Accuracy", "admin_09_validation.png"),
                ("Pipeline & Diagnostics", "admin_10_pipeline.png"),
                ("Database & Host Health", "admin_11_database.png"),
            ]

            for cat_label, filename in admin_categories:
                print(f"Clicking admin category: {cat_label}")
                nav_item = admin_page.locator(f"button:has-text('{cat_label}')").first
                if nav_item.count() > 0:
                    nav_item.click()
                    time.sleep(1.5)
                    admin_page.screenshot(path=os.path.join(SCREENSHOT_DIR, filename))
                    results["admin"]["pages"].append({"category": cat_label, "status": "OK"})
                else:
                    results["admin"]["pages"].append({"category": cat_label, "status": "BUTTON_NOT_FOUND"})

        except Exception as e:
            results["admin"]["errors"].append(str(e))
            print(f"Admin audit error: {e}")

        results["admin"]["console_errors"] = admin_console_errors
        admin_page.close()
        browser.close()

    # Save detailed JSON report
    report_path = os.path.join(SCREENSHOT_DIR, "audit_report.json")
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)

    print("\n--- AUDIT COMPLETE ---")
    print(f"Report saved to: {report_path}")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    audit_frontend()
