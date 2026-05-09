"""Middleware that short-circuits the proxy and returns a canned response
when the target service has a MockResponseConfig registered."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler
from typing import Callable

from porthole.mock_response import MockRegistry


def mock_proxy(
    registry: MockRegistry,
    next_handler: Callable[[BaseHTTPRequestHandler], int],
) -> Callable[[BaseHTTPRequestHandler], int]:
    """Return a handler that serves a mock response when one is configured.

    If no mock is registered for the service the request falls through to
    *next_handler* unchanged.
    """

    def handler(req: BaseHTTPRequestHandler) -> int:
        # Resolve the service name from the Host header (strip port if present)
        host_header: str = req.headers.get("Host", "")
        service = host_header.split(":")[0]

        cfg = registry.get(service)
        if cfg is None:
            return next_handler(req)

        body_bytes = cfg.body.encode()
        req.send_response(cfg.status)
        req.send_header("Content-Type", cfg.content_type)
        req.send_header("Content-Length", str(len(body_bytes)))
        req.send_header("X-Porthole-Mock", "true")
        for name, value in cfg.headers.items():
            req.send_header(name, value)
        req.end_headers()
        req.wfile.write(body_bytes)
        return cfg.status

    return handler
