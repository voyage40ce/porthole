"""CLI sub-command: show active header-rewrite rules for every service."""
from __future__ import annotations

from typing import List

from porthole.header_rewrite import HeaderRewriteRegistry


_COL_SERVICE = 20
_COL_ACTION = 10
_COL_HEADER = 30
_COL_VALUE = 30


def _header() -> str:
    return (
        f"{'SERVICE':<{_COL_SERVICE}}"
        f"{'ACTION':<{_COL_ACTION}}"
        f"{'HEADER':<{_COL_HEADER}}"
        f"{'VALUE':<{_COL_VALUE}}"
    )


def _row(service: str, action: str, header: str, value: str = "") -> str:
    return (
        f"{service:<{_COL_SERVICE}}"
        f"{action:<{_COL_ACTION}}"
        f"{header:<{_COL_HEADER}}"
        f"{value:<{_COL_VALUE}}"
    )


def run_header_rewrite(registry: HeaderRewriteRegistry, services: List[str]) -> None:
    """Print a table of header rewrite rules for *services*."""
    rows: List[str] = []

    for svc in services:
        cfg = registry.get(svc)
        if cfg is None:
            continue
        for name, value in cfg.add.items():
            rows.append(_row(svc, "add", name, value))
        for name, value in cfg.override.items():
            rows.append(_row(svc, "override", name, value))
        for name in cfg.remove:
            rows.append(_row(svc, "remove", name))

    if not rows:
        print("No header rewrite rules configured.")
        return

    print(_header())
    print("-" * (_COL_SERVICE + _COL_ACTION + _COL_HEADER + _COL_VALUE))
    for row in rows:
        print(row)
