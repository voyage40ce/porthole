"""HTTP server lifecycle management for porthole proxy."""

from __future__ import annotations

import logging
import threading
from http.server import HTTPServer
from typing import TYPE_CHECKING

from porthole.proxy import make_proxy_handler

if TYPE_CHECKING:
    from porthole.reload import ReloadCoordinator

logger = logging.getLogger(__name__)


class ProxyServer:
    """Manages the lifecycle of the HTTP proxy server."""

    def __init__(self, host: str, port: int, coordinator: "ReloadCoordinator") -> None:
        self.host = host
        self.port = port
        self.coordinator = coordinator
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the proxy server in a background thread."""
        handler = make_proxy_handler(self.coordinator)
        self._server = HTTPServer((self.host, self.port), handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="porthole-server",
            daemon=True,
        )
        self._thread.start()
        logger.info("Proxy server listening on %s:%d", self.host, self.port)

    def stop(self) -> None:
        """Gracefully shut down the proxy server."""
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            logger.info("Proxy server stopped.")
        if self._thread is not None:
            self._thread.join(timeout=5)

    def restart(self) -> None:
        """Restart the server (e.g. after a config reload)."""
        logger.info("Restarting proxy server...")
        self.stop()
        self.start()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
