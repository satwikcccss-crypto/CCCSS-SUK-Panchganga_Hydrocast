"""Seed the 5 @Adm1 primary admin users."""
import asyncio
import os
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from dotenv import load_dotenv
load_dotenv()

import asyncpg
import bcrypt

DB_URL = os.getenv("DATABASE_URL", "")
INITIAL_PASSWORD = "CCCSS@HydroCast2024"

USERS = [
    ("DEV.Satwikcccss@Adm1",   "admin", "Er. Satwik K. Udupi",     "Satwikudupi@gmail.com"),
    ("PI.Panhalkarsachin@Adm1", "admin", "Dr. Sachin S. Panhalkar", "panhalkarsachin@gmail.com"),
    ("COPI.Nivhekarganesh@Adm1","admin", "Dr. Ganesh S. Nhivekar",  "gonioelect@gmail.com"),
    ("JRF.PawarNikhil@Adm1",   "admin", "Nikhil Pawar",            "nikhilpawar6297@gmail.com"),
    ("Dev.Arunbaby@Adm1",      "admin", "Arun Baby",               None),
]

OLD_ACCOUNTS = [
    "satwikcccss@gmail.com",
    "panhalkarsachin@gmail.com",
    "gonioelect@gmail.com",
    "nikhilpawar6297@gmail.com",
]


async def main():
    if not DB_URL:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    pwd_hash = bcrypt.hashpw(INITIAL_PASSWORD.encode(), bcrypt.gensalt(rounds=12)).decode()
    conn = await asyncpg.connect(DB_URL, timeout=10)

    try:
        for old in OLD_ACCOUNTS:
            await conn.execute("UPDATE admin_users SET is_active = FALSE, email = NULL WHERE username = $1", old)
        print("  Old email-based accounts deactivated (emails cleared).")

        for uname, role, dname, email in USERS:
            existing = await conn.fetchrow("SELECT id FROM admin_users WHERE username = $1", uname)
            if existing:
                await conn.execute(
                    "UPDATE admin_users SET password_hash=$1, role=$2, display_name=$3, email=$4, is_active=TRUE WHERE username=$5",
                    pwd_hash, role, dname, email, uname,
                )
                print(f"  Updated: {uname} (role={role})")
            else:
                await conn.execute(
                    "INSERT INTO admin_users (username, password_hash, role, display_name, email, is_active, must_change_password) VALUES ($1,$2,$3,$4,$5,TRUE,TRUE)",
                    uname, pwd_hash, role, dname, email,
                )
                print(f"  Created: {uname} (role={role})")

        print(f"\n  All 5 @Adm1 users seeded. Initial password: {INITIAL_PASSWORD}")
        print("  Share this password with each person. They should change it via /login/reset.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
