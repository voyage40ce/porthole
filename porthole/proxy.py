"""Reverse proxy request handler for porthole."""

from __future__ import annotations

import http.client
import logging
import urllib.parse
from http.server import BaseHTTPRequestHandler
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from porthole.config import ServiceConfig
    from porthole.reload import ReloadCoordinator

logger = logging.getLogger(__name__)

HOP_BY_HOP = frozenset([
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade",
])


def _find_service(host: str, coordinator: "ReloadCoordinator") -> "ServiceConfig | None":
    """Return the ServiceConfig whose host matches the request host."""
    bare = host.split(":")[0]
    for svc in coordinator.config.services:
        if svc.host == bare or svc.host == host:
            return svc
    return None


def _proxy_request(handler: BaseHTTPRequestHandler, target: str) -> None:
    """Forward the incoming request to *target* and stream back the response."""
    parsed = urllib.parse.urlparse(target)
    use_https = parsed.scheme == "https"
    netloc = parsed.netloc or parsed.path

    conn_cls = http.client.HTTPSConnection if use_https else http.client.HTTPConnection
    conn = conn_cls(netloc, timeout=10)

    headers = {
        k: v for k, v in handler.headers.items()
        if k.lower() not in HOP_BY_HOP
    }
    headers["X-Forwarded-Host"] = handler.headers.get("Host", "")

    length = int(handler.headers.get("Content-Length", 0))
    body = handler.rfile.read(length) if length else None

    try:
        conn.request(handler.command, handler.path, body=body, headers=headers)
        resp = conn.getresponse()
    except OSError as exc:
        logger.error("Upstream connection failed: %s", exc)
        handler.send_error(502, f"Bad Gateway: {exc}")
        return

    handler.send_response(resp.status)
    for key, val in resp.getheaders():
        if key.lower() not in HOP_BY_HOP:
            handler.send_header(key, val)
    handler.end_headers()
    handler.wfile.write(resp.read())
    conn.close()


def make_proxy_handler(coordinator: "ReloadCoordinator") -> type:
    """Factory that returns a BaseHTTPRequestHandler subclass bound to *coordinator*."""

    class ProxyHandler(BaseHTTPRequestHandler):
        _coordinator = coordinator

        def log_message(self, fmt: str, *args: object) -> None:  # silence default stderr
            logger.debug(fmt, *args)

        def _handle(self) -> None:
            host = self.headers.get("Host", "")
            svc = _find_service(host, self._coordinator)
            if svc is None:
                self.send_error(404, f"No service configured for host: {host!r}")
                return
            target = svc.target
            logger.info("%s %s -> %s", self.command, self.path, target)
            _proxy_request(self, target)

        do_GET = _handle
        do_POST = _handle
        do_PUT = _handle
        do_DELETE = _handle
        do_PATCH = _handle
        do_HEAD = _handle
        do_OPTIONS = _handle

    return ProxyHandler
