"""Simple token-based authentication middleware for porthole."""

from __future__ import annotations

import dataclasses
import hashlib
import hmac
from typing import Callable, Dict, Optional

from porthole.logger import get_logger

log = get_logger(__name__)


@dataclasses.dataclass
class AuthConfig:
    """Authentication configuration for a service."""

    tokens: list[str]  # allowed bearer tokens (plain text; stored as digests)
    header: str = "Authorization"  # header to inspect
    strip_header: bool = True  # remove auth header before forwarding

    def __post_init__(self) -> None:
        if not self.tokens:
            raise ValueError("AuthConfig.tokens must contain at least one token")
        self.header = self.header.strip()
        if not self.header:
            raise ValueError("AuthConfig.header must not be empty")
        # Pre-compute digests so plain-text tokens aren't kept in memory longer
        # than necessary.  We use SHA-256 via hmac to avoid timing attacks.
        self._digests: list[bytes] = [
            hashlib.sha256(t.encode()).digest() for t in self.tokens
        ]

    def is_valid(self, token: str) -> bool:
        """Return True if *token* matches any registered token."""
        candidate = hashlib.sha256(token.encode()).digest()
        return any(hmac.compare_digest(candidate, d) for d in self._digests)


class AuthRegistry:
    """Maps service names to their AuthConfig."""

    def __init__(self) -> None:
        self._configs: Dict[str, AuthConfig] = {}

    def register(self, service: str, config: AuthConfig) -> None:
        self._configs[service] = config

    def get(self, service: str) -> Optional[AuthConfig]:
        return self._configs.get(service)

    def services(self) -> list[str]:
        return list(self._configs.keys())


def auth_proxy(
    next_handler: Callable,
    registry: AuthRegistry,
    service_name: str,
) -> Callable:
    """Middleware that enforces token auth before delegating to *next_handler*."""

    def handler(request_handler) -> None:  # type: ignore[type-arg]
        cfg = registry.get(service_name)
        if cfg is None:
            # No auth configured for this service — pass through.
            return next_handler(request_handler)

        raw = request_handler.headers.get(cfg.header, "")
        # Support both "Bearer <token>" and bare token.
        token = raw.removeprefix("Bearer ").strip()

        if not token or not cfg.is_valid(token):
            log.warning("auth: rejected request for service '%s'", service_name)
            request_handler.send_response(401)
            request_handler.send_header("Content-Type", "text/plain")
            request_handler.send_header("WWW-Authenticate", 'Bearer realm="porthole"')
            request_handler.end_headers()
            request_handler.wfile.write(b"Unauthorized")
            return

        if cfg.strip_header:
            # Remove the header so upstream services don't see the internal token.
            del request_handler.headers[cfg.header]

        return next_handler(request_handler)

    return handler
