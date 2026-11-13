# 🧱 windows-v1.0.0 — Windows Server Base Release

**Tag:** `windows-v1.0.0`  
**Target branch:** `windows-server-production`  
**Release date:** 2026-11-13  
**Edition:** Windows Server (on-premises) — maintained separately from `main`

> 🏁 First structured stable release of the HydroCast **Windows Server edition**, establishing a deployable, test-verified baseline for on-premises operation at Shivaji University, Kolhapur.

---

## ✨ Highlights
- 🧩 **Modularized backend architecture:** decomposed “god files” into cohesive modules while preserving route contracts and pipeline facade behavior.
- 🔒 **Security & data-integrity hardening:** removed high-risk regressions, enforced safer fail-closed behavior, and added proxy-aware protections.
- 🖥️ **Windows Server deployment alignment:** Docker/NSSM/bootstrap/runtime wiring aligned for local/on-prem operation (no cloud dependency required).
- 📈 **Operational observability baseline:** standardized health/readiness/metrics, request tracing, compression, and version headers.

---

## 🏗️ Architecture & Modularization
- `backend/api/main.py` decomposed into app shell + `backend/api/routes/`, `backend/api/admin_routes/`, `backend/api/runtime.py`, `backend/api/observability.py`.
- `backend/service/pipeline_worker.py` retained as facade with internals in `backend/service/pipeline/`; `backend/api/admin.py` preserved as aggregator.
- Preserved historical exports and route parity (public/integration + admin) to avoid breaking existing imports and clients.

## 🔐 Security, Data Integrity & Resilience
- Removed high-risk regressions (including static/admin backdoor paths and fabricated run-history enrichment).
- Pipeline completion/status and hydrology outputs remain grounded in real computed data.
- Hardened secret/runtime handling to fail closed where safety requires it (database/baseflow/backup paths).
- Added proxy-aware rate limiting and safe admin bootstrap tooling (`backend/scripts/manage_users.py`, `backend/scripts/seed_adm1.py`) without committed credentials or password hashes.
- Aligned DB initialization assets for Windows/local `psql` and Docker (`database/schema.sql`, `database/seeds.sql`, `database/auth/*`, `database/schema/*`, `database/seeds/*`).

## 🖥️ Windows Server Deployment & Operations
- `Dockerfile.backend` runs `backend.api.main:app` with liveness healthcheck (`/healthz/live`) and no baked `.env`.
- Standardized operational endpoints and middleware:
  - `GET /healthz/live` (liveness)
  - `GET /healthz/ready` (readiness; returns 503 when not ready)
  - `GET /metrics` (Prometheus)
  - validated `X-Request-ID` propagation with error-log correlation
  - GZip responses and `API-Version` header
- Aligned Windows/NSSM service names and startup/bootstrap helpers (`windows/init_database.ps1`, `scripts/start_production.py`, `.env.example`, `docker-compose.yml`).
- Default service ports: **8000** (public API), **8001** (admin API), **3000** (public portal), **3001** (operator console), **5432** (PostgreSQL 16 + PostGIS).

---

## ✅ Verification
| Check | Result |
|:--|:--|
| Backend tests (`py -m pytest tests/ -q --no-header`) | **309 passed, 3 skipped** |
| Lint (`ruff 0.17.5`, `backend tests scripts`) | **Clean** |
| `frontend-public` (tsc + build, Next.js 14.2.35) | **Passed** |
| `frontend-admin` (tsc + build, Next.js 14.2.35) | **Passed** |

---

## ⚠️ Deployment Notes
- Use safe admin bootstrap tooling/scripts; do **not** rely on committed credentials or static/hardcoded admin secrets.
- Confirm readiness/liveness probes and `API-Version` after deployment.
- Ensure PostgreSQL/PostGIS initialization and Windows service configuration match `.env.example` and deployment scripts for your environment.

## 🔗 Full Changelog
- Compare: [`ab2b6320...windows-v1.0.0`](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/compare/ab2b6320...windows-v1.0.0) *(base cut range; includes CI remediation on tag commit lineage as applicable)*
- Changelog entry: [`CHANGELOG.md`](../../CHANGELOG.md#100---2026-11-13--windows-server-base-release-windows-v100)
