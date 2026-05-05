"""Per-service request rate limiting for porthole."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from threading import Lock
from typing import Deque, Dict, Optional

from porthole.logger import get_logger

log = get_logger("porthole.ratelimit")


@dataclass
class RateLimitConfig:
    """Configuration for a token-bucket style rate limiter."""
    requests_per_second: float
    burst: int = 1

    def __post_init__(self) -> None:
        if self.requests_per_second <= 0:
            raise ValueError("requests_per_second must be positive")
        if self.burst < 1:
            raise ValueError("burst must be at least 1")


class ServiceRateLimiter:
    """Sliding-window rate limiter for a single service."""

    def __init__(self, config: RateLimitConfig) -> None:
        self._config = config
        self._window: Deque[float] = deque()
        self._lock = Lock()

    @property
    def window_seconds(self) -> float:
        return self._config.burst / self._config.requests_per_second

    def is_allowed(self, now: Optional[float] = None) -> bool:
        """Return True if the request is within the rate limit."""
        ts = now if now is not None else time.monotonic()
        cutoff = ts - self.window_seconds
        with self._lock:
            while self._window and self._window[0] < cutoff:
                self._window.popleft()
            if len(self._window) < self._config.burst:
                self._window.append(ts)
                return True
            return False


class RateLimitRegistry:
    """Registry mapping service names to their rate limiters."""

    def __init__(self) -> None:
        self._limiters: Dict[str, ServiceRateLimiter] = {}
        self._lock = Lock()

    def configure(self, service: str, config: RateLimitConfig) -> None:
        with self._lock:
            self._limiters[service] = ServiceRateLimiter(config)
            log.debug("rate limiter configured", extra={"service": service, "rps": config.requests_per_second})

    def is_allowed(self, service: str) -> bool:
        with self._lock:
            limiter = self._limiters.get(service)
        if limiter is None:
            return True
        allowed = limiter.is_allowed()
        if not allowed:
            log.warning("rate limit exceeded", extra={"service": service})
        return allowed

    def remove(self, service: str) -> None:
        with self._lock:
            self._limiters.pop(service, None)

    def services(self) -> list:
        with self._lock:
            return list(self._limiters.keys())
