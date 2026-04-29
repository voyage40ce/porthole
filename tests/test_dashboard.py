"""Tests for porthole.dashboard."""

from __future__ import annotations

import io
from unittest.mock import patch

import pytest

from porthole.config import PortholeConfig, ServiceConfig
from porthole.dashboard import render_dashboard
from porthole.healthcheck import HealthStatus


def _make_config(*services: ServiceConfig) -> PortholeConfig:
    return PortholeConfig(services=list(services))


@pytest.fixture()
def two_service_config() -> PortholeConfig:
    return _make_config(
        ServiceConfig(name="api", host="api.local", target_host="127.0.0.1", target_port=8001),
        ServiceConfig(name="web", host="web.local", target_host="127.0.0.1", target_port=3000),
    )


def _fake_check_all(config: PortholeConfig):
    return {
        "api": HealthStatus(ok=True, error=None),
        "web": HealthStatus(ok=False, error="Connection refused"),
    }


def test_dashboard_contains_service_names(two_service_config):
    out = io.StringIO()
    with patch("porthole.dashboard.check_all", side_effect=_fake_check_all):
        render_dashboard(two_service_config, out=out)
    text = out.getvalue()
    assert "api" in text
    assert "web" in text


def test_dashboard_shows_up_down(two_service_config):
    out = io.StringIO()
    with patch("porthole.dashboard.check_all", side_effect=_fake_check_all):
        render_dashboard(two_service_config, out=out)
    text = out.getvalue()
    assert "UP" in text
    assert "DOWN" in text


def test_dashboard_shows_error_message(two_service_config):
    out = io.StringIO()
    with patch("porthole.dashboard.check_all", side_effect=_fake_check_all):
        render_dashboard(two_service_config, out=out)
    assert "Connection refused" in out.getvalue()


def test_dashboard_summary_line(two_service_config):
    out = io.StringIO()
    with patch("porthole.dashboard.check_all", side_effect=_fake_check_all):
        render_dashboard(two_service_config, out=out)
    assert "1/2 services healthy" in out.getvalue()


def test_dashboard_all_healthy():
    config = _make_config(
        ServiceConfig(name="svc", host="svc.local", target_host="127.0.0.1", target_port=9000),
    )
    with patch(
        "porthole.dashboard.check_all",
        return_value={"svc": HealthStatus(ok=True, error=None)},
    ):
        out = io.StringIO()
        render_dashboard(config, out=out)
    assert "1/1 services healthy" in out.getvalue()


def test_dashboard_empty_config():
    config = _make_config()
    with patch("porthole.dashboard.check_all", return_value={}):
        out = io.StringIO()
        render_dashboard(config, out=out)
    assert "0/0 services healthy" in out.getvalue()
