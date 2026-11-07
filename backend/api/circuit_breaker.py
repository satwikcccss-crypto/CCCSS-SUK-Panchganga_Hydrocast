"""
Enterprise circuit breaker pattern for external API calls.

Provides circuit breaker protection for external service calls including:
- ECMWF Open-Meteo weather API
- ThingSpeak IoT telemetry API
- Any other external HTTP service

The circuit breaker has three states:
- CLOSED: Normal operation, requests pass through
- OPEN: Circuit is tripped, requests fail fast without calling the external service
- HALF_OPEN: Testing if the service has recovered

Configuration:
- failure_threshold: Number of consecutive failures before opening circuit
- recovery_timeout: Seconds to wait before trying half-open state
- expected_exception: Exception type that counts as a failure
"""

import logging
import time
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional

log = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open and request is blocked."""


class CircuitBreaker:
    """
    Circuit breaker implementation for protecting external API calls.

    Usage:
        breaker = CircuitBreaker(
            name="ecmwf",
            failure_threshold=3,
            recovery_timeout=30.0,
            expected_exception=Exception,
        )

        @breaker
        def fetch_weather():
            return requests.get("https://api.open-meteo.com/...").json()

        # Or use as context manager:
        with breaker:
            result = requests.get("https://api.open-meteo.com/...").json()
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
        expected_exception: type = Exception,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._total_calls = 0
        self._total_failures = 0
        self._total_successes = 0

    @property
    def state(self) -> CircuitState:
        """Get current circuit state, auto-transitioning if recovery timeout elapsed."""
        if self._state == CircuitState.OPEN:
            if (
                self._last_failure_time is not None
                and time.time() - self._last_failure_time >= self.recovery_timeout
            ):
                self._state = CircuitState.HALF_OPEN
                log.info(
                    "Circuit breaker '%s' transitioning to HALF_OPEN", self.name
                )
        return self._state

    @state.setter
    def state(self, value: CircuitState) -> None:
        self._state = value

    def _record_success(self) -> None:
        """Record a successful call."""
        self._total_calls += 1
        self._total_successes += 1
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            log.info(
                "Circuit breaker '%s' CLOSED after successful call", self.name
            )

    def _record_failure(self) -> None:
        """Record a failed call."""
        self._total_calls += 1
        self._total_failures += 1
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            # Any failure in half-open state goes back to open
            self._state = CircuitState.OPEN
            log.warning(
                "Circuit breaker '%s' reopened to OPEN after failure in half-open state",
                self.name,
            )
        elif self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            log.warning(
                "Circuit breaker '%s' opened after %d consecutive failures",
                self.name,
                self.failure_count,
            )

    def __call__(self, func: Callable) -> Callable:
        """Decorator to wrap a function with circuit breaker protection."""

        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)

        return wrapper

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerError(
                f"Circuit breaker '{self.name}' is OPEN. "
                f"Service unavailable. Last failure at {self._last_failure_time}"
            )

        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except self.expected_exception as exc:
            self._record_failure()
            raise

    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerError(
                f"Circuit breaker '{self.name}' is OPEN. "
                f"Service unavailable. Last failure at {self._last_failure_time}"
            )

        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except self.expected_exception as exc:
            self._record_failure()
            raise

    @property
    def failure_count(self) -> int:
        """Get current consecutive failure count."""
        return self._failure_count

    @property
    def total_calls(self) -> int:
        """Get total number of calls."""
        return self._total_calls

    @property
    def total_failures(self) -> int:
        """Get total number of failures."""
        return self._total_failures

    @property
    def total_successes(self) -> int:
        """Get total number of successes."""
        return self._total_successes

    @property
    def success_rate(self) -> float:
        """Get success rate as percentage."""
        if self._total_calls == 0:
            return 100.0
        return (self._total_successes / self._total_calls) * 100.0

    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._total_calls = 0
        self._total_failures = 0
        self._total_successes = 0
        log.info("Circuit breaker '%s' reset", self.name)

    def get_status(self) -> dict:
        """Get circuit breaker status as dict."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "total_calls": self._total_calls,
            "total_failures": self._total_failures,
            "total_successes": self._total_successes,
            "success_rate": self.success_rate,
            "last_failure_time": self._last_failure_time,
        }


# Global circuit breaker instances for external services
circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    """Get or create a circuit breaker with the given name."""
    if name not in circuit_breakers:
        circuit_breakers[name] = CircuitBreaker(name=name, **kwargs)
    return circuit_breakers[name]


# Pre-configure circuit breakers for known external services
ecmwf_circuit_breaker = CircuitBreaker(
    name="ecmwf",
    failure_threshold=3,
    recovery_timeout=30.0,
    expected_exception=Exception,
)

thingspeak_circuit_breaker = CircuitBreaker(
    name="thingspeak",
    failure_threshold=3,
    recovery_timeout=30.0,
    expected_exception=Exception,
)

circuit_breakers["ecmwf"] = ecmwf_circuit_breaker
circuit_breakers["thingspeak"] = thingspeak_circuit_breaker


def get_circuit_breaker_status() -> dict:
    """Get status of all circuit breakers."""
    return {name: cb.get_status() for name, cb in circuit_breakers.items()}


def reset_all_circuit_breakers() -> None:
    """Reset all circuit breakers to CLOSED state."""
    for cb in circuit_breakers.values():
        cb.reset()