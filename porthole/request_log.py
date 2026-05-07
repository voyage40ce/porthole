"""Persistent request log: records recent proxy requests to an in-memory
ring buffer and exposes a command to inspect them."""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Deque, List, Optional

_DEFAULT_MAX_ENTRIES = 200


@dataclass
class RequestLogEntry:
    timestamp: datetime
    service: str
    method: str
    path: str
    status_code: int
    duration_ms: float
    client_ip: str = ""

    def __str__(self) -> str:  # pragma: no cover
        ts = self.timestamp.strftime("%H:%M:%S")
        return (
            f"[{ts}] {self.service:20s} {self.method:6s} {self.path:40s}"
            f" -> {self.status_code}  {self.duration_ms:.1f}ms"
        )


class RequestLog:
    """Thread-safe ring buffer of recent proxy requests."""

    def __init__(self, max_entries: int = _DEFAULT_MAX_ENTRIES) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be >= 1")
        self._max_entries = max_entries
        self._buf: Deque[RequestLogEntry] = deque(maxlen=max_entries)
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def record(
        self,
        *,
        service: str,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        client_ip: str = "",
        timestamp: Optional[datetime] = None,
    ) -> None:
        entry = RequestLogEntry(
            timestamp=timestamp or datetime.now(timezone.utc),
            service=service,
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            client_ip=client_ip,
        )
        with self._lock:
            self._buf.append(entry)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def recent(self, n: Optional[int] = None) -> List[RequestLogEntry]:
        """Return the *n* most recent entries (all entries when *n* is None)."""
        with self._lock:
            entries = list(self._buf)
        if n is None:
            return entries
        return entries[-n:]

    def clear(self) -> None:
        with self._lock:
            self._buf.clear()

    @property
    def max_entries(self) -> int:
        return self._max_entries


# Module-level singleton used by middleware and CLI command.
_global_log: RequestLog = RequestLog()


def get_request_log() -> RequestLog:
    return _global_log
