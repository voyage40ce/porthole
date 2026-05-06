"""Tests for porthole.retry."""
from __future__ import annotations

import pytest

from porthole.retry import RetryConfig, retry_proxy


# ---------------------------------------------------------------------------
# RetryConfig validation
# ---------------------------------------------------------------------------

def test_config_rejects_zero_attempts():
    with pytest.raises(ValueError, match="max_attempts"):
        RetryConfig(max_attempts=0)


def test_config_rejects_negative_backoff():
    with pytest.raises(ValueError, match="backoff_base_ms"):
        RetryConfig(backoff_base_ms=-1)


def test_config_rejects_low_multiplier():
    with pytest.raises(ValueError, match="backoff_multiplier"):
        RetryConfig(backoff_multiplier=0.5)


def test_delay_first_attempt_is_zero():
    cfg = RetryConfig(backoff_base_ms=200, backoff_multiplier=2.0)
    assert cfg.delay_for_attempt(0) == 0.0


def test_delay_second_attempt():
    cfg = RetryConfig(backoff_base_ms=200, backoff_multiplier=2.0)
    assert cfg.delay_for_attempt(1) == pytest.approx(0.2)


def test_delay_third_attempt():
    cfg = RetryConfig(backoff_base_ms=100, backoff_multiplier=2.0)
    assert cfg.delay_for_attempt(2) == pytest.approx(0.2)


# ---------------------------------------------------------------------------
# retry_proxy behaviour
# ---------------------------------------------------------------------------

def _make_sequence(*statuses):
    """Return a handler that yields statuses in order."""
    it = iter(statuses)

    def handler(_req, _path):
        return next(it)

    return handler


def test_success_on_first_attempt_no_retry():
    calls = []

    def inner(req, path):
        calls.append(1)
        return 200

    wrapped = retry_proxy(inner, RetryConfig(max_attempts=3))
    status = wrapped(None, None)
    assert status == 200
    assert len(calls) == 1


def test_retries_on_502(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)
    handler = _make_sequence(502, 502, 200)
    wrapped = retry_proxy(handler, RetryConfig(max_attempts=3))
    assert wrapped(None, None) == 200


def test_exhausts_attempts_returns_last_status(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)
    handler = _make_sequence(503, 503, 503)
    wrapped = retry_proxy(handler, RetryConfig(max_attempts=3))
    assert wrapped(None, None) == 503


def test_non_retryable_status_not_retried():
    calls = []

    def inner(req, path):
        calls.append(1)
        return 404

    wrapped = retry_proxy(inner, RetryConfig(max_attempts=3))
    status = wrapped(None, None)
    assert status == 404
    assert len(calls) == 1


def test_default_config_used_when_none():
    calls = []

    def inner(req, path):
        calls.append(1)
        return 200

    wrapped = retry_proxy(inner)
    assert wrapped(None, None) == 200
