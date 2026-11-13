#!/usr/bin/env python3
"""
Comprehensive Playwright Audit for HydroCast Frontends
Audits EVERY page, EVERY button, EVERY interactive element across both frontends.
Checks for: hardcoded/stale data, console errors, broken links, failed API calls.
"""

import json
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

# ── Configuration ───────────────────────────────────────────────────────────
PUBLIC_BASE = "http://localhost:3000"
ADMIN_BASE = "http://localhost:3001"
API_BASE = "http://localhost:8000"

PUBLIC_PAGES = [
    "/",
    "/dashboard",
    "/console",
    "/login",
    "/admin",
    "/auth/callback",
    "/offline",
]

ADMIN_PAGES = [
    "/",
    "/dashboard",
    "/console",
    "/login",
    "/login/forgot",
    "/login/reset",
    "/admin",
    "/auth/callback",
]

# Known hardcoded/stale values that should NOT appear in rendered output
HARDCODED_PATTERNS = [
    (r"532\.63", "hardcoded Shivaji stage 532.63"),
    (r"538\.86", "hardcoded Rajaram stage 538.86"),
    (r"533\.54", "hardcoded Shivaji stage 533.54"),
    (r"538\.45", "hardcoded Shivaji peak 538.45"),
    (r"\b91\.1\b", "hardcoded discharge 91.1"),
    (r"541\.02", "hardcoded CrossSection baseStage 541.02"),
    (r"533\.40", "hardcoded CrossSection baseStage 533.40"),
    (r"18420", "hardcoded Worker Daemon PID"),
    (r"10:55:0[2-6]", "hardcoded terminal timestamps"),
    (r"sample_count=12", "hardcoded telemetry sample count"),
    (r"535\.770", "hardcoded Rajaram crest"),
    (r"542\.100", "hardcoded alert stage"),
    (r"530\.180", "hardcoded gauge zero"),
]

# ── Audit Results ───────────────────────────────────────────────────────────
results = {
    "audit_time": datetime.now().isoformat(),
    "public_pages": {},
    "admin_pages": {},
    "api_endpoints": {},
    "errors": [],
    "hardcoded_findings": [],
    "summary": {},
}

def check_hardcoded(text, source):
    """Check text for hardcoded/stale values."""
    findings = []
    for pattern, desc in HARDCODED_PATTERNS:
        if re.search(pattern, text):
            findings.append({"source": source, "pattern": pattern, "description": desc, "matched": True})
    return findings


def audit_page(browser, base_url, page_path, frontend_name):
    """Audit a single page: visit, click buttons, check errors, check hardcoded data."""
    context = browser.new_context()
    page = context.new_page()

    page_errors = []
    console_errors = []
    network_errors = []
    buttons_clicked = []
    buttons_failed = []
    hardcoded = []

    # Console error listener
    def on_console(msg):
        if msg.type in ("error", "warning"):
            console_errors.append({
                "type": msg.type,
                "text": msg.text[:200],
                "location": msg.location.get("url", "") if msg.location else "",
            })

    # Page error listener
    def on_page_error(err):
        page_errors.append(str(err)[:200])

    # Failed request listener
    def on_request_failed(request):
        network_errors.append({
            "url": request.url[:150],
            "failure": request.failure.get("errorText", "") if request.failure else "",
        })

    page.on("console", on_console)
    page.on("pageerror", on_page_error)
    page.on("requestfailed", on_request_failed)

    page_result = {
        "url": f"{base_url}{page_path}",
        "status": None,
        "title": None,
        "console_errors": console_errors,
        "page_errors": page_errors,
        "network_errors": network_errors,
        "buttons": {"clicked": buttons_clicked, "failed": buttons_failed},
        "hardcoded_findings": hardcoded,
        "links": [],
        "inputs": [],
        "forms": [],
    }

    try:
        response = page.goto(f"{base_url}{page_path}", wait_until="networkidle", timeout=30000)
        page_result["status"] = response.status if response else None
        page_result["title"] = page.title()
    except Exception as e:
        page_result["status"] = "ERROR"
        page_result["page_errors"].append(str(e)[:200])
        results[frontend_name + "_pages"][page_path] = page_result
        context.close()
        return

    # Get all page text and check for hardcoded values
    try:
        body_text = page.locator("body").text_content() or ""
        hardcoded.extend(check_hardcoded(body_text, f"{frontend_name}:{page_path} body"))
    except Exception as e:
        page_result["page_errors"].append(f"body text: {str(e)[:100]}")

    # Get all links
    try:
        links = page.locator("a").all()
        for link in links:
            try:
                href = link.get_attribute("href") or ""
                text = (link.inner_text() or "").strip()[:50]
                page_result["links"].append({"href": href, "text": text})
            except:
                pass
    except:
        pass

    # Get all inputs
    try:
        inputs = page.locator("input").all()
        for inp in inputs:
            try:
                itype = inp.get_attribute("type") or "text"
                name = inp.get_attribute("name") or ""
                placeholder = inp.get_attribute("placeholder") or ""
                page_result["inputs"].append({"type": itype, "name": name, "placeholder": placeholder})
                # Check placeholder for hardcoded values
                hardcoded.extend(check_hardcoded(placeholder, f"{frontend_name}:{page_path} input[{name}]"))
            except:
                pass
    except:
        pass

    # Get all buttons and try to click them
    try:
        buttons = page.locator("button").all()
        print(f"    Found {len(buttons)} buttons on {page_path}")
        for i, btn in enumerate(buttons):
            btn_text = (btn.inner_text() or "").strip()[:50] or f"btn-{i}"
            btn_type = btn.get_attribute("type") or "button"
            btn_disabled = btn.is_disabled() if btn.is_visible() else True

            page_result["buttons"]["clicked"].append({
                "index": i,
                "text": btn_text,
                "type": btn_type,
                "disabled": btn_disabled,
                "visible": btn.is_visible(),
            })

            if btn_disabled or not btn.is_visible():
                continue

            try:
                # Try clicking - but be careful with destructive actions
                btn.click(timeout=5000)
                page.wait_for_timeout(500)
            except Exception as e:
                buttons_failed.append({
                    "index": i,
                    "text": btn_text,
                    "error": str(e)[:150],
                })
                page_result["buttons"]["failed"].append({
                    "index": i,
                    "text": btn_text,
                    "error": str(e)[:150],
                })
    except Exception as e:
        page_result["page_errors"].append(f"button scan: {str(e)[:100]}")

    # Check all visible text for hardcoded values
    try:
        all_text = page.locator("body").inner_text() or ""
        hardcoded.extend(check_hardcoded(all_text, f"{frontend_name}:{page_path} inner_text"))
    except:
        pass

    page_result["hardcoded_findings"] = hardcoded
    results[frontend_name + "_pages"][page_path] = page_result

    context.close()


def audit_api_endpoints():
    """Audit all backend API endpoints."""
    endpoints = [
        "/api/v1/status",
        "/api/v1/runoff/summary",
        "/api/v1/runoff/hydrograph",
        "/api/v1/runoff/stage/SHIVAJI_BRIDGE",
        "/api/v1/runoff/stage/RAJARAM_BRIDGE",
        "/api/v1/rainfall/ecmwf",
        "/api/v1/rainfall/stations",
        "/api/v1/rainfall/gauges",
        "/api/v1/alerts",
        "/api/v1/accuracy",
    ]

    for ep in endpoints:
        try:
            req = urllib.request.Request(f"{API_BASE}{ep}")
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
                results["api_endpoints"][ep] = {
                    "status": r.status,
                    "ok": True,
                    "sample": str(data)[:200],
                }
        except Exception as e:
            results["api_endpoints"][ep] = {
                "status": None,
                "ok": False,
                "error": str(e)[:200],
            }


def main():
    import urllib.request

    print("=" * 70)
    print("HYDROCAST COMPREHENSIVE PLAYWRIGHT AUDIT")
    print("=" * 70)
    print(f"Start time: {datetime.now().isoformat()}")
    print()

    # Audit API endpoints first
    print("\n--- Auditing Backend API Endpoints ---")
    audit_api_endpoints()
    for ep, info in results["api_endpoints"].items():
        status = "OK" if info["ok"] else "FAIL"
        print(f"  {status} {ep} ({info.get('status', 'N/A')})")

    # Audit public frontend
    print("\n--- Auditing Public Frontend ---")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for page_path in PUBLIC_PAGES:
            print(f"\n  Auditing: {page_path}")
            audit_page(browser, PUBLIC_BASE, page_path, "public_pages")
        browser.close()

    # Audit admin frontend
    print("\n--- Auditing Admin Frontend ---")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for page_path in ADMIN_PAGES:
            print(f"\n  Auditing: {page_path}")
            audit_page(browser, ADMIN_BASE, page_path, "admin_pages")
        browser.close()

    # Generate summary
    total_pages = len(results["public_pages"]) + len(results["admin_pages"])
    total_errors = sum(
        len(pg.get("page_errors", [])) + len(pg.get("console_errors", [])) + len(pg.get("network_errors", []))
        for pg in list(results["public_pages"].values()) + list(results["admin_pages"].values())
    )
    total_hardcoded = sum(
        len(pg.get("hardcoded_findings", []))
        for pg in list(results["public_pages"].values()) + list(results["admin_pages"].values())
    )
    failed_buttons = sum(
        len(pg.get("buttons", {}).get("failed", []))
        for pg in list(results["public_pages"].values()) + list(results["admin_pages"].values())
    )

    results["summary"] = {
        "total_pages_audited": total_pages,
        "total_errors": total_errors,
        "total_hardcoded_findings": total_hardcoded,
        "total_failed_buttons": failed_buttons,
        "api_endpoints_ok": sum(1 for e in results["api_endpoints"].values() if e["ok"]),
        "api_endpoints_total": len(results["api_endpoints"]),
    }

    # Write report
    report_path = Path("E:/Hydrocast Windows Server/playwright_audit_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print("AUDIT SUMMARY")
    print("=" * 70)
    print(f"Pages audited: {total_pages}")
    print(f"Total errors: {total_errors}")
    print(f"Hardcoded findings: {total_hardcoded}")
    print(f"Failed buttons: {failed_buttons}")
    print(f"API endpoints OK: {results['summary']['api_endpoints_ok']}/{results['summary']['api_endpoints_total']}")
    print(f"\nFull report: {report_path}")

    # Print hardcoded findings
    if total_hardcoded > 0:
        print("\n--- HARDCODED/STALE DATA FOUND ---")
        for pg_name, pg_data in list(results["public_pages"].items()) + list(results["admin_pages"].items()):
            for hf in pg_data.get("hardcoded_findings", []):
                print(f"  [{pg_name}] {hf['description']} in {hf['source']}")
    else:
        print("\nNo hardcoded/stale data found!")

    if total_errors > 0:
        print("\n--- ERRORS ---")
        for pg_name, pg_data in list(results["public_pages"].items()) + list(results["admin_pages"].items()):
            for err in pg_data.get("page_errors", []):
                print(f"  [{pg_name}] Page error: {err}")
            for err in pg_data.get("console_errors", []):
                print(f"  [{pg_name}] Console {err['type']}: {err['text'][:100]}")
            for err in pg_data.get("network_errors", []):
                print(f"  [{pg_name}] Network: {err['url']} -> {err['failure'][:100]}")

    print("\nAudit complete.")


if __name__ == "__main__":
    main()