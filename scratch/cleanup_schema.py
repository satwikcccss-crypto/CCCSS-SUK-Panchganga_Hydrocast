import os
import getpass
from urllib.parse import quote_plus
from psycopg2 import connect

def main():
    db_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL") or os.getenv("SUPABASE_DATABASE_URL")
    if not db_url:
        print("=" * 70)
        print(" HydroCast Panchganga - Schema Cleanup")
        print("=" * 70)
        pwd = getpass.getpass("Enter your Supabase Database Password: ")
        db_url = f"postgresql://postgres.oaranobpxwstubkxrzuu:{quote_plus(pwd.strip())}@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require"

    print("Connecting to Supabase...")
    try:
        conn = connect(db_url)
        conn.autocommit = True
        with conn.cursor() as cur:
            print("Dropping redundant tables...")
            cur.execute("DROP TABLE IF EXISTS bridge_stage_forecasts CASCADE;")
            cur.execute("DROP TABLE IF EXISTS rating_curves CASCADE;")
            print("Tables dropped successfully.")
    except Exception as e:
        print(f"Error executing cleanup: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    main()
