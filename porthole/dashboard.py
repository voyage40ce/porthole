"""Simple ASCII dashboard showing active services and their health status."""

from __future__ import annotations

import sys
from datetime import datetime
from typing import TextIO

from porthole.config import PortholeConfig
from porthole.healthcheck import HealthStatus, check_all


_STATUS_ICON = {True: "\u2705", False: "\u274c"}
_COL_WIDTHS = {"name": 20, "host": 28, "target": 30, "status": 10}


def _header() -> str:
    cols = [
        "SERVICE".ljust(_COL_WIDTHS["name"]),
        "HOST".ljust(_COL_WIDTHS["host"]),
        "TARGET".ljust(_COL_WIDTHS["target"]),
        "STATUS",
    ]
    line = "  ".join(cols)
    return f"{line}\n{'─' * len(line)}"


def _row(name: str, host: str, target: str, status: HealthStatus) -> str:
    icon = _STATUS_ICON[status.ok]
    label = "UP" if status.ok else "DOWN"
    cols = [
        name.ljust(_COL_WIDTHS["name"]),
        host.ljust(_COL_WIDTHS["host"]),
        target.ljust(_COL_WIDTHS["target"]),
        f"{icon}  {label}",
    ]
    row = "  ".join(cols)
    if not status.ok and status.error:
        row += f"\n    \u26a0\ufe0f  {status.error}"
    return row


def render_dashboard(config: PortholeConfig, out: TextIO = sys.stdout) -> None:
    """Print a live health dashboard for all configured services."""
    statuses = check_all(config)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    out.write(f"\nPorthole Dashboard  \u2014  {timestamp}\n")
    out.write(_header() + "\n")

    for svc in config.services:
        target = f"{svc.scheme}://{svc.target_host}:{svc.target_port}"
        status = statuses.get(svc.name, HealthStatus(ok=False, error="unknown"))
        out.write(_row(svc.name, svc.host, target, status) + "\n")

    total = len(config.services)
    up = sum(1 for s in statuses.values() if s.ok)
    out.write(f"\n{up}/{total} services healthy\n")
