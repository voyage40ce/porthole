"""File watcher for hot-reloading porthole config on changes."""

import logging
import threading
import time
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class ConfigWatcher:
    """Watches a config file and triggers a callback when it changes."""

    def __init__(
        self,
        config_path: str | Path,
        on_change: Callable[[Path], None],
        poll_interval: float = 1.0,
    ) -> None:
        self.config_path = Path(config_path)
        self.on_change = on_change
        self.poll_interval = poll_interval
        self._last_mtime: Optional[float] = None
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def _get_mtime(self) -> Optional[float]:
        try:
            return self.config_path.stat().st_mtime
        except FileNotFoundError:
            return None

    def _watch_loop(self) -> None:
        self._last_mtime = self._get_mtime()
        while not self._stop_event.is_set():
            time.sleep(self.poll_interval)
            current_mtime = self._get_mtime()
            if current_mtime is None:
                continue
            if self._last_mtime is None or current_mtime != self._last_mtime:
                self._last_mtime = current_mtime
                logger.info("Config changed: %s — reloading", self.config_path)
                try:
                    self.on_change(self.config_path)
                except Exception as exc:  # noqa: BLE001
                    logger.error("Error reloading config: %s", exc)

    def start(self) -> None:
        """Start the background watcher thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._watch_loop, name="porthole-watcher", daemon=True
        )
        self._thread.start()
        logger.debug("ConfigWatcher started for %s", self.config_path)

    def stop(self) -> None:
        """Stop the background watcher thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=self.poll_interval * 2)
        logger.debug("ConfigWatcher stopped")

    def __enter__(self) -> "ConfigWatcher":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()
