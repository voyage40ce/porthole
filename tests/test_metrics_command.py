"""Tests for porthole.metrics_command."""

import pytest

from porthole.metrics import MetricsCollector
from porthole.metrics_command import run_metrics, _header, _row


@pytest.fixture(autouse=True)
def fresh_collector(monkeypatch):
    """Give every test its own isolated collector."""
    col = MetricsCollector()
    monkeypatch.setattr("porthole.metrics_command.get_collector", lambda: col)
    monkeypatch.setattr("porthole.metrics.get_collector", lambda: col)
    return col


def test_header_contains_columns():
    hdr = _header()
    for label in ("Service", "Requests", "Errors", "Err %", "Avg ms"):
        assert label in hdr


def test_row_formats_values():
    from porthole.metrics import ServiceMetrics
    m = ServiceMetrics(total_requests=10, error_requests=2, total_duration_ms=100.0)
    line = _row("my-service", m)
    assert "my-service" in line
    assert "10" in line
    assert "2" in line
    assert "20.0" in line  # error_rate 20 %
    assert "10.0" in line  # avg ms


def test_run_metrics_no_data_prints_message(capsys, fresh_collector):
    run_metrics()
    out = capsys.readouterr().out
    assert "No metrics recorded" in out


def test_run_metrics_shows_service(capsys, fresh_collector):
    fresh_collector.record("api", 200, 42.0)
    run_metrics()
    out = capsys.readouterr().out
    assert "api" in out
    assert "1" in out


def test_run_metrics_reset_flag(capsys, fresh_collector):
    fresh_collector.record("api", 200, 10.0)
    run_metrics(reset_after=True)
    capsys.readouterr()
    # After reset, second call should report no data
    run_metrics()
    out = capsys.readouterr().out
    assert "No metrics recorded" in out


def test_run_metrics_sorted_output(capsys, fresh_collector):
    fresh_collector.record("zebra", 200, 1.0)
    fresh_collector.record("alpha", 200, 1.0)
    run_metrics()
    out = capsys.readouterr().out
    assert out.index("alpha") < out.index("zebra")
