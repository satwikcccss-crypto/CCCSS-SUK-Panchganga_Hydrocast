"""
backend/api/admin.py
====================
Administrative API router for HydroCast.

This module is the stable public facade. Route implementations live in cohesive
submodules under :mod:`backend.api.admin_routes`:

* ``auth``          - login, token exchange, password reset, identity
* ``users``         - admin user management
* ``pipeline_ops``  - pipeline, scheduler and diagnostics operations
* ``maintenance``   - archival, recalibration, backup, alerts and audit
* ``runs``          - run ledger, calibration, stations and live log WebSocket
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.api.admin_routes import auth, maintenance, pipeline_ops, runs, users

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Admin"],
    responses={
        401: {"description": "Missing or invalid credentials."},
        403: {"description": "Valid credentials without the required role."},
    },
)

router.include_router(auth.router)
router.include_router(users.router)
router.include_router(pipeline_ops.router)
router.include_router(maintenance.router)
router.include_router(runs.router)
