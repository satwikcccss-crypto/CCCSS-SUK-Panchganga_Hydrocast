# 11 — Security Architecture

## Overview

HydroCast is a government early warning system. Its security model prioritizes:
1. **Data integrity** — forecast data cannot be tampered with
2. **Access control** — only authorized personnel can trigger forecasts or manage users
3. **Anti-scraping** — automated data extraction is blocked
4. **Auditability** — all admin logins are logged with timestamps and IP addresses

## Authentication

### JWT (JSON Web Tokens)

- **Algorithm**: HS256 (HMAC-SHA256) — symmetric key, no algorithm confusion attacks
- **Secret**: `JWT_SECRET` environment variable (required in production; startup aborts if missing)
- **Expiration**: 24 hours (configurable via `JWT_EXPIRATION_MINUTES`)
- **Issuer claim**: `hydrocast-api`
- **Token structure**: `{sub: username, role: "admin"|"dev"|"govt", exp, iat, iss}`

### Password Hashing

- **Algorithm**: bcrypt with cost factor 12
- **Library**: `bcrypt` (Python)
- **Constant-time comparison**: Used for all credential checks (`hmac.compare_digest`)

### Login Flow

```
Client                          Admin API (:8001)                    PostgreSQL
  │                                   │                                  │
  │  POST /auth/token                 │                                  │
  │  {username, password}             │                                  │
  │──────────────────────────────────>│                                  │
  │                                   │  SELECT password_hash, role      │
  │                                   │  FROM admin_users                │
  │                                   │  WHERE username = ?              │
  │                                   │─────────────────────────────────>│
  │                                   │                                  │
  │                                   │  bcrypt.checkpw(password, hash)  │
  │                                   │                                  │
  │                                   │  INSERT INTO admin_login_log     │
  │                                   │─────────────────────────────────>│
  │                                   │                                  │
  │  {access_token, role, expires}    │                                  │
  │<──────────────────────────────────│                                  │
```

### Password Reset (Zero-Cost, No Email)

Since the system operates without a mail service, password resets use admin-generated codes:

1. **Admin generates code**: `POST /admin/users/{username}/generate-reset-code` (returns 6-digit numeric code, valid 1 hour)
2. **Admin shares code**: Out-of-band (WhatsApp, phone, in-person)
3. **User resets password**: `POST /auth/reset-password` with username + code + new password
4. **Code expires**: Automatically after 1 hour; single-use

## Role-Based Access Control (RBAC)

| Role | Can View Dashboard | Can Trigger Forecast | Can Manage Users | Can Access DB/Logs |
|------|-------------------|---------------------|-----------------|-------------------|
| `govt` | Yes | No | No | No |
| `dev` | Yes | Yes | No | Yes |
| `admin` | Yes | Yes | Yes | Yes |

### Role Assignment

- **`admin`** — Primary administrators (@Adm1 accounts): PI, Co-PI, developers
- **`dev`** — Operators: researchers with technical access to trigger cycles and view system internals
- **`govt`** — Viewers: government officials from `gov.in` and `unishivaji.ac.in` domains (read-only)
- **`pi`**, **`co_pi`**, **`jrf`** — Legacy role names mapped to appropriate access levels

### Frontend Enforcement

The admin console (`frontend-admin`) enforces RBAC client-side:
- **Sidebar categories** marked `operatorOnly: true` (ML, System, Storage) are hidden from `govt` role
- **Action buttons** (Force Forecast, DB Test, DB Backup, Message Dispatch) show only for `dev`/`admin`
- **Read-only badge** shown for viewer accounts: "Read-only access · {role}"
- **Sign Out** button clears session and redirects to `/login`

### Backend Enforcement

- `verify_admin_auth` dependency checks JWT on every admin route
- User management endpoints require `admin` role specifically
- Reset code generation requires `dev` or `admin` role
- `is_active` flag checked during login — deactivated accounts cannot authenticate

## CORS (Cross-Origin Resource Sharing)

### Public API (Port 8000)

```
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001
```

- Explicit origin allowlist only
- **Wildcard (`*`) is blocked**: If `*` appears in `CORS_ORIGINS`, the application calls `sys.exit(1)` and refuses to start
- Credentials allowed
- Methods: GET, POST, OPTIONS
- Headers: Authorization, Content-Type, X-API-Key

### Admin API (Port 8001)

Same policy with separate `ADMIN_CORS_ORIGINS` variable. Wildcard also causes immediate shutdown.

## Content Security Policy (CSP)

Both Next.js frontends set CSP headers via `next.config.ts`:
- `default-src 'self'`
- `script-src 'self' 'unsafe-eval' 'unsafe-inline'` (required for Next.js)
- `connect-src 'self' localhost:* ws://localhost:* api.thingspeak.com api.open-meteo.com`
- `img-src 'self' data: blob:`
- `frame-ancestors 'none'` (prevents clickjacking)

## Anti-Scraping Middleware

Both APIs include middleware that blocks requests from known scraping user agents:

**Blocked User-Agent fragments:**
```
scrapy, httpclient, python-requests, go-http-client, wget, curl,
libwww, java/, okhttp, httpx, node-fetch, undici, axios, got, superagent
```

**Allowed bots (public API only):**
```
googlebot, bingbot, uptimerobot
```

**Exemptions:**
- Public API: `/api/v1/health` (monitoring probes)
- Admin API: `/auth/` paths (login needs curl-friendly access for CI)

**Response for blocked requests:**
```json
{"detail": "Automated scraping is prohibited. This is a government early warning system."}
```

## Security Headers

Both APIs attach hardening headers to every response:

| Header | Value | Purpose |
|--------|-------|---------|
| X-Content-Type-Options | nosniff | Prevent MIME sniffing |
| X-Frame-Options | DENY | Prevent clickjacking |
| Referrer-Policy | no-referrer | Prevent referer leakage |
| Permissions-Policy | geolocation=(), microphone=(), camera=() | Disable browser APIs |
| Cross-Origin-Opener-Policy | same-origin | Isolate cross-origin windows |
| Strict-Transport-Security | max-age=31536000 | Force HTTPS |
| Cache-Control | no-store, no-cache, must-revalidate, private | Prevent caching of admin data |

## Rate Limiting

- **Public API**: 60 requests/minute per IP (configurable via `RATE_LIMIT_PUBLIC`)
- **Login endpoint**: 5 requests/minute per IP (configurable via `RATE_LIMIT_LOGIN`)
- **Library**: slowapi (built on limits)
- **Response**: HTTP 429 with `Retry-After` header

## robots.txt

### Public Frontend
```
User-agent: *
Disallow: /api/
Disallow: /_next/
Allow: /dashboard
```
Allows Googlebot to index the public dashboard but blocks API and internal routes.

### Admin Frontend
```
User-agent: *
Disallow: /
```
Blocks all crawlers entirely.

## Frontend Anti-Copy Protection

The public dashboard applies:
- `select-none` CSS class (prevents text selection)
- `onContextMenu` prevention (blocks right-click)
- These are deterrents, not cryptographic protection

## Audit Trail

The `admin_login_log` table records every login attempt:

| Column | Type | Description |
|--------|------|-------------|
| username | VARCHAR(64) | Account attempted |
| role | VARCHAR(32) | Role of the account |
| ip_address | VARCHAR(64) | Client IP |
| success | BOOLEAN | Whether authentication succeeded |
| attempted_at | TIMESTAMPTZ | Timestamp of attempt |

## Environment Variables (Security-Related)

| Variable | Required | Description |
|----------|----------|-------------|
| `JWT_SECRET` | Yes (production) | HS256 signing key. Startup aborts if missing. |
| `ADMIN_JWT_SECRET` | No | Separate key for admin tokens (falls back to JWT_SECRET) |
| `API_KEY` | No | Master API key for service-to-service auth |
| `ADMIN_PASSWORD` | Yes | Emergency fallback admin password |
| `ADMIN_USERNAME` | Yes | Emergency fallback admin username |

## Legal Notice

Unauthorized access is prohibited under the **Information Technology Act, 2000 (Section 66)** of the Government of India. All access is logged and monitored.
