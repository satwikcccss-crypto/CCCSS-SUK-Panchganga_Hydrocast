# Security Policy — HydroCast

HydroCast is a **public-safety forecasting system**: a forged forecast or an
unauthorised parameter change can cause real-world harm. This document records
the threat model, the controls now enforced, and the operational checklist that
must hold in production.

> **No system is "bulletproof."** The goal is defence in depth: fail closed,
> least privilege, constant-time secret comparison, input validation, and
> monitoring. The controls below close the known classes of attack; new ones
> must be handled through review and dependency updates.

## Reporting a vulnerability

Do **not** open a public issue. Email the maintainers with steps to reproduce and
the affected endpoint/file. You will get an acknowledgement within 72 hours.

---

## Trust boundaries

```
Browser ──► Next.js (server routes) ──► FastAPI ──► PostgreSQL
                    │                       │
                    └──► Telegram webhook   └──► local run files (data/runs)
```

* The browser is **untrusted**. It never receives a server secret.
* Next.js route handlers are trusted but still validate all user input.
* FastAPI admin routes are privileged; every one requires a JWT or API key.
* `data/runs/*.json` are read by id; ids are validated to prevent traversal.

---

## Controls implemented

### Authentication & authorisation
| Control | Detail |
|:---|:---|
| Fail-closed admin login | If `ADMIN_PASSWORD`/`ADMIN_USERNAME` are unset, **no** login succeeds. (Previously a blank submitted password matched an unset secret.) |
| Constant-time secrets | Passwords, API keys and internal keys use `hmac.compare_digest` / `crypto.timingSafeEqual`. Passwords are compared exactly (no trimming). |
| Login throttling | `POST /api/v1/admin/auth/token` is capped at `RATE_LIMIT_LOGIN` (default 5/min) per IP. |
| JWT hardening | Only HMAC algorithms (`HS256/384/512`) are accepted; unsupported values fall back to HS256. Parser errors are not echoed back. |
| Public API key | `X-API-Key` compared in constant time; an unset server key authorises nobody. |
| Internal broadcast | `INTERNAL_KEY` must be ≥16 chars; otherwise the endpoint returns 503. |

### Consumer keys (external models)

| Control | Detail |
|:---|:---|
| Dedicated key | `HYDROCAST_READONLY_KEY` lets an external model read public water levels without the master key. Format: `hydrocast_PS_V1_<random>`. The legacy name `HYDROSIM_API_KEY` is still accepted. |
| Read-only scope | Consumer keys are accepted by public routes only; `/api/v1/admin/*` accepts the master key or an admin JWT, never a consumer key. |
| URL-key convenience | Public reads accept `?key=` (Open-Meteo style) as well as `X-API-Key`. Query strings may appear in access logs, so this is limited to read-only, rate-limited data; production clients should prefer the header. |
| Constant-time, fail-closed | All configured consumer keys are compared in constant time; an unset key authorises nobody. |
| Zero-downtime rotation | `CONSUMER_API_KEYS` (comma-separated) allows the old and new key to overlap during a rotation. |

### Input validation
* All SQL uses asyncpg `$1` parameters — no string interpolation.
* `run_id` / `cycle_id` must match `^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$` and the
  resolved path must stay inside `data/runs` (backend **and** Next.js route).
* Pagination `limit` is clamped (`1..500`).
* Request bodies over `MAX_REQUEST_BYTES` (default 1 MB) are rejected.
* Telegram webhook payloads are shape-checked, length-capped, and HTML-escaped.

### Transport & browser
* CORS never combines `*` with credentials. Default is **same-origin only**;
  set `CORS_ORIGINS` to an explicit allowlist.
* Security headers on API responses: `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`, `Permissions-Policy`, `COOP`, `HSTS`, `Cache-Control: no-store`.
* Frontend sets a Content-Security-Policy, hides `X-Powered-By`, and no longer
  loads Leaflet CSS from a third-party CDN (supply-chain risk).
* Telegram webhook validation **fails closed** in production when
  `TELEGRAM_WEBHOOK_SECRET` is unset.

### Availability
* Per-IP rate limiting on public routes.
* WebSocket connections are capped (`MAX_WS_CONNECTIONS`, default 200).
* Visitor-counter route is throttled and returns cached counts instead of
  fanning out to Supabase/Upstash on every call.

---

## Required production environment

```bash
APP_ENV=production
JWT_SECRET=<48+ random bytes>
API_KEY=<random>
HYDROCAST_READONLY_KEY=<random, read-only>
CONSUMER_API_KEYS=                              # optional, for rotation
INTERNAL_KEY=<16+ random chars>
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<strong, unique>
CORS_ORIGINS=https://your-dashboard.example.org     # explicit, never '*'
DATABASE_URL=postgresql://...
VISIT_HASH_SALT=<random>
TELEGRAM_WEBHOOK_SECRET=<random>
```

Generate values with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

---

## Deployment checklist

- [ ] TLS terminated at a reverse proxy; HTTP redirects to HTTPS.
- [ ] Secrets injected from a vault/CI secrets store — never committed.
- [ ] `CORS_ORIGINS` is an explicit allowlist (no `*`).
- [ ] Admin credentials rotated; login rate limit verified.
- [ ] Reverse proxy forwards `X-Forwarded-For` **only** from trusted hops.
- [ ] Database user has least privilege (no superuser).
- [ ] Backups + restore drills for `data/runs` and Postgres.
- [x] Dependency scans (`pip-audit`, `bandit`, npm audit gate) run in CI and block new high/medium findings.
- [ ] Logs monitored for repeated 401/403/429 and path-traversal attempts.
- [ ] `/docs` exposure reviewed (disable via reverse proxy if not needed).

---

## Known limitations / next steps

* Next.js **14.2.5** should be upgraded to the latest 14.x/15.x patch line;
  track security advisories. No `middleware.ts` is used, so the well-known
  middleware-bypass class does not currently apply, but upgrade anyway.
* CSP uses `'unsafe-inline'` for scripts because Next's hydration bootstrap is
  inline. A nonce-based CSP via middleware is the next hardening step.
* The live WebSocket is read-only and unauthenticated by design; it exposes the
  same public forecast data as the REST routes. Do not broadcast privileged data.
* The visitor counter is cosmetic and best-effort; it is not a security control.
* Add dependency and container scanning to CI (see checklist).

---

*Last reviewed: 2026-10-31.*
