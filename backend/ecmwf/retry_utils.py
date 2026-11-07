"""
backend/ecmwf/retry_utils.py
=============================
Compatibility shim: re-exports from backend.rainfall.retry_utils.
"""

from backend.rainfall.retry_utils import (  # noqa: F401
    with_retry,
    calculate_backoff,
    retry_call,
)

__all__ = ["with_retry", "calculate_backoff", "retry_call"]
