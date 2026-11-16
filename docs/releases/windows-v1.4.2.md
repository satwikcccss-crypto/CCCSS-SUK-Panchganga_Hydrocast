# windows-v1.4.2 — Production Deployment Hardening

**Tag:** `windows-v1.4.2` · **Branch:** `windows-server-production` · **Date:** 2026-11-16

## What changed

This release exists because the v1.4.1 codebase could not be deployed to a clean
Windows Server. Every defect that blocked deployment was fixed, and all
dependency manifests were synchronised with the validated build environment.

### Critical fixes

| # | Problem | Fix |
|:--|:--|:--|
| #51 | `cachetools`/`orjson` undeclared → uvicorn never started | Declared + locked; module degrades gracefully |
| #52 | Cache keys ignored query params → wrong subbasin data served | Key = method + path + sorted query; ETag/304 added |
| #55 | NSSM used system Python without dependencies | Installer prefers `.venv\Scripts\python.exe` |

### Other fixes

- HAND inundation engine: missing `numpy` import, reprojection typo, inverted
  mask, incorrect per-polygon depth (#53).
- Hydrology routes: duplicate bridge block removed, `fields=` filtering restored,
  ECMWF falls back when `latest_cycle_summary` is absent (#54).
- Absolute paths removed from nine scripts; `PROJECT_ROOT` overrides commented
  out (#56).
- CORS corrected to lowercase HTTPS; dedicated admin hostname with WebSocket
  routing; `ws://` → `wss://` (#56).
- Removed deprecated `ORJSONResponse` default response class.

### Dependency updates

- `requirements.txt` floors raised to validated versions; `requirements.lock`
  regenerated; unused `psycopg2-pool`, `circuitbreaker`, `structlog` dropped.
- Dev/pre-commit tooling pinned to current releases (black 26.3.1, isort 8.0.1,
  mypy 2.4.1, gitleaks 8.30.1, pre-commit-hooks v6.0.0).
- TypeScript 5.9.3 pinned in both frontends; `pyproject.toml` targets 3.12.
- `frontend-admin/.env.local` untracked; `.env.local.example` templates added.

### Added

- `windows/deploy_release.ps1` — one-command idempotent deployment.
- Regression tests: `tests/test_api_cache.py`,
  `tests/test_hand_inundation.py`, `tests/test_hydrology_fallbacks.py`.

## Verification

- Backend suite: **346 passed, 3 skipped** (was 325 passed).
- New test proves the app boots with `cachetools` unavailable.
- `npm ls --depth=0` clean on both frontends.

## Upgrade

```powershell
git fetch origin
powershell -ExecutionPolicy Bypass -File .\windows\deploy_release.ps1 -Ref windows-v1.4.2
```

See [README.md](../../README.md) for the full runbook.

[`windows-v1.4.1...windows-v1.4.2`](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/compare/windows-v1.4.1...windows-v1.4.2)
