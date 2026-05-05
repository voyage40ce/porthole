"""Tests for porthole.ratelimit_middleware."""
from __future__ import annotations

import io
from unittest.mock import MagicMock

import pytest

from porthole.ratelimit import RateLimitConfig, RateLimitRegistry
from porthole.ratelimit_middleware import rate_limited_proxy


def _make_handler():
    handler = MagicMock()
    handler.wfile = io.BytesIO()
    return handler


def _make_registry(service: str, rps: float = 100.0, burst: int = 100):
    reg = RateLimitRegistry()
    reg.configure(service, RateLimitConfig(requests_per_second=rps, burst=burst))
    return reg


def test_allowed_request_calls_next_handler():
    handler = _make_handler()
    registry = _make_registry("svc", rps=100, burst=10)
    next_handler = MagicMock(return_value=200)

    status = rate_limited_proxy(handler, "svc", registry, next_handler)

    assert status == 200
    next_handler.assert_called_once_with(handler)


def test_blocked_request_returns_429():
    import time
    handler = _make_handler()
    registry = _make_registry("svc", rps=1, burst=1)
    next_handler = MagicMock(return_value=200)

    now = time.monotonic()
    # Exhaust the single slot
    from porthole.ratelimit import ServiceRateLimiter
    with registry._lock:
        registry._limiters["svc"].is_allowed(now)

    status = rate_limited_proxy(handler, "svc", registry, next_handler)

    assert status == 429
    next_handler.assert_not_called()


def test_blocked_request_writes_body():
    import time
    handler = _make_handler()
    registry = _make_registry("svc", rps=1, burst=1)
    next_handler = MagicMock(return_value=200)

    now = time.monotonic()
    with registry._lock:
        registry._limiters["svc"].is_allowed(now)

    rate_limited_proxy(handler, "svc", registry, next_handler)
    handler.wfile.seek(0)
    assert b"429" in handler.wfile.read()


def test_unknown_service_passes_through():
    handler = _make_handler()
    registry = RateLimitRegistry()  # no services configured
    next_handler = MagicMock(return_value=200)

    status = rate_limited_proxy(handler, "unknown", registry, next_handler)

    assert status == 200
    next_handler.assert_called_once()
