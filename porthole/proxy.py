"""Core proxy logic for routing HTTP requests to configured backend services."""

from __future__ import annotations

import http.client
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

from porthole.config import PortholeConfig, ServiceConfig

logger = logging.getLogger(__name__)


def _find_service(config: PortholeConfig, host_header: str) -> Optional[ServiceConfig]:
    """Match an incoming Host header to a configured service."""
    # Strip port from host header if present
    hostname = host_header.split(":")[0]
    for service in config.services:
        if service.host == hostname:
            return service
    return None


def _make_handler(config: PortholeConfig) -> type:
    """Factory that creates a request handler class bound to the given config."""

    class ProxyHandler(BaseHTTPRequestHandler):
        _config = config

        def log_message(self, fmt: str, *args: object) -> None:  # type: ignore[override]
            logger.debug(fmt, *args)

        def _proxy_request(self) -> None:
            host_header = self.headers.get("Host", "")
            service = _find_service(self._config, host_header)

            if service is None:
                self.send_error(502, f"No service configured for host: {host_header!r}")
                return

            target_host = service.target_host
            target_port = service.target_port
            path = self.path

            try:
                conn = http.client.HTTPConnection(target_host, target_port, timeout=10)
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length) if content_length else None

                forward_headers = {k: v for k, v in self.headers.items()
                                   if k.lower() not in ("host",)}
                forward_headers["Host"] = f"{target_host}:{target_port}"

                conn.request(self.command, path, body=body, headers=forward_headers)
                resp = conn.getresponse()

                self.send_response(resp.status)
                for header, value in resp.getheaders():
                    if header.lower() not in ("transfer-encoding",):
                        self.send_header(header, value)
                self.end_headers()
                self.wfile.write(resp.read())
            except OSError as exc:
                logger.error("Proxy error for %s: %s", service.name, exc)
                self.send_error(502, f"Upstream unreachable: {exc}")

        def do_GET(self) -> None:      self._proxy_request()
        def do_POST(self) -> None:     self._proxy_request()
        def do_PUT(self) -> None:      self._proxy_request()
        def do_DELETE(self) -> None:   self._proxy_request()
        def do_PATCH(self) -> None:    self._proxy_request()
        def do_HEAD(self) -> None:     self._proxy_request()
        def do_OPTIONS(self) -> None:  self._proxy_request()

    return ProxyHandler


def run_proxy(config: PortholeConfig) -> None:
    """Start the blocking proxy server on the configured listen port."""
    handler_cls = _make_handler(config)
    server = HTTPServer((config.listen_host, config.listen_port), handler_cls)
    logger.info(
        "Porthole proxy listening on %s:%s",
        config.listen_host,
        config.listen_port,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down proxy.")
    finally:
        server.server_close()
