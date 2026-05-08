"""Middleware that transparently mirrors matched requests to a shadow upstream."""
from __future__ import annotations

from typing import Callable

from porthole.shadow import ShadowRegistry, mirror_request


def shadow_proxy(
    service: str,
    registry: ShadowRegistry,
    next_handler: Callable,
) -> Callable:
    """Wrap *next_handler* so that every request is also mirrored to the shadow
    target (if one is registered for *service*).  The real response from
    *next_handler* is always returned to the caller unchanged.
    """

    def handler(request_handler) -> int:  # type: ignore[return]
        cfg = registry.get(service)
        if cfg is not None:
            # Capture request data before the real handler consumes it.
            try:
                length = int(request_handler.headers.get("Content-Length", 0))
            except (TypeError, ValueError):
                length = 0
            body = request_handler.rfile.read(length) if length else b""

            headers = {
                k: v
                for k, v in request_handler.headers.items()
                if k.lower() not in ("host", "content-length")
            }
            mirror_request(
                service,
                cfg,
                request_handler.command,
                request_handler.path,
                headers,
                body,
                registry,
            )

            # Re-inject the body so the real handler can read it.
            import io

            request_handler.rfile = io.BytesIO(body)
            if length:
                request_handler.headers["Content-Length"] = str(len(body))

        return next_handler(request_handler)

    return handler
