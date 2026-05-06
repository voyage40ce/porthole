"""Tests for porthole.cors — CORSConfig and cors_proxy middleware."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, call

from porthole.cors import CORSConfig, cors_proxy


# ---------------------------------------------------------------------------
# CORSConfig validation
# ---------------------------------------------------------------------------

def test_config_rejects_empty_origins():
    with pytest.raises(ValueError, match="allow_origins"):
        CORSConfig(allow_origins=[])


def test_config_rejects_negative_max_age():
    with pytest.raises(ValueError, match="max_age"):
        CORSConfig(max_age=-1)


def test_config_rejects_credentials_with_wildcard():
    with pytest.raises(ValueError, match="allow_credentials"):
        CORSConfig(allow_origins=["*"], allow_credentials=True)


def test_config_credentials_with_explicit_origin():
    cfg = CORSConfig(allow_origins=["https://example.com"], allow_credentials=True)
    assert cfg.allow_credentials is True


# ---------------------------------------------------------------------------
# origin_allowed
# ---------------------------------------------------------------------------

def test_wildcard_allows_any_origin():
    cfg = CORSConfig(allow_origins=["*"])
    assert cfg.origin_allowed("https://random.dev") == "*"


def test_explicit_origin_allowed():
    cfg = CORSConfig(allow_origins=["https://app.example.com"])
    assert cfg.origin_allowed("https://app.example.com") == "https://app.example.com"


def test_unknown_origin_denied():
    cfg = CORSConfig(allow_origins=["https://app.example.com"])
    assert cfg.origin_allowed("https://evil.com") is None


def test_missing_origin_returns_none():
    cfg = CORSConfig()
    assert cfg.origin_allowed(None) is None


# ---------------------------------------------------------------------------
# cors_proxy — preflight
# ---------------------------------------------------------------------------

def _make_handler(command: str = "GET", origin: str = "https://example.com"):
    handler = MagicMock()
    handler.command = command
    handler.headers = {"Origin": origin}
    return handler


def test_preflight_returns_204():
    cfg = CORSConfig(allow_origins=["https://example.com"])
    next_h = MagicMock()
    wrapped = cors_proxy(next_h, cfg)

    proxy = _make_handler(command="OPTIONS")
    wrapped(proxy)

    proxy.send_response.assert_called_once_with(204)
    next_h.assert_not_called()


def test_preflight_sends_allow_origin_header():
    cfg = CORSConfig(allow_origins=["https://example.com"])
    wrapped = cors_proxy(MagicMock(), cfg)
    proxy = _make_handler(command="OPTIONS")
    wrapped(proxy)

    headers_sent = {c.args[0]: c.args[1] for c in proxy.send_header.call_args_list}
    assert headers_sent["Access-Control-Allow-Origin"] == "https://example.com"


def test_preflight_unknown_origin_sends_no_cors_headers():
    cfg = CORSConfig(allow_origins=["https://allowed.com"])
    wrapped = cors_proxy(MagicMock(), cfg)
    proxy = _make_handler(command="OPTIONS", origin="https://evil.com")
    wrapped(proxy)

    header_names = [c.args[0] for c in proxy.send_header.call_args_list]
    assert "Access-Control-Allow-Origin" not in header_names


# ---------------------------------------------------------------------------
# cors_proxy — normal requests
# ---------------------------------------------------------------------------

def test_normal_request_calls_next_handler():
    cfg = CORSConfig()
    next_h = MagicMock()
    wrapped = cors_proxy(next_h, cfg)
    proxy = _make_handler(command="GET")
    wrapped(proxy)
    next_h.assert_called_once_with(proxy)


def test_normal_request_injects_allow_origin():
    cfg = CORSConfig(allow_origins=["*"])
    wrapped = cors_proxy(MagicMock(), cfg)
    proxy = _make_handler(command="POST")
    wrapped(proxy)

    header_names = [c.args[0] for c in proxy.send_header.call_args_list]
    assert "Access-Control-Allow-Origin" in header_names
