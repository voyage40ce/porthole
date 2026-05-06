"""CLI sub-command: display sticky-session registry state."""
from __future__ import annotations

from porthole.sticky import StickyRegistry

_COL_TOKEN = 36
_COL_UPSTREAM = 30
_COL_STATUS = 8


def _header() -> str:
    return (
        f"{'SESSION TOKEN':<{_COL_TOKEN}}  "
        f"{'UPSTREAM':<{_COL_UPSTREAM}}  "
        f"{'STATUS':<{_COL_STATUS}}"
    )


def _row(token: str, upstream: str, active: bool) -> str:
    status = "active" if active else "expired"
    return (
        f"{token:<{_COL_TOKEN}}  "
        f"{upstream:<{_COL_UPSTREAM}}  "
        f"{status:<{_COL_STATUS}}"
    )


def run_sticky(registry: StickyRegistry) -> None:  # pragma: no cover
    """Print a human-readable table of current sticky-session mappings."""
    # pylint: disable=protected-access
    store = registry._store  # type: ignore[attr-defined]
    if not store:
        print("No sticky sessions recorded.")
        return

    import time

    now = time.monotonic()
    print(_header())
    print("-" * (_COL_TOKEN + _COL_UPSTREAM + _COL_STATUS + 4))
    for token, entry in sorted(store.items()):
        active = now <= entry.expires_at
        print(_row(token, entry.upstream, active))

    stats = registry.stats()
    print(f"\nTotal: {stats['total']}  Active: {stats['active']}")
