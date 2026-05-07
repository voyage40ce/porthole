"""Tests for porthole.upstream_health_command."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from porthole.config import PortholeConfig, ServiceConfig
from porthole.healthcheck import HealthStatus
from porthole.upstream_health_command import _header, _row, run_upstream_health


@pytest.fixture()
def simple_config() -> PortholeConfig:
    return PortholeConfig(
        services=[ServiceConfig(name="api", host="localhost", port=8001)]
    )


def _ok_status(name: str) -> HealthStatus:
    return HealthStatus(service=name, ok=True, detail="200 OK")


def _err_status(name: str) -> HealthStatus:
    return HealthStatus(service=name, ok=False, detail="Connection refused")


def test_header_contains_column_names():
    h = _header()
    for col in ("SERVICE", "TARGET", "STATUS", "DETAIL"):
        assert col in h


def test_row_up():
    r = _row("api", "localhost:8001", True, "200 OK")
    assert "UP" in r
    assert "api" in r
    assert "localhost:8001" in r


def test_row_down():
    r = _row("db", "localhost:5432", False, "Connection refused")
    assert "DOWN" in r


def test_run_upstream_health_prints_table(simple_config, capsys):
    with patch(
        "porthole.upstream_health.check_service",
        side_effect=lambda svc: _ok_status(svc.name),
    ):
        run_upstream_health(simple_config, watch=False)

    captured = capsys.readouterr().out
    assert "api" in captured
    assert "UP" in captured


def test_run_upstream_health_shows_down(simple_config, capsys):
    with patch(
        "porthole.upstream_health.check_service",
        side_effect=lambda svc: _err_status(svc.name),
    ):
        run_upstream_health(simple_config, watch=False)

    captured = capsys.readouterr().out
    assert "DOWN" in captured
