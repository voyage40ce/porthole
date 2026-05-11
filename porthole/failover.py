"""Failover support: redirect traffic to a backup URL when the primary is unavailable."""
from __future__ import annotations

import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class FailoverConfig:
    backups: List[str]
    timeout_seconds: float = 2.0
    retry_on_status: List[int] = field(default_factory=lambda: [502, 503, 504])

    def __post_init__(self) -> None:
        if not self.backups:
            raise ValueError("failover.backups must contain at least one URL")
        for url in self.backups:
            if not url.startswith(("http://", "https://")):
                raise ValueError(f"failover backup URL must start with http:// or https://: {url!r}")
        if self.timeout_seconds <= 0:
            raise ValueError("failover.timeout_seconds must be positive")


class FailoverRegistry:
    """Holds per-service failover configuration."""

    def __init__(self) -> None:
        self._configs: Dict[str, FailoverConfig] = {}
        self._active_backup: Dict[str, Optional[str]] = {}

    def register(self, service: str, cfg: FailoverConfig) -> None:
        self._configs[service] = cfg
        self._active_backup[service] = None

    def get(self, service: str) -> Optional[FailoverConfig]:
        return self._configs.get(service)

    def set_active_backup(self, service: str, url: Optional[str]) -> None:
        self._active_backup[service] = url

    def active_backup(self, service: str) -> Optional[str]:
        return self._active_backup.get(service)

    def all_services(self) -> List[str]:
        return list(self._configs.keys())

    def probe_primary(self, service: str, primary_url: str) -> bool:
        """Return True if the primary responds successfully."""
        cfg = self._configs.get(service)
        timeout = cfg.timeout_seconds if cfg else 2.0
        try:
            with urllib.request.urlopen(primary_url, timeout=timeout) as resp:
                return resp.status < 500
        except Exception:
            return False

    def resolve_url(self, service: str, primary_url: str) -> str:
        """Return the URL to use, falling back through backups if needed."""
        cfg = self._configs.get(service)
        if cfg is None:
            return primary_url
        if self.probe_primary(service, primary_url):
            self._active_backup[service] = None
            return primary_url
        for backup in cfg.backups:
            try:
                with urllib.request.urlopen(backup, timeout=cfg.timeout_seconds) as resp:
                    if resp.status < 500:
                        self._active_backup[service] = backup
                        return backup
            except Exception:
                continue
        # All backups failed; return primary and let the request fail naturally
        self._active_backup[service] = None
        return primary_url
