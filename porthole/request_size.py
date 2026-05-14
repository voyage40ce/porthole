"""Request and response size limiting middleware for porthole."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from porthole.logger import get_logger

log = get_logger(__name__)

_DEFAULT_MAX_REQUEST_BYTES = 1 * 1024 * 1024   # 1 MiB
_DEFAULT_MAX_RESPONSE_BYTES = 10 * 1024 * 1024  # 10 MiB


@dataclass
class RequestSizeConfig:
    """Per-service size limits."""

    max_request_bytes: int = _DEFAULT_MAX_REQUEST_BYTES
    max_response_bytes: int = _DEFAULT_MAX_RESPONSE_BYTES

    def __post_init__(self) -> None:
        if self.max_request_bytes <= 0:
            raise ValueError("max_request_bytes must be positive")
        if self.max_response_bytes <= 0:
            raise ValueError("max_response_bytes must be positive")


class RequestSizeRegistry:
    """Holds per-service RequestSizeConfig instances."""

    def __init__(self) -> None:
        self._configs: dict[str, RequestSizeConfig] = {}

    def register(self, service: str, cfg: RequestSizeConfig) -> None:
        self._configs[service] = cfg

    def get(self, service: str) -> RequestSizeConfig | None:
        return self._configs.get(service)

    def all_services(self) -> list[str]:
        return list(self._configs.keys())


def size_limited_proxy(
    registry: RequestSizeRegistry,
    service: str,
    next_handler: Callable,
) -> Callable:
    """Wrap *next_handler* with request/response size enforcement.

    Returns a handler callable compatible with porthole's middleware chain.
    """
    cfg = registry.get(service)

    def handler(request_handler) -> None:  # type: ignore[type-arg]
        if cfg is not None:
            content_length = request_handler.headers.get("Content-Length")
            if content_length is not None:
                try:
                    cl = int(content_length)
                except ValueError:
                    cl = 0
                if cl > cfg.max_request_bytes:
                    log.warning(
                        "request body too large",
                        extra={
                            "service": service,
                            "content_length": cl,
                            "limit": cfg.max_request_bytes,
                        },
                    )
                    request_handler.send_response(413)
                    request_handler.send_header("Content-Length", "0")
                    request_handler.end_headers()
                    return

        status_code = next_handler(request_handler)
        return status_code

    return handler
