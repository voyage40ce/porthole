"""HTTP middleware that enforces rate limits before proxying."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler
from typing import Callable

from porthole.ratelimit import RateLimitRegistry
from porthole.logger import get_logger

log = get_logger("porthole.ratelimit_middleware")

_TOO_MANY = 429
_RETRY_AFTER = "1"


def rate_limited_proxy(
    handler: BaseHTTPRequestHandler,
    service_name: str,
    registry: RateLimitRegistry,
    next_handler: Callable[[BaseHTTPRequestHandler], int],
) -> int:
    """Wrap *next_handler* with a rate-limit check.

    Returns the HTTP status code produced by the chain.
    """
    if not registry.is_allowed(service_name):
        log.info(
            "request blocked by rate limiter",
            extra={"service": service_name},
        )
        handler.send_response(_TOO_MANY)
        handler.send_header("Content-Type", "text/plain")
        handler.send_header("Retry-After", _RETRY_AFTER)
        handler.end_headers()
        handler.wfile.write(b"429 Too Many Requests\n")
        return _TOO_MANY

    return next_handler(handler)
