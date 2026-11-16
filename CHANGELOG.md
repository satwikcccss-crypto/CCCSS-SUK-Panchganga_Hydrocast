# Changelog

All notable changes to the **HydroCast** platform are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.4.2] - 2026-11-16 — Production Deployment Hardening (`windows-v1.4.2`)

Fixes that made a fresh Windows Server deployment fail, plus dependency and
configuration synchronisation with the validated build environment.

### Fixed

- **Boot blocker:** `backend/api/cache.py` imported `cachetools` unguarded. A
  server installing only `requirements.txt` could not start the API at all.
  `cachetools` and `orjson` are now declared and the module degrades to a local
  TTL cache when they are absent.
- **Cache correctness:** response cache keys ignored the query string, so
  `?subbasin_id=X` could be served a payload cached for an unfiltered request.
  Keys now include path + sorted query, ETag/304 is implemented, and oversized
  bodies are not retained.
- **HAND engine:** missing `numpy` import (`NameError` on every call), a
  `src_cr` typo that silently returned unprojected coordinates, inverted raster
  masking, and a per-polygon depth taken from pixel `(0, 0)` instead of the
  polygon itself. All fixed; the endpoint still reports `available: false`
  without the optional geospatial stack.
- **Hydrology routes:** removed a duplicated bridge-building block that
  discarded its own result; restored field filtering on degraded paths; the
  ECMWF endpoint falls back to the base table when the optional
  `latest_cycle_summary` materialized view does not exist.
- **Deprecated API:** dropped the `ORJSONResponse` default response class
  (deprecated in current FastAPI); hot endpoints still serialise via orjson.
- **NSSM:** services now prefer `.venv\Scripts\python.exe`; previously they
  used the system interpreter, which does not carry the locked dependencies.
  Log directories are created before stdout redirection is configured.
- **Path portability:** nine scripts no longer hardcode `E:\Hydrocast Windows
  Server`, and the `PROJECT_ROOT` overrides in `.env`/`.env.example` are
  commented out (the backend resolves paths from its own location).
- **CORS/origins:** production origins corrected to lowercase HTTPS. Added a
  dedicated `hydrocast-admin.unishivaji.ac.in` Caddy site (its `/ws/*` streams
  from :8001); the old `/admin` sub-path mount redirected because its assets
  cannot load from a sub-path.
- **WebSocket security:** portal and console moved from `ws://` to `wss://`.
  An HTTPS page cannot open an insecure WebSocket, which had silently killed
  live telemetry.

### Changed

- `requirements.txt` floors raised to the validated versions;
  `requirements.lock` regenerated (no more "optional extras omitted").
  Removed unused `psycopg2-pool`, `circuitbreaker`, `structlog` entries.
- `requirements-dev.txt` and `.pre-commit-config.yaml` pinned to current tool
  releases (black 26.3.1, isort 8.0.1, mypy 2.4.1, gitleaks 8.30.1,
  pre-commit-hooks v6.0.0).
- `pyproject.toml` targets Python 3.12; frontend TypeScript pinned to 5.9.3 in
  both apps.
- `frontend-admin/.env.local` untracked; `.env.local.example` templates added so
  a fresh clone has valid, reviewable configuration.

### Added

- `windows/deploy_release.ps1` — one-command, idempotent production deployment
  (pre-flight, venv install, `npm ci && npm run build`, optional Alembic
  migration, service restart, health checks, revision recording).
- Regression tests: `tests/test_api_cache.py`,
  `tests/test_hand_inundation.py`, `tests/test_hydrology_fallbacks.py`.

### Verification

- Backend tests: **346 passed, 3 skipped** (was 325 passed).
- New tests assert the app boots with `cachetools` unavailable.

---

## [1.4.1] - 2026-11-15 — Stable Repository & Documentation Consolidation (`windows-v1.4.1`)

Stable patch release on `windows-server-production` consolidating documentation, repository hygiene, community standards, and operational tooling. No hydrology or telemetry algorithm changes.

### Documentation

- Consolidated the legacy documentation set into 27 maintained engineering manuals.
- Preserved 18 legacy documents and 2 source modules not present in `main`.
- Removed 57 superseded Markdown files and 26 unused legacy `src/` modules after verifying they remain available in `main`.
- Added a public API documentation page and validated local documentation links with 0 missing targets.

### Repository Hygiene

- Ignored generated caches, screenshots, coverage artifacts, and local raw telemetry exports.
- Stopped committing generated runtime snapshots; runtime JSON files remain local/generated.
- Kept `graphify-out/` on disk but out of Git.
- Added community health files, issue templates, accessibility guidance, and `AGENTS.md`.
- Redacted personal contact details and legacy credential examples from tracked documentation and source comments.

### Verification

- Backend tests: **325 passed, 3 skipped**.
- Ruff: **clean**.
- Frontend production builds: **`frontend-public` and `frontend-admin` passed**.
- Documentation local-link check: **0 missing targets**.
- No changes to `main`; no live credentials or personal contacts in release documentation.

### Notes

- v1.4.0 IoT sensor corrections and telemetry integrity fixes remain included.
- GitHub Release publication is handled separately; tag `windows-v1.4.1` targets `windows-server-production`.

---

## [1.4.0] - 2026-11-15 — IoT Sensor Corrections & Telemetry Integrity (`windows-v1.4.0`)

Release on `windows-server-production` focused on critical IoT sensor physics bugs, ThingSpeak multi-station data integrity, SIM signal-strength telemetry surfacing, exception safety, and runtime metadata alignment.

### Bug Fixes (Critical)

- **`NameError: 'log' is not defined` in `steps.py:110`** *(was crashing pipeline exception handler)*
  - `backend/service/pipeline/steps.py`: Added `import logging` and `log = logging.getLogger(__name__)` — missing logger caused unhandled `NameError` in the pipeline exception path.

- **All 3 ThingSpeak stations returned `NOT_CONFIGURED`** *(no live telemetry)*
  - `backend/thingspeak/multi_station.py`: Added environment auto-load; added explicit `default_channel_id` fallbacks (`3424513`, `3417870`, `3417872`). The module was reading configurations before environment initialization, so all channels appeared unconfigured.

- **CRITICAL — Sensor unit physics bug: Nitawade & Ichalkaranji stages were nonsensical**
  - Root cause: ALL 3 stations were applying feet→meters conversion (`× 0.3048`), but only Shivaji Bridge (SS) sends data in feet; Nitawade (NW) and Ichalkaranji (IK) send **meters** directly.
  - `backend/thingspeak/multi_station.py`: Added `"unit": "feet"` to SS and `"unit": "meters"` to NW/IK. Updated `_compute_stage()` to branch on unit: `dist_m = raw * 0.3048 if unit=="feet" else raw`.
  - **Before fix:** NW stage ≈ 4.16 m MSL (impossible — river bottom), IK stage similarly wrong.
  - **After fix:** SS = 531.63 m MSL ✓, NW = 548.16 m MSL ✓ (matches ThingSpeak precomputed field2), IK = 527.84 m MSL ✓

- **NW (Nitawade) `voltage` field showing 548.16 V** *(impossible value — was actually precomputed river stage)*
  - ThingSpeak Channel 3417870: `field2 = Level (m MSL precomputed)`, NOT voltage.
  - `backend/thingspeak/multi_station.py`: Changed NW `has_voltage: False`, removed voltage from field map; NW `field_map` updated to `{distance: field1, level: field2, altitude: field3}`.

- **`realtime_telemetry_validator.py` initialization when run standalone**
  - Added environment auto-load at top of file; added validation guard on API parameters to prevent querying ThingSpeak with placeholder tokens.

- **`admin_notifier.py` lead email failure when `LEAD_ADMIN_EMAIL` has multiple emails**
  - `backend/alerts/admin_notifier.py`: `get_lead_admin_email()` now splits on comma and returns the first valid address; previously would use the whole multi-email string as a single address, causing mail delivery rejection.

- **Environment variable & field1 harmonization across telemetry gauge readers**
  - Harmonized `THINGSPEAK_READ_API_KEY` with fallback to `THINGSPEAK_API_KEY` across `thingspeak_gauge.py`, `failsafe_telemetry.py`, and `realtime_telemetry_validator.py`.
  - Pinned `field1` extraction in `thingspeak_gauge.py` to prevent reading sensor battery voltage or SIM signal strength as water distance.

### Features

- **Signal Strength (SIM) for Shivaji Bridge sensor** — ThingSpeak Channel 3424513 `field3` label = "SS" = SIM signal strength (0–100%).
  - `backend/thingspeak/multi_station.py`: Added `"signal_strength": "field3"` to SS `field_map`; parsed as `int`; `has_signal_strength: True`.
  - `frontend-public/components/SensorNetworkPanel.tsx`: Added SIM Signal row with signal-bar icon.
  - `frontend-public/app/dashboard/page.tsx`: Raw Distance display now shows correct unit per station (ft for SS, m for NW/IK).
  - `frontend-admin/components/LiveTelemetryPanel.tsx`: Added `signal_strength` field row in admin live telemetry panel.
  - **Live value:** `signal_strength: 84%` confirmed from ThingSpeak.

- **Nitawade altitude/datum field mapped** — `field3=552.80` (sensor altitude) now available in NW data response; can be used as a live sanity check against hardcoded `sensor_datum_m: 552.80`.

- **Version Metadata Alignment:**
  - Backend runtime (`main.py`, `admin_app.py`, `observability.py`, `health.py`) and frontends (`frontend-public`, `frontend-admin`) bumped to **`1.4.0`**.

### Sensor Architecture (Documented)

| Station | Channel ID | field1 | field2 | field3 | Unit | Datum (m MSL) |
|---------|-----------|--------|--------|--------|------|---------------|
| Shivaji Bridge (SS) | 3424513 | Distance (ft) | Sensor Voltage (V) | SIM Signal % | **feet** | 549.35 |
| Nitawade RWLS (NW) | 3417870 | Radar distance (m) | Level precomputed (m MSL) | Sensor altitude (m) | **meters** | 552.80 |
| Ichalkaranji (IK) | 3417872 | Level distance (m) | — | — | **meters** | 543.71 |

### Verification

- Backend: **325 passed, 3 skipped** (`py -m pytest tests/ -q --no-header`), including new unit regression suite (`tests/test_thingspeak_units.py`).
- Ruff: `ruff check backend/ tests/ scripts/` clean.
- Frontend: `frontend-public` and `frontend-admin` `npm run build` pass with 0 errors.
- ThingSpeak live fetch: all 3 stations returning valid stage values.

### Known Gaps / Pending

- Domain cutover pending from Shivaji University IT: `hydrocast.unishivaji.ac.in` and `hydrocast-admin.unishivaji.ac.in`. Caddyfile reverse proxy is pre-configured and ready.

---

## [1.3.0] - 2026-11-14 — API Upgrades & Security Hardening (`windows-v1.3.0`)

Release on `windows-server-production` focused on bandwidth-efficient APIs (ETag/304, partial responses, PDF bulletin), official vs operator role-based access control with a database-backed audit trail, and a cleaner, more honest operator-console surface — while keeping all backend/frontend contracts on `1.3.0`.

### API upgrades
- **Conditional requests (ETag/304):** `If-None-Match` support added to `/api/v1/runoff/summary`, `/api/v1/runoff/hydrograph`, and `/api/v1/dashboard`; JSON responses now carry `ETag` and `Cache-Control: no-cache`, and matching validators return `304 Not Modified`.
- **Partial responses:** `GET /api/v1/runoff/summary?fields=a,b,...` returns only requested top-level keys plus a small alias set (e.g. `peak_q`, `stage_m`, `alert_level`, `lead_hours_to_peak`, `total_volume_mcm`, `cycle_id`/`run_id`); empty/unknown fields are safe and the full payload is preserved when no fields match.
- **PDF bulletin:** new `GET /api/v1/alerts/bulletin/pdf` streams a dependency-free, on-premise-friendly `application/pdf` advisory bulletin generated from the latest forecast cycle data.
- **OpenAPI / SDK readiness:** `scripts/export_openapi.py` exports the public/admin OpenAPI schema; `docs/openapi-sdk.md` documents export, client generation, and integration examples (no packaged PyPI SDK yet).

### Security hardening
- **Official (viewer) vs operator (admin) role-based access:** the operator console now enforces DB roles end-to-end. `verify_viewer_auth` (any valid admin-realm JWT) guards identity/health checks; `verify_admin_auth` now requires `role == "admin"` on all operator-action routes; admin WebSocket streams require an admin role claim. All admin proxies gate by role (dashboard/export/history/sensors = console JWT viewer-ok; db-health/system/runtime/pipeline/health-log/dispatch = admin-only 403 for officials).
- **Admin audit trail:** blocked official attempts are persisted in `admin_audit_log` as `VIEWER_BLOCKED`; operator actions continue via `record_admin_audit`; official logins retained in `admin_login_log`.
- **Official account provisioning:** institutional domains only (`unishivaji.ac.in`, `gov.in`) — `gmail.com` removed everywhere; `viewer` role supported and is the default; only `admin` retains full (DB, trigger, dispatch, backup) access.
- **Admin WebSocket auth:** `/ws/admin/logs` and `/ws/admin/telemetry` (in `backend/api/websocket_hub.py`) now require admin JWT with `role=admin` or master API key via `?token=` before the connection is accepted (close code `1008` otherwise); removed duplicate/stub admin WS handlers in `backend/api/admin_app.py` to eliminate route-precedence conflicts.
- **Admin login proxy (`frontend-admin`):** single trusted upstream (`ADMIN_BACKEND_ORIGIN`, default `http://127.0.0.1:8001`); removed multi-target/localhost fallback chain, added input validation/size limits, per-IP rate limiting (`429`), and sanitized non-leaking error responses.
- **Admin proxy/API surface:** bearer-gated `dashboard`, `export`, `history` proxies now require an admin session token; `sensors/live` route added with bearer auth and sanitized proxying; callers (`SystemPanel`, `LiveTelemetryPanel`, `ForceRunApp`, `lib/api.ts`) send the admin token.
- **Dispatch honesty:** admin dispatch route no longer fabricates “Saved to Database / verified healthy / backup dispatched” success responses when the admin backend is unavailable—returns explicit `ok: false` with `4xx/503` status.
- **Admin visits ledger simplified:** removed Supabase/Upstash multi-ledger complexity and server-side env dependency from the operator console; it now proxies the canonical backend (with minimal local fallback).
- **Admin Telegram webhook disabled** on the operator console (`410`) to remove duplicate filesystem-coupled bot handling.
- **Tests:** added `tests/test_admin_ws_auth.py` (WS rejection with close code `1008` for missing/invalid token).

### Database & migrations
- **Alembic:** `alembic.ini` `version_locations` fixed to `alembic/versions` and `version_path_separator=os`; env normalizes `postgresql://` → `postgresql+psycopg2://` for migrator compatibility.
- **New migration `002_add_forecast_run_indexes`:** composite index `idx_bsf_run_site_lead` on `bridge_stage_forecast(forecast_run_id, site_id, lead_hours)`.

### Verification
- Backend: **319 passed, 3 skipped** (`py -m pytest tests/ -q --no-header`), incl. `tests/test_admin_ws_auth.py`.
- Lint: **ruff** clean for `backend`, `tests`, `scripts`.
- Frontend: `frontend-admin` and `frontend-public` `npx tsc --noEmit` and production `next build` pass.

### Known gaps / pending (tracked, not fixed in this release)
- CSP `connect-src` still broad (`'self' ws: wss:`); WS origin allowlist pending; live-dashboard and integration verification pending after restart with the new code/version metadata.

---

## [1.2.0] - 2026-11-13 — Ops & Observability Patchwork (`windows-v1.2.0`)

Operational reliability and observability release on `windows-server-production`, focused on safer metrics handling, richer scrape-time runtime signals, and improved Windows ops scripts for monitoring and backups.

### Observability & reliability
- **Prometheus middleware hardening:** request metrics now record safely on exception paths (status labeled as `500` when handlers raise) so error rates and durations remain visible without breaking request handling.
- **Runtime metrics enrichment (`/metrics`):** added best-effort scrape-time refresh of ops gauges for DB pool state (`available`/`used`/`size`), latest forecast cycle status (`completed`/`failed`/`running`), and latest per-site alert levels when data is available; enrichment failures never break metrics scraping.
- Preserved existing request tracing and health/readiness behavior (`X-Request-ID`, `/healthz/live`, `/healthz/ready`, `/api/v1/ready`) while aligning service/version metadata to **`1.2.0`**.

### Windows operations scripts
- **Watchdog (`windows/watchdog_service.ps1`):** added monitoring/recovery handling for **Admin API port 8001** (separate FastAPI admin deployment), including service-name-aware restart attempts and direct-process fallback; continues to supervise DB/public API/public portal/operator console ports.
- **Backup (`windows/backup_database.ps1`):** improved non-interactive backup support by honoring `PGPASSWORD` / `POSTGRES_PASSWORD` (when provided) for scheduled runs and added a restore-drill hint (`pg_restore --list`) after successful backups (checksum + retention behavior retained).

### Verification
- Backend: **309 passed, 3 skipped** (`py -m pytest tests/ -q --no-header`).
- Lint: **ruff** checks clean for `backend`, `tests`, `scripts`.
- Frontend: `frontend-public` and `frontend-admin` TypeScript checks and production builds pass (Next.js 14.2.35).

### Follow-up (planned)
- `windows-v1.3.0`: comprehensive narrative documentation and release/operations runbooks.

---

## [1.1.0] - 2026-11-13 — Frontend & API Hardening (`windows-v1.1.0`)

Targeted hardening release on `windows-server-production` focused on reducing unsafe trust boundaries in the operator console (Next.js) and tightening admin-facing proxy behavior.

### Security & access control
- Disabled unsafe legacy Google-to-JWT minting path in the admin frontend (`/api/v1/admin/auth/google` now returns 410) to prevent bypass of backend admin authentication controls.
- Hardened admin proxy routes to require caller bearer authentication and forward only explicit `Authorization` headers: `/api/admin/system`, `/api/admin/dispatch`, `/api/v1/admin/health-log`, `/api/v1/admin/pipeline`, `/api/v1/admin/runtime`, and `/api/v1/db-health`.
- Removed server-side fallback/API-key injection from hardened admin proxies (no `NEXT_PUBLIC_API_KEY`/embedded key forwarding) and eliminated fabricated db-health fallback data from the operator console proxy.
- `dispatch` actions are now restricted/validated and forwarded to the configured admin backend origin; callers must supply valid admin credentials.

### Operator console fixes
- Updated operator console components (`SystemPanel`, `LiveTelemetryPanel`, `WindowsSettingsConsole`) to send authenticated requests to hardened proxy routes (bearer token from admin session) and removed direct unauthenticated telemetry fetch patterns where applicable.
- Kept backend API/admin contracts intact while aligning `API-Version`/service metadata to `1.1.0`.

### Verification
- Backend: **309 passed, 3 skipped** (`py -m pytest tests/ -q --no-header`).
- Lint: **ruff** checks clean for `backend`, `tests`, `scripts`.
- Frontend: `frontend-public` and `frontend-admin` TypeScript checks and production builds pass (Next.js 14.2.35).

---

## [1.0.0] - 2026-11-13 — Windows Server Base Release (`windows-v1.0.0`)

This is the first structured stable release of the **Windows Server edition** on branch `windows-server-production` (maintained separately from `main`). It establishes a deployable, test-verified baseline for on-premises operation at Shivaji University, Kolhapur.

### Architecture & modularization
- Decomposed the backend “god files” into cohesive modules while preserving route contracts and the pipeline facade: `backend/api/main.py` app shell with `backend/api/routes/`, `backend/api/admin_routes/`, `backend/api/runtime.py`, and `backend/api/observability.py`; `backend/service/pipeline_worker.py` facade with `backend/service/pipeline/` internals; `backend/api/admin.py` aggregator.
- Preserved historical pipeline exports and verified route parity (public/integration + admin routes) to avoid breaking existing imports and clients.

### Security, data integrity & resilience
- Removed high-risk regressions: static/admin backdoor paths and fabricated run-history enrichment; pipeline completion/status and hydrology outputs remain grounded in real computed data.
- Hardened secret and runtime handling to fail closed where safety requires it (database/baseflow/backup paths), added proxy-aware rate limiting, and provided safe admin bootstrap tooling (`backend/scripts/manage_users.py`, `backend/scripts/seed_adm1.py`) without committing credentials or password hashes.
- Database initialization assets aligned for Windows/local `psql` and Docker (`database/schema.sql`, `database/seeds.sql`, `database/auth/*`, `database/schema/*`, `database/seeds/*`) with consistent relative includes and mounts.

### Windows Server deployment & operations
- Fixed backend container/runtime wiring: `Dockerfile.backend` runs `backend.api.main:app` with liveness healthcheck (`/healthz/live`) and no baked `.env`.
- Added/standardized operational probes and observability: `/healthz/live`, `/healthz/ready` (readiness returns 503 when not ready), `/metrics` (Prometheus), validated `X-Request-ID` propagation with error-log correlation, GZip responses, and `API-Version` header.
- Aligned Windows/NSSM service naming and startup helpers (`windows/init_database.ps1`, `scripts/start_production.py`, `.env.example`, `docker-compose.yml`) for ports 8000 (public API), 8001 (admin API), 3000 (public portal), 3001 (operator console), and 5432 (PostgreSQL 16 + PostGIS).

### Verification
- Backend: **309 passed, 3 skipped** (`py -m pytest tests/ -q --no-header`).
- Lint: **ruff 0.17.5** checks clean for `backend`, `tests`, `scripts`.
- Frontend: `frontend-public` and `frontend-admin` TypeScript checks and production builds pass (Next.js 14.2.35).

---

## [2.0.0] - 2026-11-02 — Production Release: Operations Control & Digital Twin

### 🚀 Highlights & Architectural Milestones

* **Edge & Serverless Presentation Layer:** Deployed Next.js 14 App Router frontend to Vercel with serverless API route proxying, zero mixed-content issues, and automatic edge scaling.
* **Vectorized Digital Twin Simulation Engine:** Introduced pure-Python kinematic wave and Muskingum-Cunge routing providing instantaneous, zero-dependency hydrologic modeling alongside official USACE HEC-HMS 4.13 runtime execution.
* **Operator Control Room (`/admin`):** Integrated operational control dashboard with live 12-step pipeline inspection, runtime telemetry metrics, and asynchronous cloud pipeline dispatch via GitHub Actions.
* **Enterprise Dual-Auth Architecture:** 
  * Supabase Google OAuth with strict project allowlist verification (`[redacted-email]`, `[redacted-email]`, `[redacted-email]`, `[redacted-email]`).
  * Bcrypt salted operational passkeys for offline and field operator access (`[redacted-passkey]`, `[redacted-passkey]`, `[redacted-passkey]`, `[redacted-passkey]`).
* **Live Mechanical Odometer & Telemetry:** Real-time visitor counter with persistent database synchronization and fallback ledger preventing stale or zero-count anomalies.
* **12-Step Forecast Pipeline:** Automated cyclical execution with per-step retry and emergency abort capabilities.

### 🌊 Hydrologic Modeling & Stage Calibration

* **Dynamic Rating Curves:** Re-calibrated Manning's stage-discharge equations for critical Panchganga basin checkpoints (**Chhatrapati Shivaji Maharaj Bridge** and **Rajaram K.T. Weir**), validated against 2005, 2019, and 2021 historical flood records.
* **12-Stage Automated Forecast Pipeline:** Automated 90-hour cyclical rainfall ingestion (Open-Meteo 1km + ECMWF IFS), gridded sub-basin hyetograph mapping, unit hydrograph runoff convolution, and stage alert classification.

### 🛡️ Security, Reliability & Compliance

* **Fail-Closed Security Posture:** Cryptographically salted visitor IP hashing (`VISIT_HASH_SALT`), tight rate limiting on public and auth endpoints (`RATE_LIMIT_LOGIN=5/minute`), and fail-closed secret verification.
* **Multi-Channel Emergency Alerting:** Direct integrations with DDMA Kolhapur, CWC telemetry, and Telegram bot notification channels (`TELEGRAM_ALLOWED_CHAT_IDS`).
* **Comprehensive Test Suite:** 286+ unit, integration, and security tests passing.

---

## [1.0.0] - 2026-05-15 — Baseline Release

* Initial HEC-HMS 4.13 automation via Jython script runner.
* Offline DSS boundary reading and manual runoff hydrograph export.
* Basic FastAPI server with static JSON outputs.