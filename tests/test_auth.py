"""Tests for porthole.auth."""

from __future__ import annotations

import types
from unittest.mock import MagicMock, patch

import pytest

from porthole.auth import AuthConfig, AuthRegistry, auth_proxy


# ---------------------------------------------------------------------------
# AuthConfig
# ---------------------------------------------------------------------------


def test_config_rejects_empty_tokens():
    with pytest.raises(ValueError, match="tokens"):
        AuthConfig(tokens=[])


def test_config_rejects_empty_header():
    with pytest.raises(ValueError, match="header"):
        AuthConfig(tokens=["tok"], header="   ")


def test_config_valid_token():
    cfg = AuthConfig(tokens=["secret"])
    assert cfg.is_valid("secret") is True


def test_config_invalid_token():
    cfg = AuthConfig(tokens=["secret"])
    assert cfg.is_valid("wrong") is False


def test_config_multiple_tokens():
    cfg = AuthConfig(tokens=["alpha", "beta"])
    assert cfg.is_valid("alpha") is True
    assert cfg.is_valid("beta") is True
    assert cfg.is_valid("gamma") is False


def test_config_bearer_prefix_not_stripped_by_is_valid():
    # is_valid receives the already-stripped token; "Bearer x" should not match "x"
    cfg = AuthConfig(tokens=["tok"])
    assert cfg.is_valid("Bearer tok") is False


# ---------------------------------------------------------------------------
# AuthRegistry
# ---------------------------------------------------------------------------


def test_registry_get_missing_returns_none():
    reg = AuthRegistry()
    assert reg.get("unknown") is None


def test_registry_register_and_get():
    reg = AuthRegistry()
    cfg = AuthConfig(tokens=["t"])
    reg.register("svc", cfg)
    assert reg.get("svc") is cfg


def test_registry_services_lists_names():
    reg = AuthRegistry()
    reg.register("a", AuthConfig(tokens=["x"]))
    reg.register("b", AuthConfig(tokens=["y"]))
    assert set(reg.services()) == {"a", "b"}


# ---------------------------------------------------------------------------
# auth_proxy middleware
# ---------------------------------------------------------------------------


def _make_handler(auth_header_value: str | None = None, headers_mutable: bool = True):
    """Build a minimal fake request_handler."""
    handler = MagicMock()
    headers = {}
    if auth_header_value is not None:
        headers["Authorization"] = auth_header_value
    # Support dict-style deletion
    handler.headers = headers
    handler.wfile = MagicMock()
    return handler


def test_no_config_passes_through():
    reg = AuthRegistry()  # empty
    next_h = MagicMock()
    middleware = auth_proxy(next_h, reg, "svc")
    rh = _make_handler()
    middleware(rh)
    next_h.assert_called_once_with(rh)


def test_valid_token_calls_next():
    reg = AuthRegistry()
    reg.register("svc", AuthConfig(tokens=["good"]))
    next_h = MagicMock()
    middleware = auth_proxy(next_h, reg, "svc")
    rh = _make_handler("Bearer good")
    middleware(rh)
    next_h.assert_called_once_with(rh)


def test_invalid_token_returns_401():
    reg = AuthRegistry()
    reg.register("svc", AuthConfig(tokens=["good"]))
    next_h = MagicMock()
    middleware = auth_proxy(next_h, reg, "svc")
    rh = _make_handler("Bearer bad")
    middleware(rh)
    next_h.assert_not_called()
    rh.send_response.assert_called_once_with(401)
    rh.wfile.write.assert_called_once_with(b"Unauthorized")


def test_missing_token_returns_401():
    reg = AuthRegistry()
    reg.register("svc", AuthConfig(tokens=["good"]))
    next_h = MagicMock()
    middleware = auth_proxy(next_h, reg, "svc")
    rh = _make_handler()  # no auth header
    middleware(rh)
    next_h.assert_not_called()
    rh.send_response.assert_called_once_with(401)


def test_strip_header_removes_auth_before_forwarding():
    reg = AuthRegistry()
    reg.register("svc", AuthConfig(tokens=["tok"], strip_header=True))
    next_h = MagicMock()
    middleware = auth_proxy(next_h, reg, "svc")
    rh = _make_handler("Bearer tok")
    middleware(rh)
    assert "Authorization" not in rh.headers


def test_no_strip_header_keeps_auth():
    reg = AuthRegistry()
    reg.register("svc", AuthConfig(tokens=["tok"], strip_header=False))
    next_h = MagicMock()
    middleware = auth_proxy(next_h, reg, "svc")
    rh = _make_handler("Bearer tok")
    middleware(rh)
    assert rh.headers.get("Authorization") == "Bearer tok"
