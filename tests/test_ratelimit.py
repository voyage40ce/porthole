"""Tests for porthole.ratelimit."""
import time
import pytest

from porthole.ratelimit import RateLimitConfig, RateLimitRegistry, ServiceRateLimiter


def test_rate_limit_config_rejects_zero_rps():
    with pytest.raises(ValueError, match="requests_per_second"):
        RateLimitConfig(requests_per_second=0)


def test_rate_limit_config_rejects_zero_burst():
    with pytest.raises(ValueError, match="burst"):
        RateLimitConfig(requests_per_second=1, burst=0)


def test_single_request_always_allowed():
    limiter = ServiceRateLimiter(RateLimitConfig(requests_per_second=1, burst=1))
    assert limiter.is_allowed() is True


def test_burst_allows_multiple_requests():
    limiter = ServiceRateLimiter(RateLimitConfig(requests_per_second=10, burst=3))
    now = time.monotonic()
    assert limiter.is_allowed(now) is True
    assert limiter.is_allowed(now) is True
    assert limiter.is_allowed(now) is True
    assert limiter.is_allowed(now) is False


def test_window_expires_allows_new_requests():
    limiter = ServiceRateLimiter(RateLimitConfig(requests_per_second=10, burst=1))
    t0 = 100.0
    assert limiter.is_allowed(t0) is True
    assert limiter.is_allowed(t0) is False
    # Advance beyond the window
    assert limiter.is_allowed(t0 + limiter.window_seconds + 0.01) is True


def test_registry_unknown_service_is_allowed():
    registry = RateLimitRegistry()
    assert registry.is_allowed("unknown") is True


def test_registry_configure_and_enforce():
    from porthole.ratelimit import RateLimitConfig
    registry = RateLimitRegistry()
    registry.configure("api", RateLimitConfig(requests_per_second=5, burst=1))
    now = time.monotonic()
    assert registry.is_allowed("api") is True
    assert registry.is_allowed("api") is False


def test_registry_remove_clears_limiter():
    registry = RateLimitRegistry()
    registry.configure("svc", RateLimitConfig(requests_per_second=1, burst=1))
    registry.remove("svc")
    # After removal, unlimited
    assert registry.is_allowed("svc") is True
    assert "svc" not in registry.services()


def test_registry_services_lists_configured():
    registry = RateLimitRegistry()
    registry.configure("a", RateLimitConfig(requests_per_second=1))
    registry.configure("b", RateLimitConfig(requests_per_second=2))
    assert set(registry.services()) == {"a", "b"}
