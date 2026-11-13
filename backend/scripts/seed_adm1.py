"""Bootstrap an initial administrator account without committing secrets.

Usage:
    python -m backend.scripts.seed_adm1 --username admin --email admin@example.com --name "Admin Name"

The script prompts for a password (hidden) unless a secure secret is provided via
the HYDROCAST_BOOTSTRAP_PASSWORD environment variable. It never prints or stores
the password in the repository.
"""

import argparse
import asyncio
import getpass
import os
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from dotenv import load_dotenv

load_dotenv()

import asyncpg
import bcrypt

DB_URL = os.getenv("DATABASE_URL", "")


async def main() -> int:
    parser = argparse.ArgumentParser(description="Create the initial HydroCast admin user.")
    parser.add_argument(
        "--username", required=True, help="Admin username (e.g. admin or user@domain)"
    )
    parser.add_argument("--email", help="Admin email address")
    parser.add_argument("--name", help="Display name")
    parser.add_argument("--role", default="admin", help="Role (default: admin)")
    args = parser.parse_args()

    if not DB_URL:
        print("ERROR: DATABASE_URL not set")
        return 1

    password = os.getenv("HYDROCAST_BOOTSTRAP_PASSWORD") or getpass.getpass("Bootstrap password: ")
    confirm = os.getenv("HYDROCAST_BOOTSTRAP_PASSWORD_CONFIRM") or getpass.getpass(
        "Confirm password: "
    )
    if not password:
        print("ERROR: password is required")
        return 1
    if password != confirm:
        print("ERROR: passwords do not match")
        return 1

    pwd_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
    conn = await asyncpg.connect(DB_URL, timeout=10)
    try:
        existing = await conn.fetchrow(
            "SELECT id FROM admin_users WHERE username = $1", args.username.strip()
        )
        if existing:
            await conn.execute(
                """UPDATE admin_users
                   SET password_hash=$1, role=$2, display_name=$3, email=$4,
                       is_active=TRUE, must_change_password=TRUE
                   WHERE username=$5""",
                pwd_hash,
                args.role,
                args.name,
                args.email,
                args.username.strip(),
            )
            print(
                f"Updated admin user '{args.username}' (password rotated; must_change_password=TRUE)."
            )
        else:
            await conn.execute(
                """INSERT INTO admin_users
                   (username, password_hash, role, display_name, email, is_active, must_change_password)
                   VALUES ($1,$2,$3,$4,$5,TRUE,TRUE)""",
                args.username.strip(),
                pwd_hash,
                args.role,
                args.name,
                args.email,
            )
            print(f"Created admin user '{args.username}'.")
        print(
            "No password was printed. Rotate it after first login if this was a temporary bootstrap secret."
        )
        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
