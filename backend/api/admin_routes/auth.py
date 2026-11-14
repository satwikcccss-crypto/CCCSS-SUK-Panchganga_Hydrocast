"""Admin authentication, password reset and identity."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from backend.api.limits import RATE_LIMIT_LOGIN, limiter
from backend.api.security import (
    create_access_token,
    hash_password,
    verify_admin_auth,
    verify_viewer_auth,
    verify_admin_credentials_db,
)

router = APIRouter()

class TokenRequest(BaseModel):
    """Administrative login credentials."""

    username: str = Field(
        ...,
        examples=["admin"],
        description="Administrator username, from `ADMIN_USERNAME`.",
    )
    password: str = Field(
        ...,
        examples=["********"],
        description="Administrator password, from `ADMIN_PASSWORD`. Never logged or echoed back.",
    )

class TokenResponse(BaseModel):
    """A signed HS256 bearer token and its lifetime."""

    access_token: str = Field(
        ...,
        description="JWT to send as `Authorization: Bearer <token>`.",
    )
    role: str = Field(default="dev", description="Administrative role (dev or govt).")
    token_type: str = Field(default="bearer", description="Always `bearer`.")
    expires_in_seconds: int = Field(
        ...,
        examples=[86400],
        description="Token lifetime in seconds (24 hours by default).",
    )

@router.post(
    "/auth/login",
    response_model=TokenResponse,
    summary="Admin login (password)",
    response_description="A signed bearer token valid for 24 hours.",
    responses={401: {"description": "Incorrect username or password."}},
)
@router.post(
    "/auth/token",
    response_model=TokenResponse,
    summary="Exchange credentials for a JWT",
    response_description="A signed bearer token valid for 24 hours.",
    responses={401: {"description": "Incorrect username or password."}},
)
@limiter.limit(RATE_LIMIT_LOGIN)
async def login_for_access_token(request: Request, req: TokenRequest):
    """Authenticate administrator credentials and return a signed JWT bearer token.

    Uses the approved‑usernames list from the ``ADMIN_APPROVED_USERNAMES`` env var
    (comma‑separated, e.g. ``admin_user1,admin_user2``).  If the
    submitted username is not on that list the user receives a friendly message
    to contact the lead developer.

    A successful login is cheap and idempotent — call it once per session, not
    once per request; the token is valid for a full day.
    """
    # -------------------------------------------------
    # 1️⃣  Get the list of approved usernames from the environment.
    # -------------------------------------------------
    approved_usernames_env = os.getenv("ADMIN_APPROVED_USERNAMES", "").strip()
    approved_usernames = {name.strip() for name in approved_usernames_env.split(",") if name.strip()}

    # -------------------------------------------------
    # 2️⃣  Get a database pool (same pattern used elsewhere)
    # -------------------------------------------------
    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        try:
            from backend.api.main import get_pool
            pool = await get_pool()
        except Exception:
            pool = None

    # -------------------------------------------------
    # 3️⃣  Verify credentials against the Postgres table
    # -------------------------------------------------
    valid, role = await verify_admin_credentials_db(req.username, req.password, pool)

    # -------------------------------------------------
    # 4️⃣  If the username is *not* one of the approved accounts,
    #     fall back to the classic ADMIN_USERNAME / ADMIN_PASSWORD check.
    #     If neither matches, return the “contact” message.
    # -------------------------------------------------
    if approved_usernames and req.username not in approved_usernames:
        # Traditional fallback: allow the hard‑coded admin account
        if req.username == os.getenv("ADMIN_USERNAME", "admin") and valid:
            # allow login – continue to token creation below
            pass
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized. Please contact satwikcccss@gmail.com for access.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # -------------------------------------------------
    # 5️⃣  If the username is approved but the password is wrong,
    #     give a generic “invalid credentials” message (no leak).
    # -------------------------------------------------
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrative username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # -------------------------------------------------
    # 6️⃣  Successful login – create and return the JWT
    # -------------------------------------------------
    token = create_access_token(subject=req.username, role=role or "admin")
    return TokenResponse(
        access_token=token,
        role=role or "admin",
        token_type="bearer",
        expires_in_seconds=86400,               # 24 h
    )

class ResetPasswordRequest(BaseModel):
    username: str = Field(..., description="Username or email of the account.")
    reset_code: str = Field(..., min_length=6, max_length=6, description="6-digit reset code from administrator.")
    new_password: str = Field(..., min_length=8, description="New password (minimum 8 characters).")

@router.post(
    "/auth/reset-password",
    summary="Reset password with admin-issued code",
    responses={
        200: {"description": "Password updated successfully."},
        400: {"description": "Invalid or expired reset code."},
    },
)
@limiter.limit(RATE_LIMIT_LOGIN)
async def reset_password_with_code(request: Request, req: ResetPasswordRequest):
    """Reset account password using a 6-digit code generated by an administrator.

    The code is valid for 1 hour from generation. Each code can only be used once.
    """
    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        try:
            from backend.api.main import get_pool
            pool = await get_pool()
        except Exception:
            pool = None

    if pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT id, reset_token, reset_token_expires, is_active
               FROM admin_users
               WHERE username = $1 OR email = $1""",
            req.username.strip(),
        )
        if not row:
            raise HTTPException(status_code=400, detail="Invalid username or reset code")

        if not row["is_active"]:
            raise HTTPException(status_code=403, detail="Account is deactivated. Contact administrator.")

        stored_token = row["reset_token"]
        token_expires = row["reset_token_expires"]

        if not stored_token or not token_expires:
            raise HTTPException(status_code=400, detail="No reset code pending. Request one from your administrator.")

        if datetime.now(timezone.utc) > token_expires:
            await conn.execute(
                "UPDATE admin_users SET reset_token = NULL, reset_token_expires = NULL WHERE id = $1",
                row["id"],
            )
            raise HTTPException(status_code=400, detail="Reset code has expired. Request a new one.")

        if stored_token != req.reset_code.strip():
            raise HTTPException(status_code=400, detail="Invalid username or reset code")

        new_hash = hash_password(req.new_password)
        await conn.execute(
            """UPDATE admin_users
               SET password_hash = $1, reset_token = NULL, reset_token_expires = NULL,
                   must_change_password = FALSE
               WHERE id = $2""",
            new_hash, row["id"],
        )

    return {"status": "success", "message": "Password updated. You may now sign in with your new password."}

@router.get(
    "/me",
    summary="Current administrator identity",
    response_description="The authenticated subject and role from the token claims.",
)
async def get_current_admin(auth: Dict[str, Any] = Depends(verify_viewer_auth)):
    """Return identity and claims for the authenticated administrator.

    Useful as a cheap token check: a `200` here means the credential is still
    valid and carries the `admin` or `viewer` role.
    """
    return {
        "user": auth.get("sub"),
        "role": auth.get("role"),
        "authenticated_at": datetime.now(timezone.utc).isoformat(),
    }
