"""Tests for porthole.load_balancer_command."""
from __future__ import annotations

import io
import sys
import pytest

from porthole.load_balancer import LoadBalancerConfig, LoadBalancerRegistry
from porthole.load_balancer_command import _header, _row, run_load_balancer


@pytest.fixture()
def registry_with_data():
    reg = LoadBalancerRegistry()
    reg.register(
        "api",
        LoadBalancerConfig(replicas=["http://api-1:8000", "http://api-2:8000"]),
    )
    # drive 3 requests so api-1 gets 2, api-2 gets 1
    reg.next_replica("api")
    reg.next_replica("api")
    reg.next_replica("api")
    return reg


def test_header_contains_columns():
    h = _header()
    assert "SERVICE" in h
    assert "REPLICA" in h
    assert "REQUESTS" in h


def test_row_formats_values():
    r = _row("my-svc", "http://host:9000", 42)
    assert "my-svc" in r
    assert "http://host:9000" in r
    assert "42" in r


def test_run_load_balancer_no_services_prints_message(capsys):
    reg = LoadBalancerRegistry()
    run_load_balancer(reg)
    out = capsys.readouterr().out
    assert "No load-balanced services" in out


def test_run_load_balancer_shows_service(capsys, registry_with_data):
    run_load_balancer(registry_with_data)
    out = capsys.readouterr().out
    assert "api" in out
    assert "http://api-1:8000" in out
    assert "http://api-2:8000" in out


def test_run_load_balancer_filter(capsys, registry_with_data):
    registry_with_data.register(
        "other",
        LoadBalancerConfig(replicas=["http://other:9999"]),
    )
    run_load_balancer(registry_with_data, service_filter="api")
    out = capsys.readouterr().out
    assert "api" in out
    assert "other" not in out


def test_run_load_balancer_counts_correct(capsys, registry_with_data):
    run_load_balancer(registry_with_data)
    out = capsys.readouterr().out
    lines = [l for l in out.splitlines() if "api-1" in l or "api-2" in l]
    counts = {}
    for line in lines:
        parts = line.split()
        counts[parts[1]] = int(parts[-1])
    assert counts["http://api-1:8000"] == 2
    assert counts["http://api-2:8000"] == 1
