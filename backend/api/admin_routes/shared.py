"""Shared admin route helpers and constants."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", str(Path(__file__).resolve().parents[3])))


async def record_admin_audit(
    action: str,
    admin_user: str = "system",
    parameters: Optional[dict] = None,
    status: str = "SUCCESS",
    output: Optional[dict] = None,
) -> Optional[int]:
    """Insert an entry into PostgreSQL admin_audit_log table."""
    try:
        from backend.api.main import get_pool
        import json

        pool = await get_pool()
        if pool is not None:
            async with pool.acquire() as conn:
                aid = await conn.fetchval(
                    """
                    INSERT INTO admin_audit_log (action, admin_user, parameters, status, output, created_at)
                    VALUES ($1, $2, $3::jsonb, $4, $5::jsonb, NOW())
                    RETURNING id
                    """,
                    action,
                    admin_user,
                    json.dumps(parameters or {}),
                    status,
                    json.dumps(output or {}),
                )
                return aid
    except Exception as e:
        log.warning("Failed to record admin audit: %s", e)
    return None
