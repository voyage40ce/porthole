"""Hot-reload coordinator: ties ConfigWatcher to a live ProxyServer."""

import logging
import threading
from pathlib import Path
from typing import Optional

from porthole.config import PortholeConfig, load_config
from porthole.watcher import ConfigWatcher

logger = logging.getLogger(__name__)


class ReloadCoordinator:
    """Listens for config changes and hot-swaps the active PortholeConfig."""

    def __init__(self, config_path: str | Path, poll_interval: float = 1.0) -> None:
        self.config_path = Path(config_path)
        self._lock = threading.Lock()
        self._config: Optional[PortholeConfig] = None
        self._watcher = ConfigWatcher(
            self.config_path,
            on_change=self._reload,
            poll_interval=poll_interval,
        )
        self._reload_callbacks: list = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def config(self) -> Optional[PortholeConfig]:
        with self._lock:
            return self._config

    def register_reload_callback(self, fn) -> None:  # type: ignore[type-arg]
        """Register a callable invoked with the new config after each reload."""
        self._reload_callbacks.append(fn)

    def load_initial(self) -> PortholeConfig:
        """Load config synchronously before starting the watcher."""
        cfg = load_config(self.config_path)
        with self._lock:
            self._config = cfg
        logger.info("Initial config loaded from %s", self.config_path)
        return cfg

    def start(self) -> None:
        self._watcher.start()

    def stop(self) -> None:
        self._watcher.stop()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _reload(self, path: Path) -> None:
        new_cfg = load_config(path)
        with self._lock:
            self._config = new_cfg
        logger.info(
            "Config reloaded — %d service(s) active",
            len(new_cfg.services),
        )
        for cb in self._reload_callbacks:
            try:
                cb(new_cfg)
            except Exception as exc:  # noqa: BLE001
                logger.error("Reload callback error: %s", exc)

    def __enter__(self) -> "ReloadCoordinator":
        self.load_initial()
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()
