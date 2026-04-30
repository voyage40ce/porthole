"""Request middleware: timing and per-request logging."""

from __future__ import annotations

import time
from typing import Callable

from porthole.logger import get_logger, log_request

_logger = get_logger("middleware")

# Type alias for a simple WSGI-like handler callable used in tests.
Handler = Callable[[str, str, str], int]


def timed_proxy(
    method: str,
    host: str,
    path: str,
    call: Callable[[], int],
) -> int:
    """Call *call*, measure wall-clock time, log the result, return status code.

    Parameters
    ----------
    method:
        HTTP verb (GET, POST, …).
    host:
        Destination virtual-host header value.
    path:
        Request path including query string.
    call:
        Zero-argument callable that performs the actual proxy and returns an
        HTTP status code (int).
    """
    start = time.perf_counter()
    try:
        status = call()
    except Exception as exc:  # noqa: BLE001
        elapsed = (time.perf_counter() - start) * 1000
        _logger.error(
            "proxy error: %s",
            exc,
            extra={"method": method, "host": host, "path": path, "duration_ms": round(elapsed, 2)},
        )
        raise
    elapsed = (time.perf_counter() - start) * 1000
    log_request(_logger, method, host, path, status, elapsed)
    return status


def build_access_log_prefix(method: str, host: str, path: str) -> str:
    """Return a human-readable prefix string for access log lines."""
    return f"{method} {host}{path}"
