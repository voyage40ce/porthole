"""Simple in-memory response cache with TTL support for proxied requests."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, Optional, Tuple


@dataclass
class CacheConfig:
    ttl_seconds: float = 5.0
    max_entries: int = 256

    def __post_init__(self) -> None:
        if self.ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if self.max_entries < 1:
            raise ValueError("max_entries must be at least 1")


@dataclass
class _CacheEntry:
    status: int
    headers: list
    body: bytes
    expires_at: float


class ResponseCache:
    """Thread-safe TTL response cache keyed by (method, path)."""

    def __init__(self, config: CacheConfig) -> None:
        self._config = config
        self._store: Dict[Tuple[str, str], _CacheEntry] = {}
        self._lock = Lock()

    def get(self, method: str, path: str) -> Optional[_CacheEntry]:
        key = (method, path)
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if time.monotonic() > entry.expires_at:
                del self._store[key]
                return None
            return entry

    def put(self, method: str, path: str, status: int, headers: list, body: bytes) -> None:
        if method not in ("GET", "HEAD"):
            return
        key = (method, path)
        expires_at = time.monotonic() + self._config.ttl_seconds
        entry = _CacheEntry(status=status, headers=headers, body=body, expires_at=expires_at)
        with self._lock:
            if len(self._store) >= self._config.max_entries and key not in self._store:
                # evict oldest entry
                oldest = min(self._store, key=lambda k: self._store[k].expires_at)
                del self._store[oldest]
            self._store[key] = entry

    def invalidate(self, method: str, path: str) -> None:
        with self._lock:
            self._store.pop((method, path), None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._store)
