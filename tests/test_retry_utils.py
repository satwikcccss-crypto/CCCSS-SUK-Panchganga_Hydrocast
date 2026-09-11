"""
tests/test_retry_utils.py
=========================
Unit tests for the exponential backoff retry utility and transient error handling.
"""

import unittest
from unittest.mock import patch, MagicMock
import requests

from src.ecmwf.retry_utils import with_retry, calculate_backoff, retry_call


class TestRetryUtils(unittest.TestCase):

    def test_calculate_backoff_progression(self):
        d1 = calculate_backoff(1, base_delay=1.0, max_delay=30.0, jitter=False)
        d2 = calculate_backoff(2, base_delay=1.0, max_delay=30.0, jitter=False)
        d3 = calculate_backoff(3, base_delay=1.0, max_delay=30.0, jitter=False)
        self.assertEqual(d1, 1.0)
        self.assertEqual(d2, 2.0)
        self.assertEqual(d3, 4.0)

    def test_calculate_backoff_max_cap(self):
        d = calculate_backoff(10, base_delay=1.0, max_delay=15.0, jitter=False)
        self.assertEqual(d, 15.0)

    def test_with_retry_succeeds_first_attempt(self):
        call_count = 0

        @with_retry(max_retries=3, base_delay=0.01, jitter=False)
        def succeeds():
            nonlocal call_count
            call_count += 1
            return "success"

        res = succeeds()
        self.assertEqual(res, "success")
        self.assertEqual(call_count, 1)

    def test_with_retry_succeeds_after_transient_failure(self):
        call_count = 0

        @with_retry(max_retries=3, base_delay=0.01, jitter=False)
        def fails_then_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise requests.exceptions.ConnectionError("Temporary DNS drop")
            return "recovered"

        res = fails_then_succeeds()
        self.assertEqual(res, "recovered")
        self.assertEqual(call_count, 2)

    def test_with_retry_exhaustion_raises(self):
        call_count = 0

        @with_retry(max_retries=2, base_delay=0.01, jitter=False)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise requests.exceptions.Timeout("Read timeout")

        with self.assertRaises(requests.exceptions.Timeout):
            always_fails()
        self.assertEqual(call_count, 2)

    def test_retry_call_helper(self):
        def sample(a, b):
            return a + b

        val = retry_call(sample, 10, 20, max_retries=2, base_delay=0.01)
        self.assertEqual(val, 30)


if __name__ == "__main__":
    unittest.main()
