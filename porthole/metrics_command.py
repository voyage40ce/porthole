"""CLI helper: print a metrics summary table to stdout."""

from __future__ import annotations

from typing import Optional

from porthole.metrics import get_collector

_COL = (
    ("Service", 24),
    ("Requests", 10),
    ("Errors", 8),
    ("Err %", 8),
    ("Avg ms", 10),
)


def _header() -> str:
    parts = [f"{label:<{width}}" for label, width in _COL]
    sep = "-" * sum(w + 2 for _, w in _COL)
    return "\n".join(["  ".join(parts), sep])


def _row(name: str, m) -> str:
    err_pct = f"{m.error_rate * 100:.1f}"
    avg = f"{m.avg_duration_ms:.1f}"
    cells = [
        f"{name:<24}",
        f"{m.total_requests:<10}",
        f"{m.error_requests:<8}",
        f"{err_pct:<8}",
        f"{avg:<10}",
    ]
    return "  ".join(cells)


def run_metrics(reset_after: bool = False) -> None:
    """Print metrics table; optionally reset counters afterwards."""
    collector = get_collector()
    data = collector.snapshot()

    if not data:
        print("No metrics recorded yet.")
        return

    print(_header())
    for name, metrics in sorted(data.items()):
        print(_row(name, metrics))

    if reset_after:
        collector.reset()
        print("\nMetrics reset.")
