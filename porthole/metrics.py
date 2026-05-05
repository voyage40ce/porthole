"""Simple in-memory request metrics collector for porthole."""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ServiceMetrics:
    total_requests: int = 0
    error_requests: int = 0
    total_duration_ms: float = 0.0
    status_counts: Dict[int, int] = field(default_factory=dict)

    @property
    def avg_duration_ms(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_duration_ms / self.total_requests

    @property
    def error_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.error_requests / self.total_requests


class MetricsCollector:
    """Thread-safe collector for per-service request metrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: Dict[str, ServiceMetrics] = defaultdict(ServiceMetrics)

    def record(self, service_name: str, status_code: int, duration_ms: float) -> None:
        """Record a completed request for *service_name*."""
        with self._lock:
            m = self._data[service_name]
            m.total_requests += 1
            m.total_duration_ms += duration_ms
            m.status_counts[status_code] = m.status_counts.get(status_code, 0) + 1
            if status_code >= 500:
                m.error_requests += 1

    def snapshot(self) -> Dict[str, ServiceMetrics]:
        """Return a shallow copy of current metrics keyed by service name."""
        with self._lock:
            return {name: ServiceMetrics(
                total_requests=m.total_requests,
                error_requests=m.error_requests,
                total_duration_ms=m.total_duration_ms,
                status_counts=dict(m.status_counts),
            ) for name, m in self._data.items()}

    def reset(self) -> None:
        """Clear all collected metrics."""
        with self._lock:
            self._data.clear()


# Module-level singleton used by the rest of porthole.
_collector = MetricsCollector()


def get_collector() -> MetricsCollector:
    return _collector
