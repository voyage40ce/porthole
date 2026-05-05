"""Middleware helpers: timing wrapper and access-log prefix builder."""

from __future__ import annotations

import time
from typing import Callable

from porthole.logger import get_logger
from porthole.metrics import get_collector

log = get_logger("porthole.middleware")


def build_access_log_prefix(method: str, path: str, service: str) -> str:
    return f"[{service}] {method} {path}"


def timed_proxy(
    handler_fn: Callable[[], int],
    *,
    method: str,
    path: str,
    service: str,
) -> int:
    """Call *handler_fn*, measure elapsed time, log it, record metrics.

    Returns the HTTP status code returned by *handler_fn*.
    Propagates any exception raised by *handler_fn* after logging.
    """
    prefix = build_access_log_prefix(method, path, service)
    start = time.perf_counter()
    try:
        status = handler_fn()
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        log.error("%s -> ERROR after %.1f ms: %s", prefix, elapsed, exc)
        raise
    elapsed = (time.perf_counter() - start) * 1000
    log.info("%s -> %d (%.1f ms)", prefix, status, elapsed)
    get_collector().record(service, status, elapsed)
    return status
