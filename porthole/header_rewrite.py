"""Header rewrite middleware — inject, remove, or override HTTP headers per service."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class HeaderRewriteConfig:
    """Per-service header rewrite rules."""

    add: Dict[str, str] = field(default_factory=dict)
    remove: List[str] = field(default_factory=list)
    override: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Normalise header names to lowercase for case-insensitive matching
        self.add = {k.lower(): v for k, v in self.add.items()}
        self.override = {k.lower(): v for k, v in self.override.items()}
        self.remove = [h.lower() for h in self.remove]


class HeaderRewriteRegistry:
    """Holds HeaderRewriteConfig instances keyed by service name."""

    def __init__(self) -> None:
        self._rules: Dict[str, HeaderRewriteConfig] = {}

    def register(self, service: str, cfg: HeaderRewriteConfig) -> None:
        self._rules[service] = cfg

    def get(self, service: str) -> Optional[HeaderRewriteConfig]:
        return self._rules.get(service)


def apply_request_rewrites(
    headers: Dict[str, str],
    cfg: HeaderRewriteConfig,
) -> Dict[str, str]:
    """Return a *new* headers dict with rewrite rules applied."""
    result = {k.lower(): v for k, v in headers.items()}

    for name in cfg.remove:
        result.pop(name, None)

    for name, value in cfg.override.items():
        result[name] = value

    for name, value in cfg.add.items():
        if name not in result:
            result[name] = value

    return result


def header_rewrite_proxy(service: str, registry: HeaderRewriteRegistry, next_handler):
    """Middleware factory that rewrites headers before forwarding."""

    def handler(proxy_self, method: str, url: str, headers: Dict[str, str], body: bytes):
        cfg = registry.get(service)
        effective_headers = apply_request_rewrites(headers, cfg) if cfg else dict(headers)
        return next_handler(proxy_self, method, url, effective_headers, body)

    return handler
