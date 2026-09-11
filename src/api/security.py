"""
src/api/security.py
===================
Enterprise security, JWT token handling, and administrative authentication.
Provides:
  - HMAC-SHA256 JWT generation and validation
  - Dual-mode admin authentication (JWT Bearer Token or X-API-Key)
  - Password hashing & verification (bcrypt)
"""

import hmac
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

import bcrypt
import jwt
from fastapi import HTTPException, Header, Security, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

_sec_log = logging.getLogger(__name__)

JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "1440"))  # 24 hours

API_KEY = os.getenv("API_KEY", "")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

if not JWT_SECRET:
    _sec_log.warning("JWT_SECRET is not set — JWT authentication will reject all tokens. Set JWT_SECRET env var.")
if not API_KEY:
    _sec_log.warning("API_KEY is not set — API key authentication will reject all requests. Set API_KEY env var.")
if not ADMIN_PASSWORD:
    _sec_log.warning("ADMIN_PASSWORD is not set — admin login will be disabled. Set ADMIN_PASSWORD env var.")

security_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Bcrypt password hash with auto-generated salt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def verify_admin_credentials(username: str, password: str) -> bool:
    """Verify administrator login credentials with constant-time comparison."""
    valid_user = hmac.compare_digest(username.strip(), ADMIN_USERNAME.strip())
    valid_pass = hmac.compare_digest(password.strip(), ADMIN_PASSWORD.strip())
    return valid_user and valid_pass


def create_access_token(
    subject: str,
    role: str = "admin",
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generate signed JWT access token."""
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=JWT_EXPIRATION_MINUTES)
    )
    payload = {
        "sub": subject,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "iss": "hydrocast-api",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            issuer="hydrocast-api",
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid JWT token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def verify_admin_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> Dict[str, Any]:
    """
    Unified security dependency for administrative endpoints.
    Accepts EITHER:
      1. Valid JWT in Authorization: Bearer <token>
      2. Valid master key in X-API-Key: <key>
    """
    # 1. Check Bearer token
    if credentials and credentials.credentials:
        token = credentials.credentials
        return decode_access_token(token)

    # 2. Check X-API-Key fallback
    if x_api_key and hmac.compare_digest(x_api_key.strip(), API_KEY.strip()):
        return {"sub": "system_api_key", "role": "admin"}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized. Provide a valid Bearer JWT token or X-API-Key header.",
        headers={"WWW-Authenticate": "Bearer"},
    )
