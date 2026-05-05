"""CLI sub-command: porthole ratelimit — inspect configured rate limits."""
from __future__ import annotations

from porthole.ratelimit import RateLimitRegistry

_COL = "{:<25} {:>12} {:>8}"


def _header() -> str:
    return _COL.format("SERVICE", "REQ/S", "BURST")


def _row(service: str, rps: float, burst: int) -> str:
    return _COL.format(service, f"{rps:.2f}", str(burst))


def run_ratelimit(registry: RateLimitRegistry) -> None:
    """Print current rate-limit configuration to stdout."""
    services = registry.services()
    if not services:
        print("No rate limits configured.")
        return

    print(_header())
    print("-" * 47)
    for svc in sorted(services):
        # Access internals via the public limiter for display
        with registry._lock:  # noqa: SLF001
            limiter = registry._limiters[svc]  # noqa: SLF001
        cfg = limiter._config  # noqa: SLF001
        print(_row(svc, cfg.requests_per_second, cfg.burst))
