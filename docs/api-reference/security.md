---
title: Security & Authentication
---

# Security & Authentication

`src/api/security.py` implements HMAC-SHA256 JWT issuance/validation, bcrypt
password verification, and the dual-mode admin guard.

---

## Environment-driven defaults

```text
  ┌────────────────────────────────────────────────────────────────────┐
  │  APP_ENV (default: "production")                                   │
  │       │                                                            │
  │       ├── "pytest" imported in sys.modules?  ──yes──► force "test" │
  │       │                                                            │
  │       ├── test | dev  ──►  insecure fallbacks PERMITTED            │
  │       │        JWT_SECRET = "default_insecure_secret_for_tests"    │
  │       │        API_KEY    = "default_api_key_for_tests"            │
  │       │                                                            │
  │       └── anything else (incl. production)                          │
  │                JWT_SECRET = os.getenv("JWT_SECRET", "")  ── empty  │
  │                API_KEY    = os.getenv("API_KEY", "")     ── empty    │
  │                ⇒ no silent acceptance; every signed token fails    │
  └────────────────────────────────────────────────────────────────────┘
```

!!! danger "This is the important guarantee"
    There is **no code path** where a missing `JWT_SECRET` in production yields a
    working-but-unsigned token service. The empty default makes tokens
    *unverifiable*, so `verify_admin_auth()` rejects everything and a warning is
    logged at import time. The insecure fallbacks exist solely so `tests/` can
    import the module without a provisioned secret.

| Variable | Default | Purpose |
|:---|:---|:---|
| `JWT_SECRET` | *(empty in production)* | HMAC-SHA256 signing key |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `JWT_EXPIRATION_MINUTES` | `1440` | Token lifetime (24 h) |
| `API_KEY` | *(empty in production)* | Shared `X-API-Key` for public routes |
| `REQUIRE_API_KEY` | `true` | When `false`, public routes are open (rate-limit only) |
| `ADMIN_USERNAME` | `admin` | Admin login name |
| `ADMIN_PASSWORD` | *(empty)* | Admin login secret, compared in constant time |
| `APP_ENV` | `production` | Selects the strict / dev credential behaviour |
| `INTERNAL_KEY` | *(empty)* | Shared secret for `POST /internal/broadcast` |

---

## Authentication flow

```text
       ┌────────────────────────┐
       │  POST /admin/auth/token│
       │  {username, password}  │
       └───────────┬────────────┘
                   │
                   ▼
       ┌────────────────────────┐      ┌──────────────────────────┐
       │ verify_admin_          │─────►│ bcrypt.hashpw(...)      │
       │  credentials()         │      │ compare_digest(...)      │
       └───────────┬────────────┘      └──────────────────────────┘
                   │ valid
                   ▼
       ┌────────────────────────┐
       │ create_access_token(   │   payload = {sub, role, iat, exp}
       │   subject, role="admin"│   header   = {alg: HS256, typ: JWT}
       │ )                      │   HMAC-SHA256 over header.payload
       └───────────┬────────────┘
                   │  JWT
                   ▼
       ┌────────────────────────┐      ┌──────────────────────────┐
       │ verify_admin_auth()    │─────►│ decode + verify signature│
       │ Depends(HTTPBearer)    │      │ exp in the future?       │
       └───────────┬────────────┘      │ role == "admin"?         │
                   │ pass               └──────────────────────────┘
                   ▼
              route handler

  Failure paths
    ├─ bad password          → 401 "Invalid administrative username or password"
    ├─ missing/!Bearer token → 401 "Not authenticated"
    ├─ signature mismatch    → 401 "Invalid or expired token"
    └─ token expired         → 401 "Invalid or expired token"
```

All secret comparisons use `hmac.compare_digest` to avoid timing oracles.

---

## Reference

::: src.api.security
