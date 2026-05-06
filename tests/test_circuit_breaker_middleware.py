"""Tests for porthole.circuit_breaker_middleware."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from porthole.circuit_breaker import CircuitBreakerConfig, CircuitBreakerRegistry
from porthole.circuit_breaker_middleware import circuit_broken_proxy


def _make_request():
    req = MagicMock()
    req.wfile = MagicMock()
    return req


def _make_registry(failure_threshold: int = 5) -> CircuitBreakerRegistry:
    return CircuitBreakerRegistry(CircuitBreakerConfig(failure_threshold=failure_threshold))


def test_allowed_request_calls_next_handler():
    registry = _make_registry()
    next_handler = MagicMock(return_value=200)
    handler = circuit_broken_proxy(next_handler, registry, "svc")
    req = _make_request()
    status = handler(req)
    assert status == 200
    next_handler.assert_called_once_with(req)


def test_5xx_records_failure():
    registry = _make_registry()
    next_handler = MagicMock(return_value=502)
    handler = circuit_broken_proxy(next_handler, registry, "svc")
    handler(_make_request())
    assert registry._get("svc").failure_count == 1


def test_2xx_records_success():
    registry = _make_registry()
    # Prime with one failure so we can verify reset
    registry.record_failure("svc")
    next_handler = MagicMock(return_value=200)
    handler = circuit_broken_proxy(next_handler, registry, "svc")
    handler(_make_request())
    assert registry._get("svc").failure_count == 0


def test_open_circuit_returns_503():
    registry = _make_registry(failure_threshold=1)
    registry.record_failure("svc")  # open the circuit
    next_handler = MagicMock(return_value=200)
    handler = circuit_broken_proxy(next_handler, registry, "svc")
    req = _make_request()
    status = handler(req)
    assert status == 503
    next_handler.assert_not_called()


def test_open_circuit_writes_body():
    registry = _make_registry(failure_threshold=1)
    registry.record_failure("svc")
    handler = circuit_broken_proxy(MagicMock(return_value=200), registry, "svc")
    req = _make_request()
    handler(req)
    written = req.wfile.write.call_args[0][0]
    assert b"circuit open" in written
