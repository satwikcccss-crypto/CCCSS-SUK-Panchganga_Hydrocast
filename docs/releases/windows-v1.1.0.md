# 🚀 windows-v1.1.0 — Frontend & API Hardening (Windows Server)

**Tag:** `windows-v1.1.0`  
**Target branch:** `windows-server-production`  
**Release date:** 2026-11-13  
**Edition:** Windows Server (on-premises) — maintained separately from `main`

> 🎯 Targeted hardening release focused on reducing unsafe trust boundaries in the operator console (Next.js) and tightening admin-facing proxy behavior, while preserving backend route contracts.

---

## ✨ Highlights
- 🔐 **Safer admin auth boundary:** disabled the legacy Google→JWT minting path in the operator console (`/api/v1/admin/auth/google` now returns **410 Gone**) to prevent bypass of backend admin authentication controls.
- 🛡️ **Hardened admin proxies:** bearer-required operator console API routes now forward only explicit `Authorization` headers (no embedded/server-side API-key fallback injection).
- 🧹 **Reduced unsafe fallback behavior:** removed fabricated operator-side db-health fallback data and tightened backend status/error propagation.
- 🖥️ **Console caller alignment:** admin UI components now send authenticated requests for protected telemetry, dispatch, system, and db-health operations.

---

## 🔒 Security & Access Control
- **Disabled legacy token minting:** `frontend-admin/app/api/v1/admin/auth/google` returns `410` (unsafe minting path removed from operator console boundary).
- **Bearer-required, auth-forwarding proxies (hardened):**
  - `/api/admin/system`
  - `/api/admin/dispatch` (validated/whitelisted actions; forwarded to configured admin backend origin)
  - `/api/v1/admin/health-log`
  - `/api/v1/admin/pipeline`
  - `/api/v1/admin/runtime`
  - `/api/v1/db-health`
- **Removed fallback key injection:** no `NEXT_PUBLIC_API_KEY`/embedded server-side key forwarding in hardened admin proxies.
- **Data integrity:** eliminated fabricated db-health fallback response in the operator console proxy path.

## 🛠️ Operator Console & API Fixes
- Updated `SystemPanel`, `LiveTelemetryPanel`, and `WindowsSettingsConsole` to use authenticated proxy requests (admin session bearer token) and corrected fetch paths/auth behavior.
- Preserved backend/admin API contracts while aligning service metadata and response versioning to **`1.1.0`**.

## 📦 Release Metadata
- **API/Admin version:** `1.1.0` (`API-Version: 1.1.0`)
- **Frontend packages:** `frontend-public` and `frontend-admin` bumped to `1.1.0`
- **Scope:** Windows Server edition hardening on `windows-server-production` (`windows-v*` tagging)

---

## ✅ Verification
| Check | Result |
|:--|:--|
| Backend tests (`py -m pytest tests/ -q --no-header`) | **309 passed, 3 skipped** (11 warnings) |
| Lint (`py -m ruff check backend tests scripts`) | **Clean** |
| `frontend-public` (tsc + build, Next.js 14.2.35) | **Passed** |
| `frontend-admin` (tsc + build, Next.js 14.2.35) | **Passed** |

---

## ⚠️ Upgrade Notes
- Operator console flows that depend on hardened admin proxies now require a **valid admin bearer session/token**; unauthenticated proxy requests will be rejected.
- Verify deployment configuration for Windows Server origins:
  - `NEXT_PUBLIC_ADMIN_API_URL` / `ADMIN_BACKEND_ORIGIN` (default admin API: `:8001`)
  - `NEXT_PUBLIC_API_URL` / `BACKEND_ORIGIN` (default public API: `:8000`)
- Review reverse proxy (Caddy/IIS), CSP, and environment-specific header policies during rollout; deeper ops/header hardening continues in planned follow-up releases.

## 🗺️ Planned Follow-ups
- **`windows-v1.2.0`:** ops/observability patchwork (deeper metrics/log correlation, backup/restore drills, watchdog/scheduler reliability)
- **`windows-v1.3.0`:** comprehensive narrative documentation and release/operations runbooks

---

## 🔗 Full Changelog
- Compare: [`windows-v1.0.0...windows-v1.1.0`](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/compare/windows-v1.0.0...windows-v1.1.0)
- Changelog entry: [`CHANGELOG.md`](../../CHANGELOG.md#110---2026-11-13--frontend--api-hardening-windows-v110)
