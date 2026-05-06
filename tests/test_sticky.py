"""Tests for porthole.sticky and porthole.sticky_middleware."""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from porthole.sticky import StickyConfig, StickyRegistry
from porthole.sticky_middleware import sticky_proxy


# ---------------------------------------------------------------------------
# StickyConfig validation
# ---------------------------------------------------------------------------

def test_config_rejects_zero_ttl():
    with pytest.raises(ValueError, match="ttl_seconds"):
        StickyConfig(ttl_seconds=0)


def test_config_rejects_negative_ttl():
    with pytest.raises(ValueError, match="ttl_seconds"):
        StickyConfig(ttl_seconds=-1)


def test_config_rejects_empty_header():
    with pytest.raises(ValueError, match="header"):
        StickyConfig(header="   ")


# ---------------------------------------------------------------------------
# StickyRegistry
# ---------------------------------------------------------------------------

@pytest.fixture()
def registry() -> StickyRegistry:
    return StickyRegistry(StickyConfig(ttl_seconds=60))


def test_get_missing_returns_none(registry: StickyRegistry):
    assert registry.get("unknown-token") is None


def test_pin_and_get(registry: StickyRegistry):
    registry.pin("tok1", "http://localhost:8001")
    assert registry.get("tok1") == "http://localhost:8001"


def test_get_expired_returns_none():
    reg = StickyRegistry(StickyConfig(ttl_seconds=0.01))
    reg.pin("tok", "http://localhost:9000")
    time.sleep(0.05)
    assert reg.get("tok") is None


def test_pick_and_pin_consistent(registry: StickyRegistry):
    upstreams = ["http://a:8001", "http://b:8002", "http://c:8003"]
    first = registry.pick_and_pin("session-abc", upstreams)
    second = registry.pick_and_pin("session-abc", upstreams)
    assert first == second


def test_pick_and_pin_empty_upstreams_raises(registry: StickyRegistry):
    with pytest.raises(ValueError, match="upstreams"):
        registry.pick_and_pin("tok", [])


def test_purge_expired_removes_stale():
    reg = StickyRegistry(StickyConfig(ttl_seconds=0.01))
    reg.pin("old", "http://localhost:8001")
    reg.pin("new", "http://localhost:8002")
    # Manually expire 'old'
    reg._store["old"].expires_at = time.monotonic() - 1
    removed = reg.purge_expired()
    assert removed == 1
    assert reg.get("new") == "http://localhost:8002"


def test_stats_active_count(registry: StickyRegistry):
    registry.pin("a", "http://localhost:8001")
    registry.pin("b", "http://localhost:8002")
    registry._store["b"].expires_at = time.monotonic() - 1
    stats = registry.stats()
    assert stats["total"] == 2
    assert stats["active"] == 1


# ---------------------------------------------------------------------------
# sticky_middleware
# ---------------------------------------------------------------------------

def _make_request(token: str = "") -> MagicMock:
    req = MagicMock()
    req.headers = {"X-Porthole-Session": token} if token else {}
    req.__dict__["_sticky_upstream"] = None
    return req


def test_middleware_pins_new_token():
    reg = StickyRegistry(StickyConfig(ttl_seconds=60))
    upstreams = ["http://svc:8001", "http://svc:8002"]
    inner = MagicMock(return_value=200)
    handler = sticky_proxy(inner, upstreams, reg, StickyConfig())

    req = _make_request()
    status = handler(req)

    assert status == 200
    token = req.__dict__["_sticky_token"]
    assert token != ""
    assert reg.get(token) in upstreams


def test_middleware_reuses_existing_token():
    reg = StickyRegistry(StickyConfig(ttl_seconds=60))
    upstreams = ["http://svc:8001", "http://svc:8002"]
    reg.pin("fixed-token", upstreams[0])

    inner = MagicMock(return_value=200)
    handler = sticky_proxy(inner, upstreams, reg, StickyConfig())

    req = _make_request(token="fixed-token")
    handler(req)

    assert req.__dict__["_sticky_upstream"] == upstreams[0]
