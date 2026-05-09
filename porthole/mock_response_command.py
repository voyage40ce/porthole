"""CLI helpers for displaying the active mock-response configuration."""

from __future__ import annotations

from typing import Optional

from porthole.mock_response import MockRegistry


def _header() -> str:
    return (
        f"{'SERVICE':<20} {'STATUS':>6}  {'CONTENT-TYPE':<25} {'BODY (preview)'}"
    )


def _row(service: str, status: int, content_type: str, body: str) -> str:
    preview = body[:40].replace("\n", " ")
    if len(body) > 40:
        preview += "…"
    return f"{service:<20} {status:>6}  {content_type:<25} {preview}"


def run_mock_response(registry: MockRegistry, out=None) -> None:
    """Print a summary table of all registered mock responses."""
    import sys

    out = out or sys.stdout

    mocks = registry.all_services()
    if not mocks:
        out.write("No mock responses registered.\n")
        return

    out.write(_header() + "\n")
    out.write("-" * 80 + "\n")
    for service, cfg in sorted(mocks.items()):
        out.write(_row(service, cfg.status, cfg.content_type, cfg.body) + "\n")
