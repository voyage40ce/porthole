"""Command-line entry point for porthole."""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from pathlib import Path

from porthole.reload import ReloadCoordinator
from porthole.server import ProxyServer
from porthole.watcher import ConfigWatcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("porthole")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="porthole",
        description="Lightweight local proxy manager for microservices.",
    )
    parser.add_argument(
        "--config",
        default="porthole/porthole.toml",
        help="Path to porthole.toml config file.",
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host to bind the proxy server."
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="Port to bind the proxy server."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    coordinator = ReloadCoordinator(config_path)
    coordinator.load_initial()

    server = ProxyServer(args.host, args.port, coordinator)
    coordinator.register_reload_callback(server.restart)
    server.start()

    watcher = ConfigWatcher(config_path, on_change=coordinator.reload)
    watcher.start()

    stop_event = signal.Event() if hasattr(signal, "Event") else None

    def _shutdown(sig: int, frame: object) -> None:
        logger.info("Shutting down porthole (signal %d)...", sig)
        watcher.stop()
        server.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    logger.info("porthole running. Press Ctrl+C to stop.")
    while True:
        time.sleep(1)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
