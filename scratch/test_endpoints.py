import psycopg2
import sys

pwd = "CCCSSSUKDSTSERB"
ref = "oaranobpxwstubkxrzuu"

endpoints = [
    ("Pooler 5432 (Session mode)", f"postgresql://postgres.{ref}:{pwd}@aws-0-ap-south-1.pooler.supabase.com:5432/postgres?sslmode=require"),
    ("Pooler 6543 (Transaction mode)", f"postgresql://postgres.{ref}:{pwd}@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require"),
    ("Direct 5432", f"postgresql://postgres:{pwd}@db.{ref}.supabase.co:5432/postgres?sslmode=require"),
]

for label, url in endpoints:
    print(f"Testing {label}...")
    try:
        conn = psycopg2.connect(url, connect_timeout=5)
        print(f"[SUCCESS] Connected via {label}!")
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            ver = cur.fetchone()[0]
            print(f"  PostgreSQL Version: {ver[:45]}...")
        conn.close()
        sys.exit(0)
    except Exception as e:
        print(f"  Failed: {e}")
