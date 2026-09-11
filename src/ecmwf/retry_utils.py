"""
src/ecmwf/retry_utils.py
========================
Robust exponential backoff and jitter retry utilities for external meteorological
and sensor telemetry ingestion (Open-Meteo, ECMWF IFS, ThingSpeak).
"""

import functools
import logging
import random
import time
from typing import Any, Callable, Optional, Tuple, Type

import requests

log = logging.getLogger(__name__)

# Common transient network and HTTP exceptions to retry
DEFAULT_RETRY_EXCEPTIONS: Tuple[Type[BaseException], ...] = (
    requests.exceptions.Timeout,
    requests.exceptions.ConnectionError,
    requests.exceptions.ChunkedEncodingError,
    ConnectionResetError,
    TimeoutError,
    OSError,
)


def calculate_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    factor: float = 2.0,
    jitter: bool = True,
) -> float:
    """Calculate exponential backoff with optional full jitter."""
    delay = min(max_delay, base_delay * (factor ** (attempt - 1)))
    if jitter:
        delay = delay * (0.5 + random.random() * 0.5)
    return max(base_delay, delay)


def with_retry(
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    factor: float = 2.0,
    jitter: bool = True,
    retry_exceptions: Optional[Tuple[Type[BaseException], ...]] = None,
    on_retry_cb: Optional[Callable[[Exception, int, float], None]] = None,
):
    """
    Decorator for wrapping functions with exponential backoff and jitter.
    Handles transient network errors, HTTP 429 rate limits, and 5xx server errors.
    """
    if retry_exceptions is None:
        retry_exceptions = DEFAULT_RETRY_EXCEPTIONS

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_err = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_err = exc
                    # Check if exception is retryable
                    is_transient = isinstance(exc, retry_exceptions)
                    if hasattr(exc, "response") and exc.response is not None:  # type: ignore
                        status = getattr(exc.response, "status_code", None)  # type: ignore
                        if status in (429, 500, 502, 503, 504):
                            is_transient = True

                    if not is_transient or attempt == max_retries:
                        log.error(
                            "Function %s failed permanently after %d/%d attempts: %s",
                            func.__name__,
                            attempt,
                            max_retries,
                            exc,
                        )
                        raise

                    delay = calculate_backoff(attempt, base_delay, max_delay, factor, jitter)
                    log.warning(
                        "Transient error in %s (attempt %d/%d): %s. Retrying in %.2fs...",
                        func.__name__,
                        attempt,
                        max_retries,
                        exc,
                        delay,
                    )
                    if on_retry_cb:
                        try:
                            on_retry_cb(exc, attempt, delay)
                        except Exception:
                            pass
                    time.sleep(delay)

            if last_err:
                raise last_err

        return wrapper

    return decorator


def retry_call(
    func: Callable,
    *args,
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retry_exceptions: Optional[Tuple[Type[BaseException], ...]] = None,
    **kwargs,
) -> Any:
    """Helper to execute any callable with retry without applying decorator."""
    wrapped = with_retry(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        retry_exceptions=retry_exceptions,
    )(func)
    return wrapped(*args, **kwargs)
