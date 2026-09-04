"""
src/db/connection.py
====================
Enterprise-grade PostgreSQL / Supabase connection manager.

Features:
- Centralized psycopg2 connection creation with timeout guards.
- Automatic detection of IPv6-only direct Supabase hostnames (db.<ref>.supabase.co).
- Smart auto-fallback to Supabase Connection Pooler (Supavisor IPv4)
  when operating inside IPv4-only environments (such as GitHub Actions runners).
- Clear, actionable diagnostic error messaging.
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

log = logging.getLogger(__name__)

# Common Supabase AWS pooler regions in order of likelihood
DEFAULT_POOLER_REGIONS = [
    "ap-south-1",      # AWS Mumbai (default for India / Panchganga catchment)
    "ap-southeast-1",  # Singapore
    "us-east-1",       # N. Virginia
    "eu-central-1",    # Frankfurt
    "eu-west-1",       # Ireland
    "us-west-1",       # N. California
]


def parse_supabase_ref(host: str) -> Optional[str]:
    """Extract project reference from direct Supabase host db.<ref>.supabase.co."""
    if not host:
        return None
    m = re.match(r"^db\.([a-z0-9]+)\.supabase\.co$", host.strip().lower())
    return m.group(1) if m else None


def build_pooler_url(
    project_ref: str,
    user: str,
    password: Optional[str],
    region: str = "ap-south-1",
    port: int = 6543,
    dbname: str = "postgres",
) -> str:
    """Construct an IPv4-compatible Supabase connection pooler URI."""
    pooler_user = user if user.endswith(f".{project_ref}") else f"{user}.{project_ref}"
    cred = f"{pooler_user}:{password}" if password else pooler_user
    host = f"aws-0-{region}.pooler.supabase.com"
    return f"postgresql://{cred}@{host}:{port}/{dbname}?sslmode=require"


def get_db_connection(db_url: Optional[str] = None, connect_timeout: int = 10, **kwargs):
    """
    Establish a psycopg2 connection to PostgreSQL / Supabase.
    
    If connecting to a direct Supabase host fails due to IPv6 unreachability
    (common on GitHub Actions runners), attempts automatic fallback to the
    Supabase IPv4 Connection Pooler (Supavisor).
    """
    import psycopg2

    target_url = (
        db_url
        or os.getenv("DATABASE_URL")
        or os.getenv("SUPABASE_DB_URL")
        or os.getenv("SUPABASE_DATABASE_URL")
    )

    if not target_url:
        log.warning("No DATABASE_URL or SUPABASE_DB_URL configured.")
        return None

    # Normalize url scheme if necessary
    if target_url.startswith("postgres://"):
        target_url = target_url.replace("postgres://", "postgresql://", 1)

    parsed = urlparse(target_url)
    host = parsed.hostname or ""
    project_ref = parse_supabase_ref(host)

    # 1. First attempt: connect directly with user-provided URL
    try:
        conn = psycopg2.connect(target_url, connect_timeout=connect_timeout, **kwargs)
        return conn
    except Exception as primary_err:
        err_msg = str(primary_err)
        is_network_unreachable = (
            "Network is unreachable" in err_msg
            or "errno 101" in err_msg.lower()
            or "timed out" in err_msg.lower()
            or "cannot assign requested address" in err_msg.lower()
        )

        # If not a Supabase direct host or error is authentication/other, re-raise directly
        if not project_ref or not is_network_unreachable:
            log.error("Database connection failed: %s", primary_err)
            raise primary_err

        # 2. Supabase direct host on IPv4-only environment: attempt auto-fallback to pooler
        log.warning(
            "Direct Supabase host '%s' is IPv6-only and unreachable in this environment "
            "(e.g., GitHub Actions runner). Attempting auto-recovery via Supabase IPv4 Pooler...",
            host,
        )

        user = parsed.username or "postgres"
        password = parsed.password
        dbname = (parsed.path or "/postgres").lstrip("/") or "postgres"

        # Check if user specified an explicit pooler region
        preferred_region = os.getenv("SUPABASE_REGION")
        candidate_regions = [preferred_region] if preferred_region else DEFAULT_POOLER_REGIONS

        for region in candidate_regions:
            for port in (6543, 5432):
                pooler_url = build_pooler_url(
                    project_ref=project_ref,
                    user=user,
                    password=password,
                    region=region,
                    port=port,
                    dbname=dbname,
                )
                try:
                    conn = psycopg2.connect(pooler_url, connect_timeout=5, **kwargs)
                    log.info(
                        "✓ Successfully recovered database connection via Supabase IPv4 Pooler: "
                        "aws-0-%s.pooler.supabase.com:%d",
                        region,
                        port,
                    )
                    return conn
                except Exception as pool_err:
                    log.debug("Pooler attempt aws-0-%s:%d failed: %s", region, port, pool_err)

        # 3. If fallback could not recover, display the definitive remediation instructions
        log.error(
            "\n"
            "================================================================================\n"
            "CRITICAL: SUPABASE IPv6 CONNECTIVITY ERROR IN CI/CD (GitHub Actions)\n"
            "--------------------------------------------------------------------------------\n"
            "The direct host 'db.%s.supabase.co' only resolves over IPv6.\n"
            "GitHub Actions runners are IPv4-only and cannot reach IPv6 endpoints.\n\n"
            "ACTION REQUIRED TO FIX THIS PERMANENTLY:\n"
            "1. Open Supabase Dashboard -> Project Settings -> Database -> Connection Pooling.\n"
            "2. Copy the Connection Pooler URI (Transaction mode, port 6543 or Session port 5432):\n"
            "   postgresql://postgres.%s:[YOUR_PASSWORD]@aws-0-[region].pooler.supabase.com:6543/postgres\n"
            "3. Update your GitHub Secret 'DATABASE_URL' with this pooler URI.\n"
            "================================================================================\n",
            project_ref,
            project_ref,
        )
        raise primary_err
