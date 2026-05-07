"""CLI sub-command: ``porthole upstream-health``."""
from __future__ import annotations

import time

from porthole.config import PortholeConfig
from porthole.upstream_health import UpstreamHealthMonitor


_COLS = ("SERVICE", "TARGET", "STATUS", "DETAIL")
_WIDTHS = (20, 30, 8, 40)


def _header() -> str:
    parts = [c.ljust(w) for c, w in zip(_COLS, _WIDTHS)]
    line = "  ".join(parts)
    return line + "\n" + "-" * len(line)


def _row(name: str, target: str, ok: bool, detail: str) -> str:
    status = "UP" if ok else "DOWN"
    cells = [
        name[:_WIDTHS[0]].ljust(_WIDTHS[0]),
        target[:_WIDTHS[1]].ljust(_WIDTHS[1]),
        status.ljust(_WIDTHS[2]),
        detail[:_WIDTHS[3]].ljust(_WIDTHS[3]),
    ]
    return "  ".join(cells)


def run_upstream_health(
    config: PortholeConfig,
    interval: float = 10.0,
    watch: bool = False,
) -> None:
    """Print upstream health, optionally watching for changes."""
    monitor = UpstreamHealthMonitor(config=config, interval_seconds=interval)
    # Run one synchronous check before starting the background thread
    monitor._run_checks()  # noqa: SLF001

    def _print_table() -> None:
        print(_header())
        for svc in config.services:
            st = monitor.latest(svc.name)
            if st is None:
                continue
            target = f"{svc.host}:{svc.port}"
            print(_row(svc.name, target, st.ok, st.detail or ""))

    _print_table()

    if not watch:
        return

    monitor.start()
    try:
        while True:
            time.sleep(interval)
            print()
            _print_table()
    except KeyboardInterrupt:
        pass
    finally:
        monitor.stop()
