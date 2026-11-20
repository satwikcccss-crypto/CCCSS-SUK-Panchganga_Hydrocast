# windows-v2.0.0 — Runtime Stability & API Reliability

**Tag:** `windows-v2.0.0` · **Branch:** `windows-server-production` · **Date:** 2026-11-20

## What changed

A deliberate major platform milestone. The public API contract is unchanged —
this release marks the Windows Server edition reaching a verified, stable
production posture after a full-stack audit and fix campaign.

### Critical fixes

| Area | Problem | Fix |
|:--|:--|:--|
| Public dashboard | `Decimal` values serialized as JSON strings → `.toFixed()` crash | Decimal → JSON number in cache/ETag/fallback paths; defensive `Number()` coercion in `BasinMap.tsx` |
| Sensor telemetry | `/api/v1/sensors/live` returned 500 | Missing `asyncio` import + duplicate shadowed fetch functions removed |
| Hydrology | `/rainfall/stations` and `/rainfall/gauges` returned 500 | Async pipeline-state loader + `latitude`/`longitude` instead of nonexistent `geom` column |
| Accuracy | `/api/v1/accuracy` returned 404 | Stale `CYC_TEST_*` run removed from the runs index |
| Scheduler | Service could not be launched as a module | Added `__main__` entry point and `wait()` |
| Release gate | `ruff` F821 — undefined `urllib` in ThingSpeak sync path | `import urllib.request` added (latent failure once real keys are set) |
| Test isolation | Pipeline tests recreated `CYC_TEST_*` entries in the production runs ledger | Test paths redirected to `tmp_path`; stale test artifacts removed |
| Supervisor | Orphaned uvicorn workers held the port after parent exit, blocking restart and serving stale code | Port listeners cleared before respawning a fresh process tree |

### Added

- `rainfall_data` telemetry table + Alembic revision `003_add_rainfall_data.py`
  (deployed database advanced to revision 003).
- Regression tests for serialisation, module integrity, SQL columns, runs-index
  hygiene and documented endpoint validity.
- API documentation page now advertises only verified, live endpoints.

## Verification

- Backend suite: **357 passed, 3 skipped**.
- `ruff check backend tests scripts`: **clean**.
- Frontend production builds: **`frontend-public` and `frontend-admin` passed**.
- Database: **Alembic head = 003**.
- Live stack: **all five services healthy** (5432, 8000, 8001, 3000, 3001).
- Dashboard payload: **0 string-encoded `mm_hr`**, 3420 numeric values.

## Known deployment items (not release blockers)

- ThingSpeak channel keys are still `REPLACE_ME` placeholders; stations report
  `OFFLINE` until real keys are configured.
- NSSM services are not yet registered on this host, so the stack currently runs
  under `scripts/start_production.py` and will not auto-start on reboot.
- Host C: drive is at ~98.6% capacity.
- Production WebSocket hostname does not resolve locally; `localhost` works.

## Upgrade

```powershell
git fetch origin
powershell -ExecutionPolicy Bypass -File .\windows\deploy_release.ps1 -Ref windows-v2.0.0
```

See [README.md](../../README.md) for the full runbook.

[`windows-v1.4.2...windows-v2.0.0`](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/compare/windows-v1.4.2...windows-v2.0.0)
