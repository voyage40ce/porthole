"""Tests for porthole.load_balancer."""
from __future__ import annotations

import threading
import pytest

from porthole.load_balancer import LoadBalancerConfig, LoadBalancerRegistry


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------

def test_config_rejects_empty_replicas():
    with pytest.raises(ValueError, match="at least one replica"):
        LoadBalancerConfig(replicas=[])


def test_config_rejects_bad_url():
    with pytest.raises(ValueError, match="http://"):
        LoadBalancerConfig(replicas=["localhost:8080"])


def test_config_rejects_unknown_strategy():
    with pytest.raises(ValueError, match="Unsupported strategy"):
        LoadBalancerConfig(replicas=["http://localhost:8080"], strategy="random")


def test_config_accepts_valid():
    cfg = LoadBalancerConfig(replicas=["http://a:1", "http://b:2"])
    assert cfg.strategy == "round_robin"


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

@pytest.fixture()
def registry():
    return LoadBalancerRegistry()


def test_next_replica_unknown_service_returns_none(registry):
    assert registry.next_replica("ghost") is None


def test_counts_unknown_service_returns_none(registry):
    assert registry.counts("ghost") is None


def test_round_robin_cycles(registry):
    cfg = LoadBalancerConfig(replicas=["http://a:1", "http://b:2", "http://c:3"])
    registry.register("svc", cfg)
    results = [registry.next_replica("svc") for _ in range(6)]
    assert results == [
        "http://a:1", "http://b:2", "http://c:3",
        "http://a:1", "http://b:2", "http://c:3",
    ]


def test_counts_track_distribution(registry):
    cfg = LoadBalancerConfig(replicas=["http://a:1", "http://b:2"])
    registry.register("svc", cfg)
    for _ in range(5):
        registry.next_replica("svc")
    counts = registry.counts("svc")
    assert counts["http://a:1"] == 3
    assert counts["http://b:2"] == 2


def test_all_services_lists_registered(registry):
    registry.register("alpha", LoadBalancerConfig(replicas=["http://x:1"]))
    registry.register("beta", LoadBalancerConfig(replicas=["http://y:2"]))
    assert set(registry.all_services()) == {"alpha", "beta"}


def test_thread_safety(registry):
    cfg = LoadBalancerConfig(replicas=["http://a:1", "http://b:2"])
    registry.register("svc", cfg)
    errors: list[Exception] = []

    def worker():
        try:
            for _ in range(100):
                registry.next_replica("svc")
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    total = sum(registry.counts("svc").values())
    assert total == 1000
