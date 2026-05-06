"""CORS (Cross-Origin Resource Sharing) middleware for porthole proxy."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from porthole.logger import get_logger

logger = get_logger("porthole.cors")


@dataclass
class CORSConfig:
    """Configuration for CORS headers injected on proxied responses."""

    allow_origins: List[str] = field(default_factory=lambda: ["*"])
    allow_methods: List[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"])
    allow_headers: List[str] = field(default_factory=lambda: ["Content-Type", "Authorization"])
    allow_credentials: bool = False
    max_age: int = 600

    def __post_init__(self) -> None:
        if not self.allow_origins:
            raise ValueError("allow_origins must contain at least one entry")
        if self.max_age < 0:
            raise ValueError("max_age must be non-negative")
        if self.allow_credentials and "*" in self.allow_origins:
            raise ValueError("allow_credentials=True is incompatible with wildcard allow_origins")

    def origin_allowed(self, origin: Optional[str]) -> Optional[str]:
        """Return the value to use for Access-Control-Allow-Origin, or None."""
        if not origin:
            return None
        if "*" in self.allow_origins:
            return "*"
        if origin in self.allow_origins:
            return origin
        return None


def cors_proxy(
    next_handler: Callable,
    config: CORSConfig,
) -> Callable:
    """Wrap *next_handler* so that CORS headers are added to every response.

    Preflight OPTIONS requests are answered immediately with 204 No Content
    without forwarding to the upstream service.
    """

    def handler(proxy_self) -> None:  # proxy_self is a BaseHTTPRequestHandler
        origin = proxy_self.headers.get("Origin")
        allowed_origin = config.origin_allowed(origin)

        # Handle preflight
        if proxy_self.command == "OPTIONS":
            proxy_self.send_response(204)
            if allowed_origin:
                proxy_self.send_header("Access-Control-Allow-Origin", allowed_origin)
                proxy_self.send_header("Access-Control-Allow-Methods", ", ".join(config.allow_methods))
                proxy_self.send_header("Access-Control-Allow-Headers", ", ".join(config.allow_headers))
                if config.allow_credentials:
                    proxy_self.send_header("Access-Control-Allow-Credentials", "true")
                proxy_self.send_header("Access-Control-Max-Age", str(config.max_age))
            proxy_self.end_headers()
            logger.debug("Preflight OPTIONS answered for origin=%s", origin)
            return

        # Forward to next handler; CORS headers are injected after
        next_handler(proxy_self)

        if allowed_origin:
            proxy_self.send_header("Access-Control-Allow-Origin", allowed_origin)
            if config.allow_credentials:
                proxy_self.send_header("Access-Control-Allow-Credentials", "true")

    return handler
