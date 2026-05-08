"""Tests for porthole.ip_filter."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from porthole.ip_filter import IPFilterConfig, IPFilterRegistry, ip_filter_proxy


# ---------------------------------------------------------------------------
# IPFilterConfig validation
# ---------------------------------------------------------------------------

def test_config_rejects_both_lists():
    with pytest.raises(ValueError, match="either allowlist or blocklist"):
        IPFilterConfig(allowlist=["10.0.0.0/8"], blocklist=["192.168.1.1"])


def test_config_rejects_invalid_cidr():
    with pytest.raises(ValueError, match="Invalid IP/CIDR"):
        IPFilterConfig(allowlist=["not-an-ip"])


def test_config_accepts_valid_allowlist():
    cfg = IPFilterConfig(allowlist=["10.0.0.0/8", "192.168.1.1"])
    assert len(cfg.allowlist) == 2


def test_config_accepts_valid_blocklist():
    cfg = IPFilterConfig(blocklist=["203.0.113.0/24"])
    assert len(cfg.blocklist) == 1


# ---------------------------------------------------------------------------
# is_allowed logic
# ---------------------------------------------------------------------------

def test_empty_config_allows_all():
    cfg = IPFilterConfig()
    assert cfg.is_allowed("1.2.3.4") is True


def test_allowlist_permits_matching_ip():
    cfg = IPFilterConfig(allowlist=["10.0.0.0/8"])
    assert cfg.is_allowed("10.1.2.3") is True


def test_allowlist_blocks_non_matching_ip():
    cfg = IPFilterConfig(allowlist=["10.0.0.0/8"])
    assert cfg.is_allowed("172.16.0.1") is False


def test_blocklist_blocks_matching_ip():
    cfg = IPFilterConfig(blocklist=["203.0.113.0/24"])
    assert cfg.is_allowed("203.0.113.5") is False


def test_blocklist_permits_non_matching_ip():
    cfg = IPFilterConfig(blocklist=["203.0.113.0/24"])
    assert cfg.is_allowed("8.8.8.8") is True


def test_invalid_client_ip_is_denied():
    cfg = IPFilterConfig(allowlist=["10.0.0.0/8"])
    assert cfg.is_allowed("not-an-ip") is False


# ---------------------------------------------------------------------------
# IPFilterRegistry
# ---------------------------------------------------------------------------

def test_registry_get_missing_returns_none():
    reg = IPFilterRegistry()
    assert reg.get("unknown") is None


def test_registry_register_and_get():
    reg = IPFilterRegistry()
    cfg = IPFilterConfig(allowlist=["127.0.0.1"])
    reg.register("svc-a", cfg)
    assert reg.get("svc-a") is cfg


# ---------------------------------------------------------------------------
# ip_filter_proxy middleware
# ---------------------------------------------------------------------------

def _make_handler(client_ip: str):
    h = MagicMock()
    h.client_address = (client_ip, 54321)
    h.wfile = MagicMock()
    return h


def test_allowed_request_calls_next_handler():
    reg = IPFilterRegistry()
    reg.register("api", IPFilterConfig(allowlist=["127.0.0.0/8"]))
    next_h = MagicMock(return_value=200)
    handler = ip_filter_proxy(reg, "api", next_h)
    rh = _make_handler("127.0.0.1")
    result = handler(rh)
    next_h.assert_called_once_with(rh)
    assert result == 200


def test_blocked_request_returns_403():
    reg = IPFilterRegistry()
    reg.register("api", IPFilterConfig(allowlist=["10.0.0.0/8"]))
    next_h = MagicMock()
    handler = ip_filter_proxy(reg, "api", next_h)
    rh = _make_handler("1.2.3.4")
    result = handler(rh)
    assert result == 403
    next_h.assert_not_called()
    rh.send_response.assert_called_once_with(403)


def test_no_config_passes_through():
    reg = IPFilterRegistry()  # no rules registered
    next_h = MagicMock(return_value=200)
    handler = ip_filter_proxy(reg, "unknown-service", next_h)
    rh = _make_handler("9.9.9.9")
    result = handler(rh)
    assert result == 200
    next_h.assert_called_once_with(rh)
