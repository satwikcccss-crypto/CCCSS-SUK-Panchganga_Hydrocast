"""
HydroCast Admin User Management CLI
====================================
Usage:
    python -m backend.scripts.manage_users add    --username USER --password PASS [--role ROLE] [--email EMAIL] [--name "Display Name"]
    python -m backend.scripts.manage_users list
    python -m backend.scripts.manage_users reset   --username USER          # prints 6-digit code
    python -m backend.scripts.manage_users setpwd  --username USER --password NEWPASS
    python -m backend.scripts.manage_users toggle  --username USER --active true|false

Roles: admin, dev, pi, co_pi, jrf, govt
"""

import argparse
import os
import secrets
import sys
from datetime import datetime, timezone, timedelta

import asyncio
import asyncpg
from dotenv import load_dotenv

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
load_dotenv()

from backend.api.security import hash_password  # noqa: E402

DB_URL = os.getenv("DATABASE_URL", "")
VALID_ROLES = {"admin", "dev", "pi", "co_pi", "jrf", "govt"}
ALLOWED_EMAIL_DOMAINS = {"unishivaji.ac.in", "gov.in", "gmail.com"}


async def get_conn() -> asyncpg.Connection:
    if not DB_URL:
        print("ERROR: DATABASE_URL not set in .env")
        sys.exit(1)
    return await asyncpg.connect(DB_URL, timeout=10)


async def cmd_add(args):
    if args.role not in VALID_ROLES:
        print(f"ERROR: Invalid role '{args.role}'. Must be one of: {', '.join(sorted(VALID_ROLES))}")
        sys.exit(1)
    if args.email:
        domain = args.email.rsplit("@", 1)[-1].lower()
        valid = domain in ALLOWED_EMAIL_DOMAINS or any(domain.endswith("." + d) for d in ALLOWED_EMAIL_DOMAINS)
        if not valid:
            print(f"ERROR: Email domain '{domain}' not in allowed list: {ALLOWED_EMAIL_DOMAINS}")
            sys.exit(1)

    conn = await get_conn()
    try:
        pwd_hash = hash_password(args.password)
        await conn.execute(
            """INSERT INTO admin_users (username, password_hash, role, display_name, email, must_change_password)
               VALUES ($1, $2, $3, $4, $5, TRUE)""",
            args.username.strip(), pwd_hash, args.role,
            args.name, args.email,
        )
        print(f"  Created user: {args.username} (role={args.role})")
    except asyncpg.UniqueViolationError:
        print(f"  User '{args.username}' already exists — updating password and role.")
        pwd_hash = hash_password(args.password)
        await conn.execute(
            """UPDATE admin_users SET password_hash = $1, role = $2, display_name = COALESCE($3, display_name),
                                      email = COALESCE($4, email)
               WHERE username = $5""",
            pwd_hash, args.role, args.name, args.email, args.username.strip(),
        )
        print(f"  Updated user: {args.username}")
    finally:
        await conn.close()


async def cmd_list(_args):
    conn = await get_conn()
    try:
        rows = await conn.fetch(
            """SELECT username, role, display_name, email, is_active, must_change_password,
                      last_login, created_at, reset_token IS NOT NULL AS has_reset
               FROM admin_users ORDER BY created_at"""
        )
        if not rows:
            print("  No admin users found.")
            return
        print(f"  {'Username':<30} {'Role':<8} {'Active':<7} {'Name':<20} {'Last Login'}")
        print("  " + "-" * 95)
        for r in rows:
            active = "yes" if r["is_active"] is not False else "NO"
            name = (r["display_name"] or "")[:20]
            ll = r["last_login"].strftime("%Y-%m-%d %H:%M") if r["last_login"] else "never"
            reset = " [RESET PENDING]" if r["has_reset"] else ""
            print(f"  {r['username']:<30} {r['role']:<8} {active:<7} {name:<20} {ll}{reset}")
        print(f"\n  Total: {len(rows)} users")
    finally:
        await conn.close()


async def cmd_reset(args):
    conn = await get_conn()
    try:
        row = await conn.fetchrow("SELECT id, username FROM admin_users WHERE username = $1", args.username.strip())
        if not row:
            print(f"  ERROR: User '{args.username}' not found.")
            sys.exit(1)
        code = f"{secrets.randbelow(1000000):06d}"
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        await conn.execute(
            "UPDATE admin_users SET reset_token = $1, reset_token_expires = $2 WHERE id = $3",
            code, expires, row["id"],
        )
        print(f"\n  Reset code for '{args.username}': {code}")
        print(f"  Expires: {expires.strftime('%Y-%m-%d %H:%M UTC')} (1 hour)")
        print(f"  Share this code with the user. They enter it at /login/reset\n")
    finally:
        await conn.close()


async def cmd_setpwd(args):
    conn = await get_conn()
    try:
        pwd_hash = hash_password(args.password)
        result = await conn.execute(
            """UPDATE admin_users SET password_hash = $1, reset_token = NULL, reset_token_expires = NULL,
                                      must_change_password = FALSE
               WHERE username = $2""",
            pwd_hash, args.username.strip(),
        )
        if result == "UPDATE 0":
            print(f"  ERROR: User '{args.username}' not found.")
            sys.exit(1)
        print(f"  Password updated for '{args.username}'.")
    finally:
        await conn.close()


async def cmd_toggle(args):
    active = args.active.lower() in ("true", "1", "yes")
    conn = await get_conn()
    try:
        result = await conn.execute(
            "UPDATE admin_users SET is_active = $1 WHERE username = $2",
            active, args.username.strip(),
        )
        if result == "UPDATE 0":
            print(f"  ERROR: User '{args.username}' not found.")
            sys.exit(1)
        print(f"  User '{args.username}' is now {'ACTIVE' if active else 'DEACTIVATED'}.")
    finally:
        await conn.close()


def main():
    parser = argparse.ArgumentParser(description="HydroCast Admin User Management")
    sub = parser.add_subparsers(dest="command")

    p_add = sub.add_parser("add", help="Add or update a user")
    p_add.add_argument("--username", required=True)
    p_add.add_argument("--password", required=True)
    p_add.add_argument("--role", default="govt", choices=sorted(VALID_ROLES))
    p_add.add_argument("--email", default=None)
    p_add.add_argument("--name", default=None, help="Display name")

    sub.add_parser("list", help="List all users")

    p_reset = sub.add_parser("reset", help="Generate 6-digit reset code")
    p_reset.add_argument("--username", required=True)

    p_setpwd = sub.add_parser("setpwd", help="Set password directly")
    p_setpwd.add_argument("--username", required=True)
    p_setpwd.add_argument("--password", required=True)

    p_toggle = sub.add_parser("toggle", help="Activate or deactivate user")
    p_toggle.add_argument("--username", required=True)
    p_toggle.add_argument("--active", required=True, help="true or false")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    cmd_map = {"add": cmd_add, "list": cmd_list, "reset": cmd_reset, "setpwd": cmd_setpwd, "toggle": cmd_toggle}
    asyncio.run(cmd_map[args.command](args))


if __name__ == "__main__":
    main()
