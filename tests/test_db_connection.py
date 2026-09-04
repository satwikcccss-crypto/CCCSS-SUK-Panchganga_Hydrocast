"""
tests/test_db_connection.py
===========================
Unit tests for the enterprise database connection manager and Supabase IPv6/IPv4 resolver.
"""

import unittest
from src.db.connection import parse_supabase_ref, build_pooler_url, get_db_connection


class TestDatabaseConnection(unittest.TestCase):

    def test_parse_supabase_ref_valid(self):
        host = "db.oaranobpxwstubkxrzuu.supabase.co"
        ref = parse_supabase_ref(host)
        self.assertEqual(ref, "oaranobpxwstubkxrzuu")

    def test_parse_supabase_ref_case_insensitive(self):
        host = "DB.OARANOBPXWSTUBKXRZUU.SUPABASE.CO"
        ref = parse_supabase_ref(host)
        self.assertEqual(ref, "oaranobpxwstubkxrzuu")

    def test_parse_supabase_ref_invalid(self):
        self.assertIsNone(parse_supabase_ref("localhost"))
        self.assertIsNone(parse_supabase_ref("aws-0-ap-south-1.pooler.supabase.com"))
        self.assertIsNone(parse_supabase_ref("oaranobpxwstubkxrzuu.supabase.co"))
        self.assertIsNone(parse_supabase_ref(""))

    def test_build_pooler_url(self):
        url = build_pooler_url(
            project_ref="oaranobpxwstubkxrzuu",
            user="postgres",
            password="mysecretpassword",
            region="ap-south-1",
            port=6543,
            dbname="postgres",
        )
        expected = "postgresql://postgres.oaranobpxwstubkxrzuu:mysecretpassword@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require"
        self.assertEqual(url, expected)

    def test_build_pooler_url_user_already_has_ref(self):
        url = build_pooler_url(
            project_ref="oaranobpxwstubkxrzuu",
            user="postgres.oaranobpxwstubkxrzuu",
            password="mysecretpassword",
            region="ap-south-1",
            port=5432,
            dbname="postgres",
        )
        expected = "postgresql://postgres.oaranobpxwstubkxrzuu:mysecretpassword@aws-0-ap-south-1.pooler.supabase.com:5432/postgres?sslmode=require"
        self.assertEqual(url, expected)

    def test_get_db_connection_none_when_no_env(self):
        # When no URL is provided and env vars are unset or empty, should safely return None
        conn = get_db_connection(db_url="")
        self.assertIsNone(conn)


if __name__ == "__main__":
    unittest.main()
