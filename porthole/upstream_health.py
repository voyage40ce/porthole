"""Periodic upstream health monitoring with automatic circuit-breaker integration."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

from porthole.config import PortholeConfig
from porthole.healthcheck import HealthStatus, check_service
from porthole.logger import get_logger

log = get_logger(__name__)


@dataclass
class UpstreamHealthMonitor:
    """Polls every configured service and maintains the latest HealthStatus."""

    config: PortholeConfig
    interval_seconds: float = 10.0
    _statuses: Dict[str, HealthStatus] = field(default_factory=dict, init=False)
    _thread: Optional[threading.Thread] = field(default=None, init=False)
    _stop_event: threading.Event = field(default_factory=threading.Event, init=False)
    _callbacks: list[Callable[[str, HealthStatus], None]] = field(
        default_factory=list, init=False
    )

    def register_callback(
        self, cb: Callable[[str, HealthStatus], None]
    ) -> None:
        """Register a function called whenever a service status changes."""
        self._callbacks.append(cb)

    def latest(self, service_name: str) -> Optional[HealthStatus]:
        """Return the most recent HealthStatus for *service_name*, or None."""
        return self._statuses.get(service_name)

    def all_statuses(self) -> Dict[str, HealthStatus]:
        return dict(self._statuses)

    def start(self) -> None:
        """Start background polling thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._poll_loop, daemon=True, name="upstream-health-monitor"
        )
        self._thread.start()
        log.info("upstream health monitor started (interval=%.1fs)", self.interval_seconds)

    def stop(self) -> None:
        """Signal the polling thread to stop and wait for it."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self.interval_seconds + 2)
        log.info("upstream health monitor stopped")

    def _poll_loop(self) -> None:
        while not self._stop_event.is_set():
            self._run_checks()
            self._stop_event.wait(timeout=self.interval_seconds)

    def _run_checks(self) -> None:
        for svc in self.config.services:
            status = check_service(svc)
            previous = self._statuses.get(svc.name)
            self._statuses[svc.name] = status
            if previous is None or previous.ok != status.ok:
                log.info(
                    "service %s is now %s",
                    svc.name,
                    "UP" if status.ok else "DOWN",
                )
                for cb in self._callbacks:
                    try:
                        cb(svc.name, status)
                    except Exception:  # noqa: BLE001
                        log.exception("upstream health callback raised")
