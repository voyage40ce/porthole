"""Tests for porthole.cache."""

import time
import pytest

from porthole.cache import CacheConfig, ResponseCache


# ---------------------------------------------------------------------------
# CacheConfig validation
# ---------------------------------------------------------------------------

def test_config_rejects_zero_ttl():
    with pytest.raises(ValueError, match="ttl_seconds"):
        CacheConfig(ttl_seconds=0)


def test_config_rejects_negative_ttl():
    with pytest.raises(ValueError, match="ttl_seconds"):
        CacheConfig(ttl_seconds=-1.0)


def test_config_rejects_zero_max_entries():
    with pytest.raises(ValueError, match="max_entries"):
        CacheConfig(max_entries=0)


# ---------------------------------------------------------------------------
# Basic get / put
# ---------------------------------------------------------------------------

@pytest.fixture()
def cache():
    return ResponseCache(CacheConfig(ttl_seconds=60, max_entries=8))


def test_miss_returns_none(cache):
    assert cache.get("GET", "/api/foo") is None


def test_put_and_get(cache):
    cache.put("GET", "/api/foo", 200, [("content-type", "application/json")], b'{"ok":true}')
    entry = cache.get("GET", "/api/foo")
    assert entry is not None
    assert entry.status == 200
    assert entry.body == b'{"ok":true}'


def test_non_get_not_cached(cache):
    cache.put("POST", "/api/foo", 201, [], b"created")
    assert cache.get("POST", "/api/foo") is None


def test_head_is_cached(cache):
    cache.put("HEAD", "/ping", 200, [], b"")
    assert cache.get("HEAD", "/ping") is not None


# ---------------------------------------------------------------------------
# TTL expiry
# ---------------------------------------------------------------------------

def test_expired_entry_returns_none():
    short_cache = ResponseCache(CacheConfig(ttl_seconds=0.05))
    short_cache.put("GET", "/x", 200, [], b"data")
    time.sleep(0.1)
    assert short_cache.get("GET", "/x") is None


# ---------------------------------------------------------------------------
# Invalidation and clear
# ---------------------------------------------------------------------------

def test_invalidate_removes_entry(cache):
    cache.put("GET", "/a", 200, [], b"a")
    cache.invalidate("GET", "/a")
    assert cache.get("GET", "/a") is None


def test_invalidate_missing_does_not_raise(cache):
    cache.invalidate("GET", "/nonexistent")  # should not raise


def test_clear_empties_cache(cache):
    cache.put("GET", "/a", 200, [], b"a")
    cache.put("GET", "/b", 200, [], b"b")
    cache.clear()
    assert cache.size == 0


# ---------------------------------------------------------------------------
# Max entries / eviction
# ---------------------------------------------------------------------------

def test_max_entries_evicts_oldest():
    small_cache = ResponseCache(CacheConfig(ttl_seconds=60, max_entries=3))
    for i in range(3):
        small_cache.put("GET", f"/p{i}", 200, [], b"x")
    assert small_cache.size == 3
    small_cache.put("GET", "/p_new", 200, [], b"y")
    assert small_cache.size == 3
