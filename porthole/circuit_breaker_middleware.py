"""Middleware that wraps proxy requests with circuit-breaker logic."""
from __future__ import annotations

import http.server
from typing import Callable

from porthole.circuit_breaker import CircuitBreakerRegistry
from porthole.logger import get_logger

logger = get_logger("porthole.circuit_breaker_middleware")

ProxyHandler = Callable[[http.server.BaseHTTPRequestHandler], int]


def circuit_broken_proxy(
    next_handler: ProxyHandler,
    registry: CircuitBreakerRegistry,
    service_name: str,
) -> ProxyHandler:
    """Return a handler that enforces the circuit breaker for *service_name*."""

    def handler(request: http.server.BaseHTTPRequestHandler) -> int:
        if not registry.is_allowed(service_name):
            logger.warning("circuit open for %s — rejecting request", service_name)
            request.send_response(503)
            request.send_header("Content-Type", "text/plain")
            request.end_headers()
            request.wfile.write(
                f"Service '{service_name}' is temporarily unavailable (circuit open).\n".encode()
            )
            return 503

        status = next_handler(request)

        if status >= 500:
            registry.record_failure(service_name)
            logger.debug("circuit breaker failure recorded for %s (status=%s)", service_name, status)
        else:
            registry.record_success(service_name)

        return status

    return handler
