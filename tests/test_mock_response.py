"""Tests for porthole.mock_response, mock_response_middleware, and
mock_response_command."""

from __future__ import annotations

import io
import json
from unittest.mock import MagicMock

import pytest

from porthole.mock_response import MockRegistry, MockResponseConfig
from porthole.mock_response_command import _header, _row, run_mock_response
from porthole.mock_response_middleware import mock_proxy


# ---------------------------------------------------------------------------
# MockResponseConfig
# ---------------------------------------------------------------------------

def test_config_rejects_invalid_status():
    with pytest.raises(ValueError, match="status"):
        MockResponseConfig(status=99)


def test_config_rejects_empty_content_type():
    with pytest.raises(ValueError, match="content_type"):
        MockResponseConfig(content_type="")


def test_json_convenience_constructor():
    cfg = MockResponseConfig.json({"ok": True})
    assert cfg.status == 200
    assert json.loads(cfg.body) == {"ok": True}
    assert cfg.content_type == "application/json"


def test_text_convenience_constructor():
    cfg = MockResponseConfig.text("hello", status=201)
    assert cfg.status == 201
    assert cfg.body == "hello"
    assert cfg.content_type == "text/plain"


# ---------------------------------------------------------------------------
# MockRegistry
# ---------------------------------------------------------------------------

@pytest.fixture()
def registry() -> MockRegistry:
    return MockRegistry()


def test_register_and_get(registry):
    cfg = MockResponseConfig.json({"a": 1})
    registry.register("svc-a", cfg)
    assert registry.get("svc-a") is cfg


def test_get_missing_returns_none(registry):
    assert registry.get("missing") is None


def test_register_empty_name_raises(registry):
    with pytest.raises(ValueError):
        registry.register("", MockResponseConfig())


def test_remove_existing(registry):
    registry.register("svc", MockResponseConfig())
    assert registry.remove("svc") is True
    assert registry.get("svc") is None


def test_remove_missing_returns_false(registry):
    assert registry.remove("ghost") is False


def test_clear(registry):
    registry.register("a", MockResponseConfig())
    registry.register("b", MockResponseConfig())
    registry.clear()
    assert registry.all_services() == {}


# ---------------------------------------------------------------------------
# mock_proxy middleware
# ---------------------------------------------------------------------------

def _make_request(host: str) -> MagicMock:
    req = MagicMock()
    req.headers = {"Host": host}
    req.wfile = io.BytesIO()
    return req


def test_mock_proxy_serves_registered_service(registry):
    registry.register("api", MockResponseConfig.json({"mocked": True}, status=200))
    next_handler = MagicMock(return_value=200)
    handler = mock_proxy(registry, next_handler)

    req = _make_request("api")
    status = handler(req)

    assert status == 200
    next_handler.assert_not_called()
    req.send_response.assert_called_once_with(200)


def test_mock_proxy_falls_through_for_unregistered(registry):
    next_handler = MagicMock(return_value=502)
    handler = mock_proxy(registry, next_handler)

    req = _make_request("other-service")
    status = handler(req)

    assert status == 502
    next_handler.assert_called_once_with(req)


def test_mock_proxy_strips_port_from_host(registry):
    registry.register("api", MockResponseConfig.text("ok"))
    next_handler = MagicMock()
    handler = mock_proxy(registry, next_handler)

    req = _make_request("api:8080")
    handler(req)
    next_handler.assert_not_called()


# ---------------------------------------------------------------------------
# mock_response_command
# ---------------------------------------------------------------------------

def test_header_contains_columns():
    h = _header()
    assert "SERVICE" in h
    assert "STATUS" in h
    assert "CONTENT-TYPE" in h


def test_row_truncates_long_body():
    row = _row("svc", 200, "application/json", "x" * 80)
    assert "…" in row


def test_run_mock_response_no_data(registry):
    out = io.StringIO()
    run_mock_response(registry, out=out)
    assert "No mock" in out.getvalue()


def test_run_mock_response_shows_service(registry):
    registry.register("payments", MockResponseConfig.json({"status": "ok"}))
    out = io.StringIO()
    run_mock_response(registry, out=out)
    assert "payments" in out.getvalue()
    assert "200" in out.getvalue()
