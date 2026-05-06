"""Tests for porthole.timeout — TimeoutConfig, TimeoutRegistry, timeout_proxy."""

from __future__ import annotations

import socket
from unittest.mock import MagicMock, patch

import pytest

from porthole.timeout import TimeoutConfig, TimeoutRegistry, timeout_proxy


# ---------------------------------------------------------------------------
# TimeoutConfig
# ---------------------------------------------------------------------------


def test_config_defaults():
    cfg = TimeoutConfig()
    assert cfg.connect_timeout == 30.0
    assert cfg.read_timeout == 30.0


def test_config_total():
    cfg = TimeoutConfig(connect_timeout=5.0, read_timeout=10.0)
    assert cfg.total == 15.0


def test_config_rejects_zero_connect():
    with pytest.raises(ValueError, match="connect_timeout"):
        TimeoutConfig(connect_timeout=0)


def test_config_rejects_negative_read():
    with pytest.raises(ValueError, match="read_timeout"):
        TimeoutConfig(read_timeout=-1.0)


# ---------------------------------------------------------------------------
# TimeoutRegistry
# ---------------------------------------------------------------------------


@pytest.fixture()
def registry() -> TimeoutRegistry:
    return TimeoutRegistry(defaults=TimeoutConfig(connect_timeout=5.0, read_timeout=5.0))


def test_registry_returns_default_for_unknown(registry):
    cfg = registry.get("unknown-service")
    assert cfg.connect_timeout == 5.0
    assert cfg.read_timeout == 5.0


def test_registry_stores_custom_config(registry):
    custom = TimeoutConfig(connect_timeout=1.0, read_timeout=2.0)
    registry.register("svc-a", custom)
    assert registry.get("svc-a") is custom


def test_registry_reset_falls_back_to_default(registry):
    registry.register("svc-b", TimeoutConfig(connect_timeout=1.0, read_timeout=1.0))
    registry.reset("svc-b")
    assert registry.get("svc-b").connect_timeout == 5.0


def test_registry_reset_missing_service_does_not_raise(registry):
    registry.reset("nonexistent")  # should not raise


# ---------------------------------------------------------------------------
# timeout_proxy middleware
# ---------------------------------------------------------------------------


def _make_registry(connect: float = 5.0, read: float = 5.0) -> TimeoutRegistry:
    return TimeoutRegistry(defaults=TimeoutConfig(connect_timeout=connect, read_timeout=read))


def test_timeout_proxy_calls_next_handler():
    next_handler = MagicMock(return_value=(200, {}, b"ok"))
    handler = timeout_proxy(next_handler, _make_registry(), "svc")
    result = handler({"path": "/"})
    assert result == (200, {}, b"ok")
    next_handler.assert_called_once_with({"path": "/"})


def test_timeout_proxy_sets_and_restores_socket_timeout():
    original = socket.getdefaulttimeout()
    captured: list[float] = []

    def next_handler(req):
        captured.append(socket.getdefaulttimeout())
        return (200, {}, b"")

    reg = _make_registry(connect=3.0, read=7.0)
    handler = timeout_proxy(next_handler, reg, "svc")
    handler({})

    assert captured[0] == 10.0  # connect + read
    assert socket.getdefaulttimeout() == original


def test_timeout_proxy_restores_timeout_on_exception():
    original = socket.getdefaulttimeout()

    def boom(req):
        raise socket.timeout("timed out")

    handler = timeout_proxy(boom, _make_registry(), "svc")
    with pytest.raises(socket.timeout):
        handler({})

    assert socket.getdefaulttimeout() == original
