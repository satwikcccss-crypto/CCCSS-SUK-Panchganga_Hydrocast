"""
scripts/verify_m3_endpoints.py
==============================
Live endpoint prober for HydroCast Public API (Port 8000) and
Operator Console API (Port 8001).
"""

import gzip
import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple


def probe(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    req_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Encoding": "gzip, deflate",
    }
    if headers:
        req_headers.update(headers)

    body_bytes = None
    if data is not None:
        body_bytes = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body_bytes, headers=req_headers, method=method)
    result = {
        "url": url,
        "method": method,
        "status": None,
        "headers": {},
        "body_preview": "",
        "body_len": 0,
        "error": None,
        "is_gzip": False,
        "x_request_id": None,
    }

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result["status"] = resp.status
            result["headers"] = dict(resp.headers)
            raw = resp.read()
            result["body_len"] = len(raw)
            result["content_type"] = resp.headers.get("Content-Type", "")
            encoding = resp.headers.get("Content-Encoding", "").lower()
            if "gzip" in encoding:
                result["is_gzip"] = True
                try:
                    decompressed = gzip.decompress(raw)
                    result["body_text"] = decompressed.decode("utf-8", errors="replace")
                except Exception as ex:
                    result["body_text"] = f"<gzip decompression error: {ex}>"
            else:
                result["body_text"] = raw.decode("utf-8", errors="replace")
            result["body_preview"] = result["body_text"][:200]
            result["x_request_id"] = resp.headers.get("X-Request-ID")
    except urllib.error.HTTPError as he:
        result["status"] = he.code
        result["headers"] = dict(he.headers)
        raw = he.read()
        result["body_len"] = len(raw)
        result["content_type"] = he.headers.get("Content-Type", "")
        encoding = he.headers.get("Content-Encoding", "").lower()
        if "gzip" in encoding:
            result["is_gzip"] = True
            try:
                decompressed = gzip.decompress(raw)
                result["body_text"] = decompressed.decode("utf-8", errors="replace")
            except Exception:
                result["body_text"] = raw.decode("utf-8", errors="replace")
        else:
            result["body_text"] = raw.decode("utf-8", errors="replace")
        result["body_preview"] = result["body_text"][:200]
        result["x_request_id"] = he.headers.get("X-Request-ID")
        result["error"] = f"HTTPError {he.code}"
    except Exception as ex:
        result["error"] = str(ex)

    return result


def main():
    print("=" * 80)
    print("HYDROCAST M3 LIVE ENDPOINT VERIFICATION")
    print("=" * 80)

    # 1. Probes on Port 8000
    p8000_routes = [
        # System & Probes
        ("GET", "http://127.0.0.1:8000/healthz/live", None, None),
        ("GET", "http://127.0.0.1:8000/healthz/ready", None, None),
        ("GET", "http://127.0.0.1:8000/metrics", None, None),
        ("GET", "http://127.0.0.1:8000/api/v1/ready", None, None),
        ("GET", "http://127.0.0.1:8000/api/v1/health", None, None),
        ("GET", "http://127.0.0.1:8000/api/v1/status", None, None),
        # Hydrology & Stage
        ("GET", "http://127.0.0.1:8000/api/v1/rainfall/ecmwf", None, None),
        ("GET", "http://127.0.0.1:8000/api/v1/rainfall/stations", None, None),
        ("GET", "http://127.0.0.1:8000/api/v1/rainfall/gauges", None, None),
        ("GET", "http://127.0.0.1:8000/api/v1/runoff/hydrograph", None, None),
        ("GET", "http://127.0.0.1:8000/api/v1/runoff/summary", None, None),
        ("GET", "http://127.0.0.1:8000/api/v1/runoff/stage/SHIVAJI_BRIDGE", None, None),
        ("GET", "http://127.0.0.1:8000/api/v1/bridge/SHIVAJI_BRIDGE", None, None),
        ("GET", "http://127.0.0.1:8000/api/v1/alerts", None, None),
        ("GET", "http://127.0.0.1:8000/api/v1/alerts/bulletin", None, None),
        ("GET", "http://127.0.0.1:8000/api/v1/alerts/bulletin/pdf", None, None),
        # Feeds
        ("GET", "http://127.0.0.1:8000/api/v1/water-levels", None, None),
        ("GET", "http://127.0.0.1:8000/api/SUK_hydrocast_v1", None, None),
        ("GET", "http://127.0.0.1:8000/api/v1/hydrocast/complete", None, None),
        # Sensors
        ("GET", "http://127.0.0.1:8000/api/v1/sensors/live", None, None),
        ("GET", "http://127.0.0.1:8000/api/v1/sensors/registry", None, None),
        # Pipeline
        ("GET", "http://127.0.0.1:8000/api/v1/pipeline", None, None),
        ("GET", "http://127.0.0.1:8000/api/v1/pipeline/history", None, None),
        ("GET", "http://127.0.0.1:8000/api/v1/dashboard", None, None),
        ("GET", "http://127.0.0.1:8000/api/v1/runs", None, None),
    ]

    results_8000 = []
    print("\n--- PROBING PORT 8000 (PUBLIC API) ---")
    for method, url, hdrs, payload in p8000_routes:
        res = probe(url, method=method, headers=hdrs, data=payload)
        results_8000.append(res)
        x_req = res["x_request_id"] or "MISSING"
        gzip_status = "GZIP" if res["is_gzip"] else f"{res['body_len']}B raw"
        print(f"[{res['status']}] {method} {url} | ReqID: {x_req[:12]} | Size: {gzip_status}")
        if res["error"] and res["status"] not in (200, 503):
            print(f"    ERROR: {res['error']} - {res['body_preview']}")

    # 2. Login on Port 8001 to get admin JWT
    print("\n--- PROBING PORT 8001 (OPERATOR CONSOLE API) ---")
    login_res = probe(
        "http://127.0.0.1:8001/api/v1/admin/auth/login",
        method="POST",
        data={"username": "admin", "password": "REPLACE_ME_ADMIN_PASSWORD"},
    )
    print(f"[{login_res['status']}] POST http://127.0.0.1:8001/api/v1/admin/auth/login")
    token = None
    if login_res["status"] == 200:
        token_data = json.loads(login_res["body_text"])
        token = token_data.get("access_token")
        print(f"    Admin Token acquired: {token[:20]}...")
    else:
        print(f"    Failed to acquire admin token: {login_res['body_preview']}")

    admin_headers = {"Authorization": f"Bearer {token}"} if token else {}

    p8001_routes = [
        ("GET", "http://127.0.0.1:8001/healthz/live", None, None),
        ("GET", "http://127.0.0.1:8001/api/v1/admin/me", admin_headers, None),
        ("GET", "http://127.0.0.1:8001/api/v1/admin/runtime", admin_headers, None),
        ("GET", "http://127.0.0.1:8001/api/v1/admin/pipeline", admin_headers, None),
        (
            "POST",
            "http://127.0.0.1:8001/api/v1/admin/trigger-run",
            admin_headers,
            {"async_mode": True},
        ),
        ("GET", "http://127.0.0.1:8001/api/v1/admin/audit-logs", admin_headers, None),
    ]

    results_8001 = [login_res]
    for method, url, hdrs, payload in p8001_routes:
        res = probe(url, method=method, headers=hdrs, data=payload)
        results_8001.append(res)
        print(f"[{res['status']}] {method} {url}")
        print(f"    Preview: {res['body_preview'][:120]}")

    # Summary
    all_results = results_8000 + results_8001
    errors_500 = [r for r in all_results if r["status"] == 500]
    print("\n" + "=" * 80)
    print("SUMMARY OF PROBES:")
    print(f"Total endpoints probed: {len(all_results)}")
    print(f"500 Internal Server Errors: {len(errors_500)}")
    print("=" * 80)


if __name__ == "__main__":
    main()
