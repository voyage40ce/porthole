"""Tests for porthole.upstream_health."""
from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from porthole.config import PortholeConfig, ServiceConfig
from porthole.healthcheck import HealthStatus
from porthole.upstream_health import UpstreamHealthMonitor


@pytest.fixture()
def two_service_config() -> PortholeConfig:
    return PortholeConfig(
        services=[
            ServiceConfig(name="api", host="localhost", port=8001),
            ServiceConfig(name="web", host="localhost", port=8002),
        ]
    )


def _ok(name: str) -> HealthStatus:
    return HealthStatus(service=name, ok=True, detail="200 OK")


def _err(name: str) -> HealthStatus:
    return HealthStatus(service=name, ok=False, detail="Connection refused")


def test_latest_before_check_returns_none(two_service_config):
    mon = UpstreamHealthMonitor(config=two_service_config)
    assert mon.latest("api") is None


def test_run_checks_populates_statuses(two_service_config):
    mon = UpstreamHealthMonitor(config=two_service_config)
    with patch(
        "porthole.upstream_health.check_service",
        side_effect=lambda svc: _ok(svc.name),
    ):
        mon._run_checks()
    assert mon.latest("api").ok is True
    assert mon.latest("web").ok is True


def test_all_statuses_returns_copy(two_service_config):
    mon = UpstreamHealthMonitor(config=two_service_config)
    with patch(
        "porthole.upstream_health.check_service",
        side_effect=lambda svc: _ok(svc.name),
    ):
        mon._run_checks()
    statuses = mon.all_statuses()
    assert set(statuses.keys()) == {"api", "web"}


def test_callback_invoked_on_status_change(two_service_config):
    mon = UpstreamHealthMonitor(config=two_service_config)
    events: list[tuple[str, bool]] = []
    mon.register_callback(lambda name, st: events.append((name, st.ok)))

    with patch(
        "porthole.upstream_health.check_service",
        side_effect=lambda svc: _ok(svc.name),
    ):
        mon._run_checks()  # first check — status goes from None → UP

    assert ("api", True) in events
    assert ("web", True) in events


def test_callback_not_invoked_when_status_unchanged(two_service_config):
    mon = UpstreamHealthMonitor(config=two_service_config)
    events: list = []
    mon.register_callback(lambda name, st: events.append(name))

    with patch(
        "porthole.upstream_health.check_service",
        side_effect=lambda svc: _ok(svc.name),
    ):
        mon._run_checks()  # first check
        events.clear()
        mon._run_checks()  # second check — same result, no callback

    assert events == []


def test_start_stop_thread(two_service_config):
    mon = UpstreamHealthMonitor(
        config=two_service_config, interval_seconds=0.05
    )
    with patch("porthole.upstream_health.check_service", side_effect=lambda svc: _ok(svc.name)):
        mon.start()
        time.sleep(0.15)
        mon.stop()
    assert not mon._thread.is_alive()


def test_faulty_callback_does_not_crash_monitor(two_service_config):
    mon = UpstreamHealthMonitor(config=two_service_config)
    mon.register_callback(lambda name, st: (_ for _ in ()).throw(RuntimeError("boom")))

    with patch(
        "porthole.upstream_health.check_service",
        side_effect=lambda svc: _ok(svc.name),
    ):
        # Should not raise
        mon._run_checks()
