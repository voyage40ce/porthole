"""Shadow traffic mirroring: duplicate requests to a shadow upstream for testing."""
from __future__ import annotations

import threading
import urllib.request
from dataclasses import dataclass, field
from typing import Dict, Optional

from porthole.logger import get_logger

log = get_logger("porthole.shadow")


@dataclass
class ShadowConfig:
    """Per-service shadow mirroring configuration."""

    target: str  # e.g. "http://shadow-host:9000"
    sample_rate: float = 1.0  # 0.0 – 1.0
    timeout_seconds: float = 2.0

    def __post_init__(self) -> None:
        if not self.target.startswith(("http://", "https://")):
            raise ValueError(f"shadow target must be an HTTP URL, got: {self.target!r}")
        if not (0.0 < self.sample_rate <= 1.0):
            raise ValueError("sample_rate must be in (0, 1]")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


class ShadowRegistry:
    """Holds shadow configs keyed by service name."""

    def __init__(self) -> None:
        self._configs: Dict[str, ShadowConfig] = {}
        self._counters: Dict[str, int] = {}

    def register(self, service: str, cfg: ShadowConfig) -> None:
        self._configs[service] = cfg
        self._counters[service] = 0

    def get(self, service: str) -> Optional[ShadowConfig]:
        return self._configs.get(service)

    def all_services(self) -> Dict[str, ShadowConfig]:
        return dict(self._configs)

    def mirror_count(self, service: str) -> int:
        return self._counters.get(service, 0)

    def _increment(self, service: str) -> None:
        self._counters[service] = self._counters.get(service, 0) + 1


def _fire_and_forget(
    service: str,
    cfg: ShadowConfig,
    method: str,
    path: str,
    headers: Dict[str, str],
    body: bytes,
    registry: ShadowRegistry,
) -> None:
    url = cfg.target.rstrip("/") + path
    req = urllib.request.Request(url, data=body or None, method=method)
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=cfg.timeout_seconds):
            pass
        registry._increment(service)
    except Exception as exc:  # noqa: BLE001
        log.debug("shadow mirror failed for %s -> %s: %s", service, url, exc)


def mirror_request(
    service: str,
    cfg: ShadowConfig,
    method: str,
    path: str,
    headers: Dict[str, str],
    body: bytes,
    registry: ShadowRegistry,
) -> None:
    """Send a fire-and-forget copy of the request to the shadow target."""
    import random

    if random.random() > cfg.sample_rate:
        return
    t = threading.Thread(
        target=_fire_and_forget,
        args=(service, cfg, method, path, headers, body, registry),
        daemon=True,
    )
    t.start()
