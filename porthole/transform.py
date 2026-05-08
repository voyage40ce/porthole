"""Request/response body transform rules for proxied services."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TransformConfig:
    """Transformation rules for a single service."""

    service: str
    # Each entry: {"find": "<regex>", "replace": "<str>"} applied to response body
    response_body_rewrites: List[Dict[str, str]] = field(default_factory=list)
    # Headers to inject into every proxied request
    inject_request_headers: Dict[str, str] = field(default_factory=dict)
    # Headers to strip from the upstream response before forwarding
    strip_response_headers: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for rule in self.response_body_rewrites:
            if "find" not in rule or "replace" not in rule:
                raise ValueError(
                    "Each response_body_rewrite must have 'find' and 'replace' keys."
                )
            try:
                re.compile(rule["find"])
            except re.error as exc:
                raise ValueError(f"Invalid regex '{rule['find']}': {exc}") from exc
        self.strip_response_headers = [
            h.lower() for h in self.strip_response_headers
        ]


class TransformRegistry:
    """Holds TransformConfig objects keyed by service name."""

    def __init__(self) -> None:
        self._configs: Dict[str, TransformConfig] = {}

    def register(self, cfg: TransformConfig) -> None:
        self._configs[cfg.service] = cfg

    def get(self, service: str) -> Optional[TransformConfig]:
        return self._configs.get(service)

    def apply_request_headers(
        self, service: str, headers: Dict[str, str]
    ) -> Dict[str, str]:
        """Return a copy of *headers* with injected request headers merged in."""
        cfg = self.get(service)
        if cfg is None:
            return dict(headers)
        merged = dict(headers)
        merged.update(cfg.inject_request_headers)
        return merged

    def apply_response_body(
        self, service: str, body: bytes, content_type: str = ""
    ) -> bytes:
        """Apply regex rewrites to *body* when content-type is text/json-ish."""
        cfg = self.get(service)
        if cfg is None or not cfg.response_body_rewrites:
            return body
        if not any(
            ct in content_type.lower()
            for ct in ("text/", "application/json", "application/xml")
        ):
            return body
        text = body.decode("utf-8", errors="replace")
        for rule in cfg.response_body_rewrites:
            text = re.sub(rule["find"], rule["replace"], text)
        return text.encode("utf-8")

    def filter_response_headers(
        self, service: str, headers: Dict[str, str]
    ) -> Dict[str, str]:
        """Return *headers* with stripped response headers removed."""
        cfg = self.get(service)
        if cfg is None:
            return dict(headers)
        return {
            k: v
            for k, v in headers.items()
            if k.lower() not in cfg.strip_response_headers
        }
