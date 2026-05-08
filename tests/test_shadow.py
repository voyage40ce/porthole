"""Tests for porthole.shadow and porthole.shadow_command."""
from __future__ import annotations

import io
import threading
from unittest.mock import MagicMock, patch

import pytest

from porthole.shadow import ShadowConfig, ShadowRegistry, mirror_request
from porthole.shadow_command import _header, _row, run_shadow
from porthole.shadow_middleware import shadow_proxy


# ---------------------------------------------------------------------------
# ShadowConfig validation
# ---------------------------------------------------------------------------

def test_config_rejects_bad_url():
    with pytest.raises(ValueError, match="HTTP URL"):
        ShadowConfig(target="grpc://localhost:9000")


def test_config_rejects_zero_sample_rate():
    with pytest.raises(ValueError, match="sample_rate"):
        ShadowConfig(target="http://localhost:9000", sample_rate=0.0)


def test_config_rejects_sample_rate_above_one():
    with pytest.raises(ValueError, match="sample_rate"):
        ShadowConfig(target="http://localhost:9000", sample_rate=1.1)


def test_config_rejects_non_positive_timeout():
    with pytest.raises(ValueError, match="timeout"):
        ShadowConfig(target="http://localhost:9000", timeout_seconds=0)


def test_config_accepts_valid():
    cfg = ShadowConfig(target="http://shadow:8080", sample_rate=0.5)
    assert cfg.target == "http://shadow:8080"
    assert cfg.sample_rate == 0.5


# ---------------------------------------------------------------------------
# ShadowRegistry
# ---------------------------------------------------------------------------

@pytest.fixture()
def registry():
    reg = ShadowRegistry()
    reg.register("svc-a", ShadowConfig(target="http://shadow-a:9000"))
    return reg


def test_get_registered(registry):
    assert registry.get("svc-a") is not None


def test_get_unknown_returns_none(registry):
    assert registry.get("unknown") is None


def test_mirror_count_starts_at_zero(registry):
    assert registry.mirror_count("svc-a") == 0


def test_increment_increases_count(registry):
    registry._increment("svc-a")
    registry._increment("svc-a")
    assert registry.mirror_count("svc-a") == 2


# ---------------------------------------------------------------------------
# mirror_request (sampling + threading)
# ---------------------------------------------------------------------------

def test_mirror_request_fires_thread(registry):
    cfg = registry.get("svc-a")
    event = threading.Event()

    def fake_urlopen(req, timeout):
        event.set()
        return MagicMock(__enter__=lambda s: s, __exit__=MagicMock(return_value=False))

    with patch("porthole.shadow.urllib.request.urlopen", side_effect=fake_urlopen):
        mirror_request("svc-a", cfg, "GET", "/ping", {}, b"", registry)
        assert event.wait(timeout=2), "mirror thread did not fire"


def test_mirror_request_respects_sample_rate(registry):
    cfg = ShadowConfig(target="http://shadow:9000", sample_rate=0.0001)
    fired = []
    with patch("porthole.shadow.random.random", return_value=0.9999):
        with patch("porthole.shadow.threading.Thread") as mock_thread:
            mirror_request("svc-a", cfg, "GET", "/", {}, b"", registry)
            mock_thread.assert_not_called()


# ---------------------------------------------------------------------------
# shadow_command
# ---------------------------------------------------------------------------

def test_header_contains_columns():
    h = _header()
    assert "SERVICE" in h
    assert "SHADOW TARGET" in h
    assert "SAMPLE" in h
    assert "MIRRORED" in h


def test_row_formats_values():
    r = _row("my-svc", "http://shadow:9000", 0.5, 42)
    assert "my-svc" in r
    assert "http://shadow:9000" in r
    assert "50%" in r
    assert "42" in r


def test_run_shadow_no_services_prints_message(capsys):
    run_shadow(ShadowRegistry())
    out = capsys.readouterr().out
    assert "No shadow" in out


def test_run_shadow_shows_service(capsys, registry):
    run_shadow(registry)
    out = capsys.readouterr().out
    assert "svc-a" in out
    assert "shadow-a" in out


# ---------------------------------------------------------------------------
# shadow_middleware
# ---------------------------------------------------------------------------

def _make_request_handler(body: bytes = b""):
    handler = MagicMock()
    handler.command = "POST"
    handler.path = "/api/test"
    handler.headers = {"Content-Type": "application/json", "Content-Length": str(len(body))}
    handler.rfile = io.BytesIO(body)
    return handler


def test_middleware_calls_next_handler(registry):
    next_h = MagicMock(return_value=200)
    wrapped = shadow_proxy("svc-a", registry, next_h)
    rh = _make_request_handler(b'{"x":1}')
    with patch("porthole.shadow_middleware.mirror_request"):
        result = wrapped(rh)
    assert result == 200
    next_h.assert_called_once()


def test_middleware_no_config_skips_mirror():
    reg = ShadowRegistry()  # empty
    next_h = MagicMock(return_value=200)
    wrapped = shadow_proxy("unknown", reg, next_h)
    rh = _make_request_handler()
    with patch("porthole.shadow_middleware.mirror_request") as mock_mirror:
        wrapped(rh)
        mock_mirror.assert_not_called()
