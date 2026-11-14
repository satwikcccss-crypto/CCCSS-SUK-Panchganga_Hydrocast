# 🛠️ windows-v1.3.0 — API Upgrades & Security Hardening (Windows Server)

**Tag:** `windows-v1.3.0`  
**Target branch:** `windows-server-production`  
**Release date:** 2026-11-14  
**Edition:** Windows Server (on-premises) — maintained separately from `main`

> 🧭 Hardening and API-upgrade release focused on bandwidth-efficient APIs, official (viewer) vs operator (admin) role-based access, database-backed audit trails, and a cleaner release posture for public and administrative surfaces.

---

## ✨ Highlights

- 🛰️ **Conditional requests (ETag / 304)** on dashboard, hydrograph, and runoff summary endpoints — clients resend `If-None-Match` and get `304 Not Modified` instead of full JSON bodies.
- 🧩 **Partial responses (`?fields=...`)** on runoff summary — request only the values widgets need (`peak_q`, `stage_m`, `alert_level`, bridge stage summaries, aliases for lead/volume keys).
- 📄 **`GET /api/v1/alerts/bulletin/pdf`** — dependency-free, on-premises `application/pdf` advisory bulletin built from the latest forecast cycle.
- 🔐 **Role-based access control (RBAC):** officials (`@unishivaji.ac.in` / `@gov.in`, role `viewer`) get the dashboard + export/download only; operator accounts (`role=admin`) retain full DB, trigger, dispatch, backup and telemetry-write access. Admin WS streams also require `role=admin`.
- 🧾 **Admin audit trail:** blocked official action attempts are persisted to `admin_audit_log` as `VIEWER_BLOCKED`; official logins retained in `admin_login_log`; operator actions logged via the existing `admin_audit_log` record path.
- 🧹 **Frontend honesty:** fabricated dashboard fallbacks removed (no synthetic run IDs, volume, stage or threshold constants), admin/operator dispatch no longer claims fake "Saved to Database" results, and the Telegram broadcast only ships live PostgreSQL telemetry (never static defaults).
- 🗄️ **Migration `002`:** composite index `bridge_stage_forecast(forecast_run_id, site_id, lead_hours)` for high-speed dashboard lookups.

---

## 🧩 API Upgrades

| Endpoint | Capability |
|:--|:--|
| `/api/v1/runoff/summary` | `ETag` + `If-None-Match` → `304`; `?fields=` partial responses |
| `/api/v1/runoff/hydrograph` | `ETag` + `If-None-Match` → `304` |
| `/api/v1/dashboard` | `ETag` + `If-None-Match` → `304` |
| `/api/v1/alerts/bulletin/pdf` | **NEW** — `application/pdf` advisory bulletin from latest cycle |

Aliases for `fields=` include: `peak_q`, `peak_discharge_m3s`, `peak_discharge`, `stage_m`, `current_stage_m`, `stages`, `alert_level`, `alert`, `lead_hours`, `lead_hours_to_peak`, `total_volume_mcm`, `volume_mcm`, `cycle_id`, `run_id`, plus direct top-level keys. Empty/unknown fields are safe; without a match the full payload is returned.

## 🔐 Security & Access Control

- **Backend auth split:** `verify_viewer_auth` accepts any valid admin-realm JWT (official read-only identity/health). `verify_admin_auth` now **requires `role == "admin"`** on all operator-action routes (DB test, trigger, recalibrate, dispatch, backup, user management).
- **Official account provisioning:** `manage_users.py` and the admin users API now only allow `unishivaji.ac.in` and `gov.in` — `gmail.com` removed everywhere; default role is `viewer`; `viewer` supported end-to-end.
- **Next.js proxies role-gated:** `/api/v1/dashboard`, `export`, `history`, `sensors/live`, `public-health` accept any valid console JWT; `db-health`, `admin/runtime`, `admin/pipeline`, `admin/health-log`, `admin/system`, `admin/dispatch` are **admin-only** (403 for officials). Server-side verification via `GET /api/v1/admin/me` (fail closed).
- **Admin dispatch honesty:** never returns fabricated `Saved to Database / verified healthy / backup dispatched` when the admin backend is unavailable or fails — returns explicit failure/503 with real status.
- **Operator `system` / `db-health` style routes:** bearer enforcement + admin-role check; services and DB are probed only by authenticated operators.
- **Admin login proxy hardened:** single trusted upstream (`ADMIN_BACKEND_ORIGIN`, default `http://127.0.0.1:8001`), payload validation, per-IP `429` rate limit, sanitized errors.
- **Frontend operator console:** role-aware `isOperator()`/`isViewer()`; Trigger/Abort/Recalibrate are hidden for officials; login defaults to `viewer` when role is missing; all admin proxies forward `Authorization` bearer from the session.
- **Admin WS (`/ws/admin/logs`, `/ws/admin/telemetry`):** `?token=` JWT/`API_KEY` with `role == "admin"` enforced **before** accept; close code `1008` otherwise; duplicate app-level stubs removed.
- **Admin Telegram webhook disabled** on the operator console (`410`); Telegram broadcasts now use live PostgreSQL telemetry and refuse to send when data is unavailable (admin role required).
- **Audit trail:** `VIEWER_BLOCKED` rows written to `admin_audit_log` for every official attempt on an operator endpoint/WS; operator actions and official logins tracked in `admin_audit_log` / `admin_login_log`.

## 🛠️ Reliability & Data Integrity

- **Baseflow integrity:** dashboard DB-sync no longer overwrites `baseflow_m3s` with the peak discharge; baseflow follows the ThingSpeak stage → previous cycle → `MONSOON_BASEFLOW` derivation instead.
- **Readiness probe JSON serialization fixed** (`start_time` datetime → ISO), closing the `/healthz/ready` 500 path.
- **Hydrograph lookups:** new Alembic `002` composite index on `bridge_stage_forecast(forecast_run_id, site_id, lead_hours)`.
- **Alembic / migrator fix:** `version_locations` corrected to `alembic/versions`, `version_path_separator`, and `postgresql://` → `postgresql+psycopg2://`.
- **Version metadata aligned to 1.3.0** across backend service/version middleware, readiness/liveliness, admin app, and both frontends.

## 🧪 Verification

| Check | Result |
|:--|:--|
| Backend tests (`py -m pytest tests/ -q --no-header`) | **319 passed, 3 skipped** (incl. `tests/test_admin_ws_auth.py`) |
| Lint (`py -m ruff check backend tests scripts`) | **Clean** |
| `frontend-public` (tsc + build, Next.js 14.2.35) | **Passed** |
| `frontend-admin` (tsc + build, Next.js 14.2.35) | **Passed** |

---

## ⚠️ Upgrade Notes

- Live backends (8000/8001) and both frontends must be rebuilt/restarted to pick up **1.3.0** (version metadata) and **RBAC enforcement** — officials will get 403 on operator endpoints.
- Create official accounts explicitly as `viewer` with the admin CLI (`python -m backend.scripts.manage_users add --username <id> --password <pw> --role viewer --email <id@unishivaji.ac.in>`). Only `role=admin` can trigger, dispatch, DB-test, backup, or manage users.
- Official operations (`.unishivaji.ac.in`, `.gov.in`) are recorded in `admin_login_log` (logins) and `admin_audit_log` (blocked attempts).
- `public-health` proxy depends on the public portal being reachable; configure `PUBLIC_PORTAL_URL` for production.

## 🗺️ Planned Follow-up

- **`windows-v1.4.0`:** comprehensive narrative documentation, release/operations runbooks, and domain cutover (HTTPS/WSS) when IT issues the HydroCast domains.

---

## 🔗 Full Changelog

- Compare: [`windows-v1.2.0...windows-v1.3.0`](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/compare/windows-v1.2.0...windows-v1.3.0)
- Changelog entry: [`CHANGELOG.md`](../../CHANGELOG.md)
