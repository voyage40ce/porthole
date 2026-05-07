"""CLI command: porthole lb  — show load-balancer request distribution."""
from __future__ import annotations

from typing import Optional

from porthole.load_balancer import LoadBalancerRegistry

_COL_SERVICE = 20
_COL_REPLICA = 40
_COL_REQUESTS = 10


def _header() -> str:
    return (
        f"{'SERVICE':<{_COL_SERVICE}}  "
        f"{'REPLICA':<{_COL_REPLICA}}  "
        f"{'REQUESTS':>{_COL_REQUESTS}}"
    )


def _row(service: str, replica: str, count: int) -> str:
    return (
        f"{service:<{_COL_SERVICE}}  "
        f"{replica:<{_COL_REPLICA}}  "
        f"{count:>{_COL_REQUESTS}}"
    )


def run_load_balancer(
    registry: LoadBalancerRegistry,
    service_filter: Optional[str] = None,
) -> None:
    """Print a table of replica request counts to stdout."""
    services = registry.all_services()
    if service_filter:
        services = [s for s in services if s == service_filter]

    if not services:
        print("No load-balanced services registered.")
        return

    print(_header())
    print("-" * (_COL_SERVICE + _COL_REPLICA + _COL_REQUESTS + 4))

    for svc in sorted(services):
        counts = registry.counts(svc)
        if not counts:
            continue
        for replica, count in sorted(counts.items()):
            print(_row(svc, replica, count))
