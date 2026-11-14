# OpenAPI Export & SDK Readiness

This document describes how to export HydroCast API schemas and generate client integrations for the Windows Server deployment.

## 1) Interactive API docs (OpenAPI playground)
When the FastAPI app is running, the built-in OpenAPI playground is available at:
- **Public API (default 8000):** `/docs` (Swagger UI), `/redoc`, `/openapi.json`
- **Admin API (default 8001, if deployed separately):** `/docs`, `/redoc`, `/openapi.json`

Use these for interactive exploration, request/response inspection, and schema discovery.

## 2) Export OpenAPI schema (automated)
Use the export script to generate a clean schema file for client generation or sharing:

```bash
# Public API schema
python scripts/export_openapi.py --app public --out openapi.json

# Admin API schema (if separate admin app is used)
python scripts/export_openapi.py --app admin --out openapi-admin.json
```

Notes:
- Run from the repository root with backend dependencies installed.
- The script imports the FastAPI app and writes `app.openapi()`; it does not start a server.
- Re-export after API changes to keep generated clients in sync.

## 3) New API capabilities (Windows Server upgrades)
- **Conditional requests (ETag/304):** supported on selected read endpoints (e.g. `/api/v1/dashboard`, `/api/v1/runoff/summary`, `/api/v1/runoff/hydrograph`). Clients may send `If-None-Match` and handle `304 Not Modified`.
- **Partial responses:** `GET /api/v1/runoff/summary?fields=...` supports comma-separated fields/aliases (examples: `peak_q`, `stage_m`, `alert_level`, `lead_hours_to_peak`, and top-level keys like `summary`, `bridges`, `hydrograph`).
- **PDF bulletin:** `GET /api/v1/alerts/bulletin/pdf` streams an `application/pdf` flood advisory bulletin generated from the latest bulletin payload.

## 4) Python client integration (SDK readiness)
Until a packaged SDK is published, use one of these approaches:

### A. Generated client (recommended for external integrators)
Generate a typed client from the exported schema using tools such as `openapi-python-client` or `openapi-generator`.

Example workflow (tooling installed separately):
```bash
python scripts/export_openapi.py --app public --out openapi.json
openapi-python-client generate --path openapi.json
```

### B. Lightweight direct integration (requests/httpx)
```python
import requests

BASE = "http://localhost:8000"
r = requests.get(f"{BASE}/api/v1/runoff/summary", params={"fields": "peak_q,stage_m,alert_level"}, timeout=10)
r.raise_for_status()
data = r.json()
print(data)

# Conditional request example
etag = r.headers.get("ETag")
r2 = requests.get(f"{BASE}/api/v1/runoff/summary", headers={"If-None-Match": etag} if etag else None, timeout=10)
print(r2.status_code)  # 200 or 304
```

### C. PDF bulletin download
```python
import requests

resp = requests.get("http://localhost:8000/api/v1/alerts/bulletin/pdf", timeout=15)
resp.raise_for_status()
with open("hydrocast_bulletin.pdf", "wb") as f:
    f.write(resp.content)
```

## 5) Packaging note
A published package (e.g. `pip install hydrocast-client`) is a separate release/distribution task (packaging, versioning, registry publish, maintenance). The repository currently provides **schema export + client-generation readiness + integration examples** to enable rapid SDK/client creation.
