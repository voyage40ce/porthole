"""Tests for porthole.middleware."""

from __future__ import annotations

import logging

import pytest

from porthole.logger import configure_logging
from porthole.middleware import build_access_log_prefix, timed_proxy


@pytest.fixture(autouse=True)
def _reset_logging():
    configure_logging(level="debug")
    yield


def test_timed_proxy_returns_status_code():
    status = timed_proxy("GET", "svc.local", "/ping", lambda: 200)
    assert status == 200


def test_timed_proxy_passes_through_non_200():
    status = timed_proxy("POST", "svc.local", "/data", lambda: 503)
    assert status == 503


def test_timed_proxy_re_raises_exceptions():
    def boom() -> int:
        raise ConnectionRefusedError("no server")

    with pytest.raises(ConnectionRefusedError):
        timed_proxy("GET", "svc.local", "/", boom)


def test_timed_proxy_logs_on_success(caplog):
    with caplog.at_level(logging.INFO, logger="porthole.middleware"):
        timed_proxy("DELETE", "svc.local", "/item/1", lambda: 204)
    assert any("proxied" in r.message for r in caplog.records)


def test_timed_proxy_logs_on_error(caplog):
    with caplog.at_level(logging.ERROR, logger="porthole.middleware"):
        with pytest.raises(RuntimeError):
            timed_proxy("GET", "svc.local", "/boom", lambda: (_ for _ in ()).throw(RuntimeError("oops")))
    assert any("proxy error" in r.message for r in caplog.records)


def test_build_access_log_prefix():
    prefix = build_access_log_prefix("GET", "api.local", "/v1/users")
    assert prefix == "GET api.local/v1/users"


def test_build_access_log_prefix_with_query():
    prefix = build_access_log_prefix("GET", "api.local", "/search?q=foo")
    assert "?q=foo" in prefix
