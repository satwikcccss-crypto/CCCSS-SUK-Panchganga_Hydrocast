---
title: FastAPI Service Reference
---

# FastAPI Service Reference

Rendered from the docstrings in `src/api/`. Every route below is also visible in the
live [Swagger UI](../backend.md#3-interactive-api-explorer).

## Request lifecycle

```text
  Client (Next.js / curl / Telegram bot)
        │
        ▼
  ┌───────────────────────────────────────────────────────────────────┐
  │  1. CORSMiddleware            allows CORS_ORIGINS, methods GET/    │
  │                               POST/OPTIONS                        │
  ├───────────────────────────────────────────────────────────────────┤
  │  2. slowapi rate limiter      per-IP; 100/minute default          │
  │                               → 429 + Retry-After on breach       │
  ├───────────────────────────────────────────────────────────────────┤
  │  3. verify_public_or_key     X-API-Key header when REQUIRED      │
  │                               → 401 when missing/wrong            │
  ├───────────────────────────────────────────────────────────────────┤
  │  4. Route handler             asyncpg Pool (min 2 / max 10 conns)  │
  ├───────────────────────────────────────────────────────────────────┤
  │  5. Response                  dict → JSONResponse                 │
  └───────────────────────────────────────────────────────────────────┘
        │
        ▼
  Next.js dashboard  /  Supabase  /  PostgreSQL
```

---

## `src/api/main.py`

The application object, public data endpoints and the live WebSocket.

::: src.api.main

---

## `src/api/admin.py`

Administrative router mounted at `/api/v1/admin`. Every route except
`/auth/token` requires a valid admin JWT bearer token.

```text
  POST /api/v1/admin/auth/token   ──►  {username, password} ──►  JWT
  POST /api/v1/admin/trigger-run  ──►  {date, hour, cycle_id, async_mode}
  POST /api/v1/admin/archive      ──►  {retention_days, dry_run}
  POST /api/v1/admin/recalibrate  ──►  {timing_offset_hours, stage_error_m,
                                         sync_basin_file}
  GET  /api/v1/admin/me           ──►  current session claims
```

::: src.api.admin

---

## `src/api/notifier.py`

Lightweight push helper used when a cycle completes and the dashboard must
refresh without polling.

::: src.api.notifier
