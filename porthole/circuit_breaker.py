"""Circuit breaker for upstream service fault tolerance."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict


class CircuitState(Enum):
    CLOSED = "closed"      # normal operation
    OPEN = "open"          # failing, reject requests
    HALF_OPEN = "half_open"  # probing if service recovered


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5      # failures before opening
    recovery_timeout: float = 30.0  # seconds before half-open
    success_threshold: int = 2      # successes to close from half-open

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if self.recovery_timeout <= 0:
            raise ValueError("recovery_timeout must be > 0")
        if self.success_threshold < 1:
            raise ValueError("success_threshold must be >= 1")


@dataclass
class _ServiceBreaker:
    config: CircuitBreakerConfig
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    opened_at: float = 0.0

    def record_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def record_failure(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.opened_at = time.monotonic()
            self.success_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count += 1
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                self.opened_at = time.monotonic()

    def is_allowed(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            elapsed = time.monotonic() - self.opened_at
            if elapsed >= self.config.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                return True
            return False
        # HALF_OPEN: allow one probe
        return True


class CircuitBreakerRegistry:
    """Per-service circuit breaker registry."""

    def __init__(self, default_config: CircuitBreakerConfig | None = None) -> None:
        self._config = default_config or CircuitBreakerConfig()
        self._breakers: Dict[str, _ServiceBreaker] = {}

    def _get(self, service: str) -> _ServiceBreaker:
        if service not in self._breakers:
            self._breakers[service] = _ServiceBreaker(config=self._config)
        return self._breakers[service]

    def is_allowed(self, service: str) -> bool:
        return self._get(service).is_allowed()

    def record_success(self, service: str) -> None:
        self._get(service).record_success()

    def record_failure(self, service: str) -> None:
        self._get(service).record_failure()

    def state(self, service: str) -> CircuitState:
        return self._get(service).state

    def all_states(self) -> Dict[str, CircuitState]:
        return {name: b.state for name, b in self._breakers.items()}
