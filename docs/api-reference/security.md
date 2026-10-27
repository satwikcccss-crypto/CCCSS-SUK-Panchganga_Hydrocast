---
title: Security & Authentication
---

# Security & Authentication

`src/api/security.py` implements HMAC-SHA256 JWT issuance/validation, bcrypt
password verification, and the dual-mode admin guard.

---

## Environment-driven defaults


!!! danger "This is the important guarantee"
    There is **no code path** where a missing `JWT_SECRET` in production yields a
    working-but-unsigned token service. The empty default makes tokens
    *unverifiable*, so `verify_admin_auth()` rejects everything and a warning is
    logged at import time. The insecure fallbacks exist solely so `tests/` can
    import the module without a provisioned secret.

| Variable | Default | Purpose |
| :--- | :--- | :--- |
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


All secret comparisons use `hmac.compare_digest` to avoid timing oracles.

---

## Reference

::: src.api.security

## Environment contract

`APP_ENV` decides which contract applies.

| `APP_ENV` | `JWT_SECRET` / `API_KEY` | Behaviour |
|:---|:---|:---|
| `test`, or `pytest` in `sys.modules` | may be absent | Fixed test fallbacks are permitted |
| `dev` | may be absent | Insecure development fallbacks are permitted |
| anything else, including `production` | absent | Empty secret — every signed token fails |

There is no silent acceptance path. In production an unset `JWT_SECRET` yields an
empty signing key, so verification fails closed rather than accepting a default.

Tokens are HS256. The payload is `{sub, role, iat, exp}` with `role = "admin"` for
the admin surface, and the header is `{alg: HS256, typ: JWT}`. The signature is
HMAC-SHA256 over `header.payload`. `verify_admin_auth()` decodes the token,
verifies the signature and expiry, and then compares the presented credential
against the stored bcrypt hash with `bcrypt.hashpw()`/`checkpw()`.

