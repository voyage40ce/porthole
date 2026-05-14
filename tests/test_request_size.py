"""Tests for porthole.request_size."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from porthole.request_size import (
    RequestSizeConfig,
    RequestSizeRegistry,
    size_limited_proxy,
)


# ---------------------------------------------------------------------------
# RequestSizeConfig validation
# ---------------------------------------------------------------------------

def test_config_rejects_zero_max_request():
    with pytest.raises(ValueError, match="max_request_bytes"):
        RequestSizeConfig(max_request_bytes=0)


def test_config_rejects_negative_max_response():
    with pytest.raises(ValueError, match="max_response_bytes"):
        RequestSizeConfig(max_response_bytes=-1)


def test_config_accepts_valid():
    cfg = RequestSizeConfig(max_request_bytes=512, max_response_bytes=2048)
    assert cfg.max_request_bytes == 512
    assert cfg.max_response_bytes == 2048


def test_config_defaults():
    cfg = RequestSizeConfig()
    assert cfg.max_request_bytes == 1 * 1024 * 1024
    assert cfg.max_response_bytes == 10 * 1024 * 1024


# ---------------------------------------------------------------------------
# RequestSizeRegistry
# ---------------------------------------------------------------------------

@pytest.fixture()
def registry() -> RequestSizeRegistry:
    return RequestSizeRegistry()


def test_get_missing_returns_none(registry):
    assert registry.get("unknown") is None


def test_register_and_get(registry):
    cfg = RequestSizeConfig(max_request_bytes=1024, max_response_bytes=4096)
    registry.register("svc", cfg)
    assert registry.get("svc") is cfg


def test_all_services(registry):
    registry.register("a", RequestSizeConfig())
    registry.register("b", RequestSizeConfig())
    assert set(registry.all_services()) == {"a", "b"}


# ---------------------------------------------------------------------------
# size_limited_proxy middleware
# ---------------------------------------------------------------------------

def _make_request_handler(content_length: str | None = None):
    rh = MagicMock()
    if content_length is None:
        rh.headers = {}
    else:
        rh.headers = {"Content-Length": content_length}
    return rh


def test_allowed_request_calls_next_handler(registry):
    registry.register("svc", RequestSizeConfig(max_request_bytes=1024))
    next_handler = MagicMock(return_value=200)
    handler = size_limited_proxy(registry, "svc", next_handler)
    rh = _make_request_handler(content_length="512")
    result = handler(rh)
    next_handler.assert_called_once_with(rh)
    assert result == 200


def test_oversized_request_returns_413(registry):
    registry.register("svc", RequestSizeConfig(max_request_bytes=100))
    next_handler = MagicMock(return_value=200)
    handler = size_limited_proxy(registry, "svc", next_handler)
    rh = _make_request_handler(content_length="200")
    handler(rh)
    rh.send_response.assert_called_once_with(413)
    next_handler.assert_not_called()


def test_no_content_length_passes_through(registry):
    registry.register("svc", RequestSizeConfig(max_request_bytes=100))
    next_handler = MagicMock(return_value=200)
    handler = size_limited_proxy(registry, "svc", next_handler)
    rh = _make_request_handler(content_length=None)
    handler(rh)
    next_handler.assert_called_once_with(rh)


def test_no_config_passes_through(registry):
    """Service not in registry → no size check performed."""
    next_handler = MagicMock(return_value=200)
    handler = size_limited_proxy(registry, "unknown", next_handler)
    rh = _make_request_handler(content_length="999999999")
    handler(rh)
    next_handler.assert_called_once_with(rh)


def test_invalid_content_length_treated_as_zero(registry):
    """Non-numeric Content-Length should not crash and should pass through."""
    registry.register("svc", RequestSizeConfig(max_request_bytes=100))
    next_handler = MagicMock(return_value=200)
    handler = size_limited_proxy(registry, "svc", next_handler)
    rh = _make_request_handler(content_length="chunked")
    handler(rh)
    next_handler.assert_called_once_with(rh)
