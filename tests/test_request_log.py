"""Tests for porthole.request_log and porthole.request_log_command."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from porthole.request_log import RequestLog, RequestLogEntry
from porthole.request_log_command import _header, _row, run_request_log


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_TS = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def log() -> RequestLog:
    return RequestLog(max_entries=10)


def _add(log: RequestLog, service: str = "svc-a", status: int = 200, path: str = "/") -> None:
    log.record(
        service=service,
        method="GET",
        path=path,
        status_code=status,
        duration_ms=12.5,
        timestamp=_TS,
    )


# ---------------------------------------------------------------------------
# RequestLog unit tests
# ---------------------------------------------------------------------------


def test_config_rejects_zero_max_entries() -> None:
    with pytest.raises(ValueError, match="max_entries"):
        RequestLog(max_entries=0)


def test_empty_log_returns_empty_list(log: RequestLog) -> None:
    assert log.recent() == []


def test_record_appends_entry(log: RequestLog) -> None:
    _add(log)
    entries = log.recent()
    assert len(entries) == 1
    assert entries[0].service == "svc-a"
    assert entries[0].status_code == 200


def test_recent_n_limits_results(log: RequestLog) -> None:
    for i in range(5):
        _add(log, path=f"/{i}")
    assert len(log.recent(3)) == 3


def test_ring_buffer_evicts_oldest(log: RequestLog) -> None:
    """max_entries=10, add 12 — oldest two are gone."""
    for i in range(12):
        _add(log, path=f"/{i}")
    entries = log.recent()
    assert len(entries) == 10
    assert entries[0].path == "/2"


def test_clear_empties_log(log: RequestLog) -> None:
    _add(log)
    log.clear()
    assert log.recent() == []


def test_max_entries_property(log: RequestLog) -> None:
    assert log.max_entries == 10


# ---------------------------------------------------------------------------
# request_log_command tests
# ---------------------------------------------------------------------------


def test_header_contains_columns() -> None:
    h = _header()
    for col in ("TIMESTAMP", "SERVICE", "METHOD", "PATH", "STATUS", "DURATION_MS"):
        assert col in h


def test_row_formats_entry() -> None:
    entry = RequestLogEntry(
        timestamp=_TS,
        service="api-gateway",
        method="POST",
        path="/v1/users",
        status_code=201,
        duration_ms=33.7,
    )
    r = _row(entry)
    assert "api-gateway" in r
    assert "POST" in r
    assert "/v1/users" in r
    assert "201" in r
    assert "33.7" in r


def test_run_request_log_no_entries_prints_message(capsys: pytest.CaptureFixture) -> None:
    log = RequestLog()
    run_request_log(log=log)
    out = capsys.readouterr().out
    assert "No request log entries" in out


def test_run_request_log_shows_entries(capsys: pytest.CaptureFixture) -> None:
    log = RequestLog()
    _add(log, service="my-svc", status=200)
    run_request_log(log=log)
    out = capsys.readouterr().out
    assert "my-svc" in out


def test_run_request_log_service_filter(capsys: pytest.CaptureFixture) -> None:
    log = RequestLog()
    _add(log, service="svc-a")
    _add(log, service="svc-b")
    run_request_log(service_filter="svc-a", log=log)
    out = capsys.readouterr().out
    assert "svc-a" in out
    assert "svc-b" not in out


def test_run_request_log_status_filter(capsys: pytest.CaptureFixture) -> None:
    log = RequestLog()
    _add(log, status=200)
    _add(log, status=500)
    run_request_log(status_filter=500, log=log)
    out = capsys.readouterr().out
    assert "500" in out
    # 200 entry should not appear
    lines = [l for l in out.splitlines() if "200" in l and "STATUS" not in l]
    assert lines == []
