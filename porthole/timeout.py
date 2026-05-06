"""Per-service request timeout enforcement for proxied connections."""

from __future__ import annotations

import socket
from dataclasses import dataclass, field
from http.client import HTTPConnection, HTTPException
from typing import Dict, Optional

from porthole.logger import get_logger

logger = get_logger("porthole.timeout")

_DEFAULT_TIMEOUT = 30.0  # seconds


@dataclass
class TimeoutConfig:
    """Timeout settings for a single service."""

    connect_timeout: float = _DEFAULT_TIMEOUT
    read_timeout: float = _DEFAULT_TIMEOUT

    def __post_init__(self) -> None:
        if self.connect_timeout <= 0:
            raise ValueError("connect_timeout must be positive")
        if self.read_timeout <= 0:
            raise ValueError("read_timeout must be positive")

    @property
    def total(self) -> float:
        return self.connect_timeout + self.read_timeout


class TimeoutRegistry:
    """Holds per-service TimeoutConfig instances."""

    def __init__(self, defaults: Optional[TimeoutConfig] = None) -> None:
        self._defaults = defaults or TimeoutConfig()
        self._registry: Dict[str, TimeoutConfig] = {}

    def register(self, service_name: str, config: TimeoutConfig) -> None:
        """Register a timeout config for *service_name*."""
        self._registry[service_name] = config
        logger.debug("Registered timeout for %s: %s", service_name, config)

    def get(self, service_name: str) -> TimeoutConfig:
        """Return the config for *service_name*, falling back to defaults."""
        return self._registry.get(service_name, self._defaults)

    def reset(self, service_name: str) -> None:
        """Remove any custom config for *service_name*."""
        self._registry.pop(service_name, None)


def timeout_proxy(next_handler, registry: TimeoutRegistry, service_name: str):
    """Middleware that enforces connect/read timeouts for *service_name*.

    Wraps *next_handler* (a callable accepting a single ``request`` dict and
    returning a ``(status_code, headers, body)`` tuple) and raises
    ``socket.timeout`` if the upstream call exceeds the configured limits.
    """

    cfg = registry.get(service_name)

    def handler(request: dict):
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(cfg.total)
        try:
            return next_handler(request)
        except (socket.timeout, TimeoutError) as exc:
            logger.warning(
                "Timeout for service %s after %.1fs: %s",
                service_name,
                cfg.total,
                exc,
            )
            raise
        finally:
            socket.setdefaulttimeout(old_timeout)

    return handler
