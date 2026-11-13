# Changelog

All notable changes to the **HydroCast** platform are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

### Follow-up (planned)
- `windows-v1.2.0`: deeper ops/observability patchwork (metrics/log correlation, backup/restore drills, watchdog/scheduler reliability).
- `windows-v1.3.0`: comprehensive narrative documentation and release/operations runbooks.

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
  * Supabase Google OAuth with strict project allowlist verification (`satwikcccss@gmail.com`, `panhalkarsachin@gmail.com`, `gonioelect@gmail.com`, `nikhilpawar6297@gmail.com`).
  * Bcrypt salted operational passkeys for offline and field operator access (`Dev@Adm1`, `PI@Adm1`, `COPI@Adm1`, `JRF@Adm1`).
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