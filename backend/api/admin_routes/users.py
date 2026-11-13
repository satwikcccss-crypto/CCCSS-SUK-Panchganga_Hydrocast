"""Admin user management."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backend.api.security import hash_password, verify_admin_auth

router = APIRouter()

_ALLOWED_EMAIL_DOMAINS = {"unishivaji.ac.in", "gov.in"}
_DEVELOPER_EXCEPTION_DOMAINS = {"gmail.com"}

def _validate_email_domain(email: str) -> bool:
    """Check email domain is in the allowed institutional list or developer exception."""
    if not email or "@" not in email:
        return False
    domain = email.rsplit("@", 1)[1].lower()
    if domain in _ALLOWED_EMAIL_DOMAINS or domain in _DEVELOPER_EXCEPTION_DOMAINS:
        return True
    if any(domain.endswith("." + allowed) for allowed in _ALLOWED_EMAIL_DOMAINS):
        return True
    return False

class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8)
    role: str = Field(default="govt", pattern=r"^(admin|dev|govt|pi|co_pi|jrf)$")
    display_name: Optional[str] = Field(None, max_length=128)
    email: Optional[str] = Field(None, max_length=256)

class UserSummary(BaseModel):
    id: int
    username: str
    role: str
    display_name: Optional[str] = None
    is_active: bool = True
    must_change_password: bool = False
    has_pending_reset: bool = False
    last_login: Optional[str] = None
    created_at: Optional[str] = None

@router.get(
    "/users",
    summary="List admin users",
    response_model=List[UserSummary],
)
async def list_admin_users(
    request: Request,
    auth: Dict[str, Any] = Depends(verify_admin_auth),
):
    """List all administrator accounts. Visible to operators (dev/admin roles)."""
    caller_role = auth.get("role", "")
    if caller_role not in ("dev", "admin"):
        raise HTTPException(status_code=403, detail="Operator access required")

    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        try:
            from backend.api.main import get_pool
            pool = await get_pool()
        except Exception:
            pool = None

    if pool is None:
        return []

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, username, role, display_name, is_active,
                      must_change_password, reset_token IS NOT NULL AS has_pending_reset,
                      last_login, created_at
               FROM admin_users ORDER BY created_at"""
        )
        result = []
        for r in rows:
            result.append(UserSummary(
                id=r["id"],
                username=r["username"],
                role=r["role"],
                display_name=r["display_name"],
                is_active=r["is_active"] if r["is_active"] is not None else True,
                must_change_password=r["must_change_password"] if r["must_change_password"] is not None else False,
                has_pending_reset=bool(r["has_pending_reset"]),
                last_login=r["last_login"].isoformat() if r["last_login"] else None,
                created_at=r["created_at"].isoformat() if r["created_at"] else None,
            ))
        return result

@router.post(
    "/users",
    summary="Create admin user",
    status_code=201,
)
async def create_admin_user(
    request: Request,
    req: CreateUserRequest,
    auth: Dict[str, Any] = Depends(verify_admin_auth),
):
    """Create a new administrator account. Only admin role can create users."""
    caller_role = auth.get("role", "")
    if caller_role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can create users")

    if req.email and not _validate_email_domain(req.email):
        raise HTTPException(
            status_code=400,
            detail="Email domain not allowed. Permitted: gov.in, unishivaji.ac.in (developer exceptions apply).",
        )

    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        try:
            from backend.api.main import get_pool
            pool = await get_pool()
        except Exception:
            pool = None

    if pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    pwd_hash = hash_password(req.password)
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO admin_users (username, password_hash, role, display_name, email, must_change_password)
                   VALUES ($1, $2, $3, $4, $5, TRUE)""",
                req.username.strip(), pwd_hash, req.role, req.display_name, req.email,
            )
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=409, detail="Username or email already exists")
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "created", "username": req.username.strip(), "role": req.role}

@router.post(
    "/users/{username}/generate-reset-code",
    summary="Generate password reset code",
)
async def generate_reset_code(
    request: Request,
    username: str,
    auth: Dict[str, Any] = Depends(verify_admin_auth),
):
    """Generate a 6-digit reset code valid for 1 hour. Only operators can generate codes.

    The administrator shares this code with the user out-of-band (WhatsApp, phone, in-person).
    The user then enters it on the reset-password page along with their new password.
    """
    caller_role = auth.get("role", "")
    if caller_role not in ("dev", "admin"):
        raise HTTPException(status_code=403, detail="Operator access required")

    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        try:
            from backend.api.main import get_pool
            pool = await get_pool()
        except Exception:
            pool = None

    if pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    code = f"{secrets.randbelow(1000000):06d}"
    expires = datetime.now(timezone.utc) + timedelta(hours=1)

    async with pool.acquire() as conn:
        result = await conn.execute(
            """UPDATE admin_users
               SET reset_token = $1, reset_token_expires = $2
               WHERE username = $3""",
            code, expires, username,
        )
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="User not found")

    return {
        "status": "code_generated",
        "username": username,
        "reset_code": code,
        "expires_at": expires.isoformat(),
        "instructions": "Share this code with the user. They enter it at /login/reset along with a new password. Code expires in 1 hour.",
    }

@router.post(
    "/users/{username}/toggle-active",
    summary="Activate or deactivate user",
)
async def toggle_user_active(
    request: Request,
    username: str,
    active: bool = Query(..., description="True to activate, False to deactivate"),
    auth: Dict[str, Any] = Depends(verify_admin_auth),
):
    """Activate or deactivate an admin account. Only admin role."""
    caller_role = auth.get("role", "")
    if caller_role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can manage user status")

    if username == auth.get("sub"):
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

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
        result = await conn.execute(
            "UPDATE admin_users SET is_active = $1 WHERE username = $2",
            active, username,
        )
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="User not found")

    return {"status": "updated", "username": username, "is_active": active}
