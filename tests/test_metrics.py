"""Tests for porthole.metrics."""

import threading
import pytest

from porthole.metrics import MetricsCollector, ServiceMetrics


@pytest.fixture()
def col() -> MetricsCollector:
    return MetricsCollector()


def test_record_increments_total(col):
    col.record("svc", 200, 12.5)
    snap = col.snapshot()
    assert snap["svc"].total_requests == 1


def test_record_tracks_status_counts(col):
    col.record("svc", 200, 5.0)
    col.record("svc", 200, 8.0)
    col.record("svc", 404, 3.0)
    snap = col.snapshot()["svc"]
    assert snap.status_counts[200] == 2
    assert snap.status_counts[404] == 1


def test_error_counted_for_5xx(col):
    col.record("svc", 500, 1.0)
    col.record("svc", 503, 1.0)
    col.record("svc", 200, 1.0)
    snap = col.snapshot()["svc"]
    assert snap.error_requests == 2


def test_avg_duration(col):
    col.record("svc", 200, 10.0)
    col.record("svc", 200, 30.0)
    snap = col.snapshot()["svc"]
    assert snap.avg_duration_ms == pytest.approx(20.0)


def test_error_rate(col):
    col.record("svc", 200, 1.0)
    col.record("svc", 500, 1.0)
    snap = col.snapshot()["svc"]
    assert snap.error_rate == pytest.approx(0.5)


def test_avg_duration_zero_requests():
    m = ServiceMetrics()
    assert m.avg_duration_ms == 0.0


def test_error_rate_zero_requests():
    m = ServiceMetrics()
    assert m.error_rate == 0.0


def test_reset_clears_data(col):
    col.record("svc", 200, 1.0)
    col.reset()
    assert col.snapshot() == {}


def test_snapshot_is_independent_copy(col):
    col.record("svc", 200, 5.0)
    snap1 = col.snapshot()
    col.record("svc", 200, 5.0)
    snap2 = col.snapshot()
    assert snap1["svc"].total_requests == 1
    assert snap2["svc"].total_requests == 2


def test_thread_safety(col):
    def worker():
        for _ in range(100):
            col.record("svc", 200, 1.0)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    snap = col.snapshot()
    assert snap["svc"].total_requests == 1000
