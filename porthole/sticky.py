"""Sticky session support: route repeat clients to the same upstream."""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class StickyConfig:
    ttl_seconds: float = 300.0
    header: str = "X-Porthole-Session"

    def __post_init__(self) -> None:
        if self.ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if not self.header.strip():
            raise ValueError("header name must not be empty")


@dataclass
class _StickyEntry:
    upstream: str
    expires_at: float


class StickyRegistry:
    """Maps session tokens to upstream targets with TTL-based expiry."""

    def __init__(self, config: StickyConfig) -> None:
        self._config = config
        self._store: Dict[str, _StickyEntry] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, token: str) -> Optional[str]:
        """Return the pinned upstream for *token*, or None if expired/missing."""
        entry = self._store.get(token)
        if entry is None:
            return None
        if time.monotonic() > entry.expires_at:
            del self._store[token]
            return None
        return entry.upstream

    def pin(self, token: str, upstream: str) -> None:
        """Pin *token* to *upstream*, resetting the TTL."""
        self._store[token] = _StickyEntry(
            upstream=upstream,
            expires_at=time.monotonic() + self._config.ttl_seconds,
        )

    def pick_and_pin(self, token: str, upstreams: List[str]) -> str:
        """Deterministically pick an upstream for *token* and persist the mapping."""
        if not upstreams:
            raise ValueError("upstreams list must not be empty")
        existing = self.get(token)
        if existing and existing in upstreams:
            return existing
        # Consistent hash so the same token always maps to the same index
        # when the upstream list is stable.
        index = int(hashlib.md5(token.encode()).hexdigest(), 16) % len(upstreams)
        chosen = upstreams[index]
        self.pin(token, chosen)
        return chosen

    def purge_expired(self) -> int:
        """Remove all expired entries and return the number removed."""
        now = time.monotonic()
        expired = [k for k, v in self._store.items() if now > v.expires_at]
        for k in expired:
            del self._store[k]
        return len(expired)

    def stats(self) -> Dict[str, object]:
        """Return a snapshot of current registry statistics."""
        now = time.monotonic()
        active = sum(1 for v in self._store.values() if now <= v.expires_at)
        return {"total": len(self._store), "active": active}
