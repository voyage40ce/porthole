"""Round-robin load balancer for distributing requests across upstream replicas."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class LoadBalancerConfig:
    replicas: List[str]
    strategy: str = "round_robin"  # only strategy supported for now

    def __post_init__(self) -> None:
        if not self.replicas:
            raise ValueError("LoadBalancerConfig requires at least one replica")
        for r in self.replicas:
            if not r.startswith(("http://", "https://")):
                raise ValueError(f"Replica URL must start with http:// or https://: {r!r}")
        if self.strategy != "round_robin":
            raise ValueError(f"Unsupported strategy: {self.strategy!r}")


class _ServiceBalancer:
    """Thread-safe round-robin cursor for a single service."""

    def __init__(self, config: LoadBalancerConfig) -> None:
        self._replicas = list(config.replicas)
        self._index = 0
        self._lock = threading.Lock()
        self._request_counts: dict[str, int] = {r: 0 for r in self._replicas}

    def next_replica(self) -> str:
        with self._lock:
            replica = self._replicas[self._index % len(self._replicas)]
            self._index += 1
            self._request_counts[replica] += 1
            return replica

    def counts(self) -> dict[str, int]:
        with self._lock:
            return dict(self._request_counts)


class LoadBalancerRegistry:
    """Registry mapping service names to their balancers."""

    def __init__(self) -> None:
        self._balancers: dict[str, _ServiceBalancer] = {}
        self._lock = threading.Lock()

    def register(self, service: str, config: LoadBalancerConfig) -> None:
        with self._lock:
            self._balancers[service] = _ServiceBalancer(config)

    def next_replica(self, service: str) -> Optional[str]:
        with self._lock:
            balancer = self._balancers.get(service)
        if balancer is None:
            return None
        return balancer.next_replica()

    def counts(self, service: str) -> Optional[dict[str, int]]:
        with self._lock:
            balancer = self._balancers.get(service)
        if balancer is None:
            return None
        return balancer.counts()

    def all_services(self) -> List[str]:
        with self._lock:
            return list(self._balancers.keys())
