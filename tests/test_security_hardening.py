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

import backend.api.security as sec
from backend.hydrology import runs_tracker


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


# ── staged transaction SQL injection prevention ──────────────────────────────

def test_staged_replay_rejects_unwhitelisted_table(tmp_path, monkeypatch):
    import json
    from backend.db.resilient_pool import replay_staged_transactions

    staged_dir = tmp_path / "staging"
    staged_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("backend.db.resilient_pool.STAGING_DIR", staged_dir)

    malicious_file = staged_dir / "staged_test_users_001.json"
    malicious_file.write_text(
        json.dumps({
            "table": "admin_users; DROP TABLE simulation_runs; --",
            "operation": "INSERT",
            "records": [{"username": "attacker", "password": "hacked"}],
        }),
        encoding="utf-8",
    )

    class FakeConn:
        def cursor(self):
            raise AssertionError("Cursor should not be opened for unwhitelisted table")

    res = replay_staged_transactions(conn=FakeConn())
    assert res["failed"] == 1
    assert res["replayed"] == 0
    # The file should not be unlinked on failure
    assert malicious_file.exists()


def test_staged_replay_rejects_sql_injection_columns(tmp_path, monkeypatch):
    import json
    from backend.db.resilient_pool import replay_staged_transactions

    staged_dir = tmp_path / "staging"
    staged_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("backend.db.resilient_pool.STAGING_DIR", staged_dir)

    malicious_file = staged_dir / "staged_test_cols_001.json"
    malicious_file.write_text(
        json.dumps({
            "table": "simulation_runs",
            "operation": "INSERT",
            "records": [{"col1); DROP TABLE bridge_stage_forecast; --": "val"}],
        }),
        encoding="utf-8",
    )

    class FakeCursor:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def execute(self, query, vals):
            raise AssertionError("cur.execute should not be reached with invalid column identifier")

    class FakeConn:
        def cursor(self):
            return FakeCursor()

    res = replay_staged_transactions(conn=FakeConn())
    assert res["failed"] == 1
    assert res["replayed"] == 0
    assert malicious_file.exists()


def test_staged_replay_executes_safe_sql(tmp_path, monkeypatch):
    import json
    from backend.db.resilient_pool import replay_staged_transactions

    staged_dir = tmp_path / "staging"
    staged_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("backend.db.resilient_pool.STAGING_DIR", staged_dir)

    valid_file = staged_dir / "staged_CYC_001_simulation_runs_001.json"
    valid_file.write_text(
        json.dumps({
            "table": "simulation_runs",
            "operation": "INSERT",
            "records": [{"run_id": "CYC_TEST_01", "status": "COMPLETED"}],
        }),
        encoding="utf-8",
    )

    executed_queries = []

    class FakeCursor:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def execute(self, query, vals):
            executed_queries.append((query, vals))

    class FakeConn:
        def cursor(self):
            return FakeCursor()
        def commit(self):
            pass

    res = replay_staged_transactions(conn=FakeConn())
    assert res["failed"] == 0
    assert res["replayed"] == 1
    assert not valid_file.exists()
    assert len(executed_queries) == 1
    assert executed_queries[0][1] == ["CYC_TEST_01", "COMPLETED"]


def test_fresh_processing_file_is_not_reclaimed(tmp_path, monkeypatch):
    """A live worker's .processing claim must not be stolen by another replay."""
    import json

    import backend.db.resilient_pool as pool

    staged_dir = tmp_path / "staging"
    staged_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(pool, "STAGING_DIR", staged_dir)

    proc_file = staged_dir / "staged_CYC_FRESH_simulation_runs_001.json.processing"
    proc_file.write_text(
        json.dumps({
            "table": "simulation_runs",
            "operation": "INSERT",
            "records": [{"run_id": "CYC_FRESH", "status": "COMPLETED"}],
        }),
        encoding="utf-8",
    )

    res = pool.replay_staged_transactions(conn=object())
    assert res == {"replayed": 0, "failed": 0, "pending": 0}
    assert proc_file.exists()


def test_stale_processing_file_is_recovered_and_replayed(tmp_path, monkeypatch):
    """A crashed worker's stale claim is reclaimed after the stale threshold."""
    import json
    import os
    import time

    import backend.db.resilient_pool as pool

    staged_dir = tmp_path / "staging"
    staged_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(pool, "STAGING_DIR", staged_dir)

    proc_file = staged_dir / "staged_CYC_STALE_simulation_runs_001.json.processing"
    proc_file.write_text(
        json.dumps({
            "table": "simulation_runs",
            "operation": "INSERT",
            "records": [{"run_id": "CYC_STALE", "status": "COMPLETED"}],
        }),
        encoding="utf-8",
    )
    old = time.time() - pool.STAGING_STALE_SECONDS - 60
    os.utime(proc_file, (old, old))

    executed = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def execute(self, query, vals):
            executed.append(vals)

    class FakeConn:
        def cursor(self):
            return FakeCursor()

        def commit(self):
            pass

    res = pool.replay_staged_transactions(conn=FakeConn())
    assert res["replayed"] == 1
    assert res["failed"] == 0
    assert executed == [["CYC_STALE", "COMPLETED"]]
    assert not proc_file.exists()


# ── proxy-aware client IP ────────────────────────────────────────────────────

def _request_with_client(client_ip, headers=None):
    from starlette.requests import Request

    raw_headers = [
        (key.lower().encode("latin-1"), value.encode("latin-1"))
        for key, value in (headers or {}).items()
    ]
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": raw_headers,
        "client": (client_ip, 12345),
        "server": ("testserver", 80),
        "scheme": "http",
        "http_version": "1.1",
    }
    return Request(scope)


def test_forwarded_for_is_ignored_from_untrusted_peer(monkeypatch):
    import ipaddress

    import backend.api.limits as limits

    monkeypatch.setattr(
        limits, "_TRUSTED_PROXIES", {ipaddress.ip_network("127.0.0.1/32")}
    )
    request = _request_with_client(
        "203.0.113.7", {"X-Forwarded-For": "198.51.100.7"}
    )
    assert limits.get_real_client_ip(request) == "203.0.113.7"


def test_forwarded_for_uses_rightmost_untrusted_hop(monkeypatch):
    import ipaddress

    import backend.api.limits as limits

    monkeypatch.setattr(
        limits,
        "_TRUSTED_PROXIES",
        {
            ipaddress.ip_network("127.0.0.1/32"),
            ipaddress.ip_network("10.0.0.5/32"),
        },
    )
    # The client-supplied leftmost entry must be ignored; the rightmost
    # untrusted hop is the address the trusted proxy actually observed.
    request = _request_with_client(
        "127.0.0.1",
        {"X-Forwarded-For": "6.6.6.6, 198.51.100.7, 10.0.0.5"},
    )
    assert limits.get_real_client_ip(request) == "198.51.100.7"


def test_x_real_ip_is_honoured_only_from_trusted_peer(monkeypatch):
    import ipaddress

    import backend.api.limits as limits

    monkeypatch.setattr(
        limits, "_TRUSTED_PROXIES", {ipaddress.ip_network("127.0.0.1/32")}
    )
    trusted = _request_with_client(
        "127.0.0.1", {"X-Real-IP": "198.51.100.9"}
    )
    untrusted = _request_with_client(
        "203.0.113.7", {"X-Real-IP": "198.51.100.9"}
    )
    assert limits.get_real_client_ip(trusted) == "198.51.100.9"
    assert limits.get_real_client_ip(untrusted) == "203.0.113.7"


# ── telegram authorization fail-closed ───────────────────────────────────────

def test_telegram_is_authorized_fail_closed_when_allowlist_configured(monkeypatch):
    from backend.alerts.telegram_bot import is_authorized

    monkeypatch.setattr("backend.alerts.telegram_bot.ALLOWED_CHAT_IDS_ENV", "12345,67890")
    monkeypatch.setattr("backend.alerts.telegram_bot.ALLOWED_USERNAMES_ENV", "operator1")

    # None chat_id / None username must fail closed
    assert is_authorized(None, None) is False
    assert is_authorized(None) is False

    # Unauthorized chat and user
    assert is_authorized("99999", "unauthorized_user") is False

    # Authorized chat
    assert is_authorized("12345") is True
    assert is_authorized(12345) is True

    # Authorized username (with or without @)
    assert is_authorized(None, "operator1") is True
    assert is_authorized(None, "@operator1") is True

