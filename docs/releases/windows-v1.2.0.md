# 📈 windows-v1.2.0 — Ops & Observability Patchwork (Windows Server)

**Tag:** `windows-v1.2.0`  
**Target branch:** `windows-server-production`  
**Release date:** 2026-11-13  
**Edition:** Windows Server (on-premises) — maintained separately from `main`

> ⚙️ Operational reliability and observability patchwork focused on safer metrics behavior, richer runtime visibility for Prometheus scraping, and improved Windows monitoring/backup scripts.

---

## ✨ Highlights
- 📊 **More reliable Prometheus metrics:** request instrumentation now records correctly on exception paths so ops dashboards can observe failures and latency even when handlers raise.
- 🩺 **Richer runtime gauges at scrape time:** `/metrics` performs best-effort refresh of DB pool, latest forecast-cycle, and per-site alert-level gauges (when available) without breaking scrapes.
- 🛟 **Improved Windows watchdog coverage:** monitors and attempts recovery for **Admin API port 8001** in split API deployments, alongside existing DB/public/admin console/public portal checks.
- 💾 **Backup workflow hardening:** non-interactive backup runs can use `PGPASSWORD`/`POSTGRES_PASSWORD` (when provided), with restore-drill guidance after successful dumps.

---

## 🔭 Observability & Reliability
- **Middleware fix:** `PrometheusMiddleware` records request count/duration with `status=500` on unexpected exceptions and never lets metrics recording break request handling.
- **Metrics enrichment:** added best-effort `refresh_runtime_gauges()` for scrape-time updates:
  - `hydrocast_db_connections{state="available|used|size"}`
  - `hydrocast_forecast_cycle_status{status="completed|failed|running"}`
  - `hydrocast_alert_level{site="..."}` (best-effort from latest forecast rows; known sites defaulted when absent)
- **Health/trace continuity:** preserved `X-Request-ID` propagation/correlation, `/healthz/live`, `/healthz/ready`, `/api/v1/ready`, and `API-Version` behavior; service metadata aligned to **`1.2.0`**.

## 🛠️ Windows Ops Scripts
- **`windows/watchdog_service.ps1`**
  - Added **port 8001 (Admin API)** TCP monitoring and recovery flow.
  - Attempts restarts for common admin API service names and falls back to direct `uvicorn backend.api.admin_app:app --port 8001` launch when needed.
  - Keeps existing supervision for PostgreSQL (`5432`), public API (`8000`), public portal (`3000`), and operator console (`3001`).
- **`windows/backup_database.ps1`**
  - Supports non-interactive scheduled runs by using `PGPASSWORD` or `POSTGRES_PASSWORD` (if set).
  - Retains compressed custom `pg_dump`, SHA-256 checksum audit logging, and retention cleanup.
  - Prints restore-drill hint after success: `pg_restore --list "<dump>"`.

---

## ✅ Verification
| Check | Result |
|:--|:--|
| Backend tests (`py -m pytest tests/ -q --no-header`) | **309 passed, 3 skipped** |
| Lint (`py -m ruff check backend tests scripts`) | **Clean** |
| `frontend-public` (tsc + build, Next.js 14.2.35) | **Passed** |
| `frontend-admin` (tsc + build, Next.js 14.2.35) | **Passed** |

---

## ⚠️ Upgrade Notes
- If your deployment runs the admin FastAPI app separately, ensure watchdog/service naming and port **8001** expectations match your NSSM/service configuration.
- Prometheus scrapes now perform lightweight best-effort DB reads to refresh runtime gauges; ensure the scrape interval and DB capacity are appropriate for your environment.
- Continue to protect credentials in automation (`.pgpass`, managed secrets, or controlled env vars) and perform periodic restore drills on non-production targets.

## 🗺️ Planned Follow-up
- **`windows-v1.3.0`:** comprehensive narrative documentation and release/operations runbooks.

---

## 🔗 Full Changelog
- Compare: [`windows-v1.1.0...windows-v1.2.0`](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/compare/windows-v1.1.0...windows-v1.2.0)
- Changelog entry: [`CHANGELOG.md`](../../CHANGELOG.md#120---2026-11-13--ops--observability-patchwork-windows-v120)
