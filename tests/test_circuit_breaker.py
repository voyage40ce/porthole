"""Tests for porthole.circuit_breaker."""
import time

import pytest

from porthole.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitBreakerRegistry,
    CircuitState,
)


def test_config_rejects_zero_failure_threshold():
    with pytest.raises(ValueError, match="failure_threshold"):
        CircuitBreakerConfig(failure_threshold=0)


def test_config_rejects_negative_recovery_timeout():
    with pytest.raises(ValueError, match="recovery_timeout"):
        CircuitBreakerConfig(recovery_timeout=-1)


def test_config_rejects_zero_success_threshold():
    with pytest.raises(ValueError, match="success_threshold"):
        CircuitBreakerConfig(success_threshold=0)


@pytest.fixture()
def registry():
    return CircuitBreakerRegistry(CircuitBreakerConfig(failure_threshold=3, recovery_timeout=1.0))


def test_initial_state_is_closed(registry):
    assert registry.state("svc") == CircuitState.CLOSED


def test_single_request_allowed_when_closed(registry):
    assert registry.is_allowed("svc") is True


def test_opens_after_threshold_failures(registry):
    for _ in range(3):
        registry.record_failure("svc")
    assert registry.state("svc") == CircuitState.OPEN


def test_open_circuit_rejects_requests(registry):
    for _ in range(3):
        registry.record_failure("svc")
    assert registry.is_allowed("svc") is False


def test_transitions_to_half_open_after_timeout(registry):
    for _ in range(3):
        registry.record_failure("svc")
    # Manually back-date the opened_at timestamp
    registry._get("svc").opened_at = time.monotonic() - 2.0
    assert registry.is_allowed("svc") is True
    assert registry.state("svc") == CircuitState.HALF_OPEN


def test_closes_after_success_threshold_in_half_open(registry):
    cfg = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0.01, success_threshold=2)
    reg = CircuitBreakerRegistry(cfg)
    for _ in range(2):
        reg.record_failure("svc")
    time.sleep(0.05)
    reg.is_allowed("svc")  # transitions to HALF_OPEN
    reg.record_success("svc")
    reg.record_success("svc")
    assert reg.state("svc") == CircuitState.CLOSED


def test_reopens_on_failure_in_half_open(registry):
    for _ in range(3):
        registry.record_failure("svc")
    registry._get("svc").opened_at = time.monotonic() - 2.0
    registry.is_allowed("svc")  # → HALF_OPEN
    registry.record_failure("svc")
    assert registry.state("svc") == CircuitState.OPEN


def test_success_resets_failure_count_when_closed(registry):
    registry.record_failure("svc")
    registry.record_failure("svc")
    registry.record_success("svc")
    assert registry._get("svc").failure_count == 0


def test_all_states_returns_dict(registry):
    registry.record_failure("a")
    registry.record_failure("b")
    states = registry.all_states()
    assert "a" in states and "b" in states
