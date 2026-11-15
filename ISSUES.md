# 📋 HydroCast Issue Tracker & Feature Register

This register documents all tracked issues, bug fixes, security hardening, and feature implementations for the **HydroCast Panchganga Flood Forecasting System** (Windows Server Edition).

All issues correspond directly to the official GitHub Issue tracker at [satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues).

---

## 🎯 Summary by Release Milestone

| Milestone | Tag | Issues Closed | Issues Open | Focus Area |
|:---|:---|:---:|:---:|:---|
| **windows-v1.4.0** | `windows-v1.4.0` | 8 | 1 | IoT Sensor Physics, SIM Signal Strength, Pipeline Exceptions, Auth Restoration |
| **windows-v1.3.0** | `windows-v1.3.0` | 6 | 0 | Role-Based Access Control (RBAC), ETag / 304, PDF Advisory Bulletin, WS Security |
| **windows-v1.2.0** | `windows-v1.2.0` | 3 | 0 | Prometheus Observability, Windows Watchdog recovery, Backup Automation |
| **windows-v1.1.0** | `windows-v1.1.0` | 3 | 0 | Operator Console Auth Boundary, Next.js Proxy Hardening, Data Honesty |
| **windows-v1.0.0** | `windows-v1.0.0` | 5 | 0 | Modular Backend Architecture, Process Safety, Production Hardening |

---

## 🚀 Active / Open Issues

| Issue # | Title | Category | Severity | Milestone | Status |
|:---:|:---|:---:|:---:|:---:|:---:|
| [#45](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/45) | [Infrastructure]: Institutional DNS domain assignment (`hydrocast.unishivaji.ac.in`) | Operations | Medium | `windows-v1.4.0` | 🟡 **OPEN** (Awaiting IT delegation) |

---

## 📦 Closed / Resolved Issues & Features Register

### Release: `windows-v1.4.0` (2026-11-15)

#### [#21](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/21) — [Bug]: Critical physics bug — incorrect sensor unit conversion for Nitawade and Ichalkaranji
- **Category:** `bug`, `telemetry`
- **Severity:** 🔴 **Critical**
- **Impact:** All 3 stations were applying feet-to-meters conversion (`raw * 0.3048`). Only Shivaji Bridge (SS) sends data in feet. Nitawade (NW) and Ichalkaranji (IK) send meters directly. Nitawade water level was computed as `4.16 m MSL` (impossible river bottom).
- **Resolution:** Added explicit per-station `"unit": "feet"` vs `"unit": "meters"` in `backend/thingspeak/multi_station.py`. Stage calculations now convert only when `unit == "feet"`.
  - **SS:** `549.35 - (58.13 ft * 0.3048) = 531.63 m MSL` ✅
  - **NW:** `552.80 - 4.64 m = 548.16 m MSL` (matches ThingSpeak precomputed field2) ✅
  - **IK:** `543.71 - 15.87 m = 527.84 m MSL` ✅
- **Status:** 🟢 **CLOSED**

#### [#22](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/22) — [Bug]: ThingSpeak multi-station telemetry returns `NOT_CONFIGURED` without `.env` auto-load
- **Category:** `bug`, `telemetry`, `backend`
- **Severity:** 🟠 **High**
- **Impact:** Stations failed to retrieve telemetry when `multi_station.py` was executed in isolation because environment variables were not loaded yet.
- **Resolution:** Added `python-dotenv` auto-load at root and provided fallback default channel IDs (`3424513`, `3417870`, `3417872`).
- **Status:** 🟢 **CLOSED**

#### [#23](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/23) — [Bug]: Nitawade sensor voltage misinterprets precomputed stage as 548.16 V
- **Category:** `bug`, `telemetry`
- **Severity:** 🟡 **Medium**
- **Impact:** UI showed an impossible battery voltage of `548.16 V` for Nitawade station.
- **Resolution:** Channel 3417870 `field2` is precomputed level (`Level`), not battery voltage. Set `has_voltage: False` and updated field map to `{distance: field1, level: field2, altitude: field3}`.
- **Status:** 🟢 **CLOSED**

#### [#24](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/24) — [Feature]: Surface SIM Signal Strength (SS) for Shivaji Bridge IoT station
- **Category:** `enhancement`, `telemetry`, `frontend`
- **Severity:** 🟢 **Feature**
- **Resolution:** ThingSpeak Channel 3424513 `field3` is SIM signal percentage (0–100%). Surfaced in `multi_station.py`, public dashboard `SensorNetworkPanel`, and operator console `LiveTelemetryPanel`.
- **Status:** 🟢 **CLOSED**

#### [#25](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/25) — [Bug]: Critical pipeline crash due to undefined logger in `steps.py:110`
- **Category:** `bug`, `backend`
- **Severity:** 🔴 **Critical**
- **Impact:** Unhandled `NameError: 'log' is not defined` crashed the forecast exception handler during telemetry validation failures.
- **Resolution:** Added `import logging; log = logging.getLogger(__name__)` to `backend/service/pipeline/steps.py`.
- **Status:** 🟢 **CLOSED**

#### [#26](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/26) — [Bug]: Lead admin email alert failure on comma-separated recipient lists
- **Category:** `bug`, `backend`, `operations`
- **Severity:** 🟠 **High**
- **Impact:** When `LEAD_ADMIN_EMAIL` had multiple comma-separated emails, mail delivery failed due to multiple addresses in a single header field.
- **Resolution:** Fixed `get_lead_admin_email()` in `backend/alerts/admin_notifier.py` to split on commas and deliver to primary address.
- **Status:** 🟢 **CLOSED**

#### [#27](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/27) — [Security]: Server-side administrative account provisioning
- **Category:** `security`, `database`
- **Severity:** 🟠 **High**
- **Resolution:** Provisioned all 5 production administrator accounts directly in PostgreSQL; repository seed remains a placeholder template.
- **Status:** 🟢 **CLOSED**

#### [#46](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/46) — [Telemetry]: Standardize `THINGSPEAK_API_KEY` vs `THINGSPEAK_READ_API_KEY` across modules
- **Category:** `telemetry`, `enhancement`
- **Severity:** 🟢 **Resolved**
- **Resolution:** Harmonized `THINGSPEAK_READ_API_KEY` with fallback to `THINGSPEAK_API_KEY` across `thingspeak_gauge.py`, `failsafe_telemetry.py`, and `realtime_telemetry_validator.py`. Also pinned `field1` extraction in `thingspeak_gauge.py` to prevent reading sensor battery voltage or SIM signal strength as water level.
- **Status:** 🟢 **CLOSED**

---

### Release: `windows-v1.3.0` (2026-11-14)

#### [#28](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/28) — [Feature]: Conditional HTTP caching (ETag / HTTP 304) for bandwidth efficiency
- **Category:** `enhancement`, `backend`
- **Resolution:** Implemented `ETag` and `If-None-Match` caching on summary, hydrograph, and dashboard endpoints. Returns HTTP 304 Not Modified when unchanged.
- **Status:** 🟢 **CLOSED**

#### [#29](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/29) — [Feature]: Partial response query filtering (`?fields=`) on summary API
- **Category:** `enhancement`, `backend`
- **Resolution:** Added field filtering query parameter on `/api/v1/runoff/summary` to support lightweight client queries.
- **Status:** 🟢 **CLOSED**

#### [#30](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/30) — [Feature]: On-premises PDF flood advisory bulletin generator
- **Category:** `enhancement`, `backend`
- **Resolution:** Created `GET /api/v1/alerts/bulletin/pdf` delivering official printable flood advisory bulletins directly from current cycle data.
- **Status:** 🟢 **CLOSED**

#### [#31](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/31) — [Security]: Role-Based Access Control (RBAC) separating Official Viewers from Operators
- **Category:** `security`, `backend`, `frontend`
- **Resolution:** Restricts institutional viewers (`role=viewer`) to read-only views; administrative routes require `role=admin`. Blocked attempts logged as `VIEWER_BLOCKED`.
- **Status:** 🟢 **CLOSED**

#### [#32](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/32) — [Security]: Admin WebSocket endpoint pre-handshake authentication
- **Category:** `security`, `backend`
- **Resolution:** Mandatory JWT validation on `/ws/admin/logs` and `/ws/admin/telemetry`; unauthorized connections rejected with close code `1008`.
- **Status:** 🟢 **CLOSED**

#### [#33](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/33) — [Database]: Composite index on `bridge_stage_forecast` for high-speed lookups
- **Category:** `database`, `backend`
- **Resolution:** Alembic migration `002_add_forecast_run_indexes` added composite index `idx_bsf_run_site_lead(forecast_run_id, site_id, lead_hours)`.
- **Status:** 🟢 **CLOSED**

---

### Release: `windows-v1.2.0` (2026-11-13)

#### [#34](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/34) — [Feature]: Prometheus observability metrics enrichment (`/metrics`)
- **Category:** `enhancement`, `operations`, `backend`
- **Resolution:** Safe scrape-time gauge updates for DB pools, cycle status, and per-site alert levels.
- **Status:** 🟢 **CLOSED**

#### [#35](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/35) — [Operations]: Windows Watchdog recovery monitoring for Admin API port 8001
- **Category:** `operations`
- **Resolution:** Enhanced `windows/watchdog_service.ps1` with port 8001 supervision and automatic process recovery.
- **Status:** 🟢 **CLOSED**

#### [#36](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/36) — [Operations]: Non-interactive database backup automation with SHA-256 verification
- **Category:** `operations`, `database`
- **Resolution:** Enhanced `windows/backup_database.ps1` with unattended execution, SHA-256 checksums, and rotation retention.
- **Status:** 🟢 **CLOSED**

---

### Release: `windows-v1.1.0` (2026-11-13)

#### [#37](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/37) — [Security]: Disable unsafe Google OAuth token minting bypass in operator console
- **Category:** `security`, `frontend`
- **Resolution:** Deprecated `/api/v1/admin/auth/google` with HTTP 410 Gone, closing insecure client-side token minting.
- **Status:** 🟢 **CLOSED**

#### [#38](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/38) — [Security]: Eliminate fallback API key injection in Next.js admin proxies
- **Category:** `security`, `frontend`
- **Resolution:** Removed automatic fallback forwarding of `NEXT_PUBLIC_API_KEY` across administrative Next.js proxy handlers.
- **Status:** 🟢 **CLOSED**

#### [#39](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/39) — [Frontend]: Remove fabricated database health and status responses
- **Category:** `frontend`, `backend`
- **Resolution:** Removed simulated database metrics on offline conditions in favor of honest degradation reporting.
- **Status:** 🟢 **CLOSED**

---

### Release: `windows-v1.0.0` (2026-11-13)

#### [#40](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/40) — [Architecture]: Modularize backend architecture into cohesive routes and runtime layers
- **Category:** `backend`, `enhancement`
- **Resolution:** Decomposed monolithic `main.py` and `pipeline_worker.py` into decoupled routing and runtime modules.
- **Status:** 🟢 **CLOSED**

#### [#41](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/41) — [Bug]: Replace `sys.exit(1)` in forecast pipeline with explicit failure dictionaries
- **Category:** `bug`, `backend`
- **Resolution:** Replaced process termination `sys.exit(1)` calls with structured degradation dictionaries.
- **Status:** 🟢 **CLOSED**

#### [#42](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/42) — [Security]: Disable Swagger UI and OpenAPI schemas in production deployments
- **Category:** `security`, `backend`
- **Resolution:** Disabled public API explorer endpoints when `APP_ENV=production`.
- **Status:** 🟢 **CLOSED**

#### [#43](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/43) — [Bug]: Offload synchronous pipeline execution to thread pool on admin trigger
- **Category:** `bug`, `backend`
- **Resolution:** Offloaded CPU-heavy hydrological simulation execution to `run_in_executor` to keep asyncio loop responsive.
- **Status:** 🟢 **CLOSED**

#### [#44](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/44) — [Hydrology]: Antecedent stage fallback rule for ThingSpeak sensor outages
- **Category:** `hydrology`, `telemetry`
- **Resolution:** Model inherits antecedent validated water levels from prior cycle when sensor goes temporarily offline.
- **Status:** 🟢 **CLOSED**
