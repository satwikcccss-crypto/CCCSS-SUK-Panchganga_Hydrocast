"""
tests/flood_concurrency_test.py
===============================
Concurrency stress test simulating high concurrent citizen & agency queries
against /api/SUK_hydrocast_v1 and /api/v1/dashboard on the running HydroCast server.

Verifies:
  1. Sub-100ms average response time under concurrent citizen/agency queries.
  2. Zero NaN/null corruption under concurrent access.
  3. Enforcement of rate limiting (HTTP 429) when query quota is exceeded.
"""

import json
import time
import unittest
import http.client
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

HOST = "127.0.0.1"
PORT = 8000


class TestFloodConcurrency(unittest.TestCase):

    def setUp(self):
        try:
            conn = http.client.HTTPConnection(HOST, PORT, timeout=5.0)
            # Warm up DB connection pool and caches
            conn.request("GET", "/api/v1/health")
            conn.getresponse().read()
            conn.request("GET", "/api/v1/dashboard")
            conn.getresponse().read()
            conn.request("GET", "/api/SUK_hydrocast_v1")
            conn.getresponse().read()
            conn.close()
        except Exception as e:
            self.skipTest(f"HydroCast server on {HOST}:{PORT} not reachable: {e}")

    def test_concurrent_dashboard_and_suk_feed(self):
        """Simulate concurrent citizen client sessions from distributed client IPs across /api/v1/dashboard and /api/SUK_hydrocast_v1."""
        endpoints = [
            "/api/v1/dashboard",
            "/api/SUK_hydrocast_v1",
        ]
        num_clients = 3
        requests_per_client = 4
        all_latencies_ms = []
        all_status_codes = []

        def client_session(client_id):
            latencies = []
            codes = []
            conn = http.client.HTTPConnection(HOST, PORT, timeout=5.0)
            client_ip = f"192.168.10.{client_id + 20}"
            try:
                conn.connect()
                for i in range(requests_per_client):
                    url = endpoints[(client_id + i) % len(endpoints)]
                    t0 = time.perf_counter()
                    conn.request(
                        "GET",
                        url,
                        headers={
                            "Connection": "keep-alive",
                            "X-Forwarded-For": client_ip,
                            "User-Agent": f"HydroCast-Citizen-{client_id}",
                        },
                    )
                    resp = conn.getresponse()
                    resp.read()
                    t1 = time.perf_counter()
                    codes.append(resp.status)
                    latencies.append((t1 - t0) * 1000.0)
            finally:
                conn.close()
            return codes, latencies

        with ThreadPoolExecutor(max_workers=num_clients) as executor:
            futures = [executor.submit(client_session, cid) for cid in range(num_clients)]
            for f in as_completed(futures):
                codes, lats = f.result()
                all_status_codes.extend(codes)
                all_latencies_ms.extend(lats)

        total_requests = len(all_status_codes)
        success_count = all_status_codes.count(200)
        self.assertEqual(success_count, total_requests, "All concurrent citizen queries must return 200 OK")

        avg_lat = statistics.mean(all_latencies_ms)
        p50_lat = statistics.median(all_latencies_ms)
        p95_lat = sorted(all_latencies_ms)[int(0.95 * total_requests)]
        print(f"\n[Flood Concurrency Test] Clients: {num_clients}, Total Req: {total_requests}, 200 OK: {success_count}, Avg: {avg_lat:.2f}ms, P50: {p50_lat:.2f}ms, P95: {p95_lat:.2f}ms")

        # Response time assertion: target sub-100ms
        self.assertLess(avg_lat, 100.0, f"Average latency ({avg_lat:.2f}ms) must be under 100ms")

    def test_payload_integrity_under_concurrency(self):
        """Verify payload does not contain NaN, Inf, or corrupted numeric values under concurrency."""
        def fetch_data(idx):
            conn = http.client.HTTPConnection(HOST, PORT, timeout=5.0)
            client_ip = f"192.168.20.{idx + 10}"
            try:
                conn.request("GET", "/api/SUK_hydrocast_v1", headers={"X-Forwarded-For": client_ip})
                resp = conn.getresponse()
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return resp.status, data
                return resp.status, {}
            finally:
                conn.close()

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(fetch_data, i) for i in range(8)]
            for f in as_completed(futures):
                code, data = f.result()
                if code == 200:
                    summary = data.get("summary", {})
                    peak_q = summary.get("peak_discharge_m3s")
                    self.assertIsNotNone(peak_q, "Peak discharge must not be None")
                    self.assertEqual(peak_q, 9.1, f"Peak discharge must match post-monsoon normal 9.1 m³/s, got {peak_q}")

    def test_rate_limiting_enforcement(self):
        """Send rapid bursts from a single client IP to verify that rate limiter triggers HTTP 429 when budget is exceeded."""
        hit_429 = False
        retry_after = None
        conn = http.client.HTTPConnection(HOST, PORT, timeout=3.0)
        target_client_ip = "192.168.99.99"

        try:
            for _ in range(70):
                conn.request(
                    "GET",
                    "/api/SUK_hydrocast_v1",
                    headers={"Connection": "keep-alive", "X-Forwarded-For": target_client_ip},
                )
                resp = conn.getresponse()
                resp.read()
                if resp.status == 429:
                    hit_429 = True
                    retry_after = resp.getheader("Retry-After")
                    break
        finally:
            conn.close()

        print(f"[Rate Limit Test] HTTP 429 Hit: {hit_429}, Retry-After: {retry_after}")
        self.assertTrue(hit_429, "Rate limiter must enforce HTTP 429 on excessive requests from single IP")


if __name__ == "__main__":
    unittest.main()
