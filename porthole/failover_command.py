"""CLI command: porthole failover — show failover status for all services."""
from __future__ import annotations

from porthole.failover import FailoverRegistry

_COL_SERVICE = 20
_COL_BACKUPS = 30
_COL_ACTIVE = 30


def _header() -> str:
    return (
        f"{'SERVICE':<{_COL_SERVICE}}"
        f"{'BACKUPS':<{_COL_BACKUPS}}"
        f"{'ACTIVE BACKUP':<{_COL_ACTIVE}}"
    )


def _row(service: str, backups: list, active: str) -> str:
    backup_str = ", ".join(backups) if backups else "-"
    return (
        f"{service:<{_COL_SERVICE}}"
        f"{backup_str:<{_COL_BACKUPS}}"
        f"{active:<{_COL_ACTIVE}}"
    )


def run_failover(registry: FailoverRegistry) -> None:
    """Print a table of failover configuration and current active backup per service."""
    services = registry.all_services()
    if not services:
        print("No failover rules configured.")
        return

    sep = "-" * (_COL_SERVICE + _COL_BACKUPS + _COL_ACTIVE)
    print(_header())
    print(sep)
    for svc in sorted(services):
        cfg = registry.get(svc)
        backups = cfg.backups if cfg else []
        active = registry.active_backup(svc) or "(primary)"
        print(_row(svc, backups, active))
