"""
tests/test_security_hardening.py
================================
Regression guards for the security fixes in ``src/api`` and ``src/hydrology``.

Each test encodes a previously-exploitable condition so it cannot silently
return.
"""

from datetime import timedelta
from unittest.mock import patch

import pytest
from fastapi import HTTPException

import src.api.security as sec
from src.hydrology import runs_tracker


# ── admin authentication ─────────────────────────────────────────────────────

def test_blank_admin_password_never_authenticates():
    # Previously compare_digest("", "") returned True -> blank-password login.
    with patch.object(sec, "ADMIN_PASSWORD", ""):
        assert sec.verify_admin_credentials("admin", "") is False
        assert sec.verify_admin_credentials("admin", "anything") is False


def test_admin_password_is_exact_but_username_is_trimmed():
    with patch.object(sec, "ADMIN_PASSWORD", "s3cret"), patch.object(sec, "ADMIN_USERNAME", "admin"):
        assert sec.verify_admin_credentials("admin", "s3cret") is True
        assert sec.verify_admin_credentials(" admin ", "s3cret") is True
        assert sec.verify_admin_credentials("admin", "s3cret ") is False  # no password trimming
        assert sec.verify_admin_credentials("root", "s3cret") is False


def test_tampered_jwt_is_rejected_generically():
    token = sec.create_access_token(subject="u", role="admin")
    tampered = token[:-2] + ("AA" if token[-2:] != "AA" else "BB")
    with pytest.raises(HTTPException) as exc:
        sec.decode_access_token(tampered)
    assert exc.value.status_code == 401
    # Must not leak parser internals.
    assert "signature" not in exc.value.detail.lower()


def test_expired_jwt_is_rejected():
    token = sec.create_access_token(subject="u", expires_delta=timedelta(seconds=-1))
    with pytest.raises(HTTPException) as exc:
        sec.decode_access_token(token)
    assert exc.value.status_code == 401
    assert "expired" in exc.value.detail.lower()


# ── run-id path traversal ────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "bad_id",
    [
        "../../etc/passwd",
        "..\\..\\windows\\win.ini",
        "C:\\Windows\\System32\\x",
        "a/b",
        "a.b",
        "",
        "-leading-dash",
    ],
)
def test_run_path_rejects_traversal(bad_id):
    with pytest.raises(ValueError):
        runs_tracker._run_path(runs_tracker.RUNS_DIR, bad_id)


def test_run_path_accepts_normal_cycle_ids():
    p = runs_tracker._run_path(runs_tracker.RUNS_DIR, "CYC_20260822_06z")
    assert p.name == "CYC_20260822_06z.json"
    assert p.parent == runs_tracker.RUNS_DIR.resolve()


def test_get_computation_run_rejects_traversal():
    assert runs_tracker.get_computation_run("../../etc/passwd") is None
