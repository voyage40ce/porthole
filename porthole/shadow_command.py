"""CLI command: display shadow-mirroring statistics."""
from __future__ import annotations

from porthole.shadow import ShadowRegistry

_COL_SERVICE = 22
_COL_TARGET = 32
_COL_RATE = 10
_COL_MIRRORS = 10


def _header() -> str:
    return (
        f"{'SERVICE':<{_COL_SERVICE}}"
        f"{'SHADOW TARGET':<{_COL_TARGET}}"
        f"{'SAMPLE':<{_COL_RATE}}"
        f"{'MIRRORED':>{_COL_MIRRORS}}"
    )


def _row(service: str, target: str, sample_rate: float, mirrored: int) -> str:
    rate_pct = f"{sample_rate * 100:.0f}%"
    return (
        f"{service:<{_COL_SERVICE}}"
        f"{target:<{_COL_TARGET}}"
        f"{rate_pct:<{_COL_RATE}}"
        f"{mirrored:>{_COL_MIRRORS}}"
    )


def run_shadow(registry: ShadowRegistry) -> None:
    """Print a summary table of shadow mirroring configuration and counters."""
    services = registry.all_services()
    if not services:
        print("No shadow targets configured.")
        return

    print(_header())
    print("-" * (_COL_SERVICE + _COL_TARGET + _COL_RATE + _COL_MIRRORS))
    for name, cfg in sorted(services.items()):
        print(_row(name, cfg.target, cfg.sample_rate, registry.mirror_count(name)))
