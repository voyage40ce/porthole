"""CLI command: display registered transform rules."""
from __future__ import annotations

import json
from typing import Optional

from porthole.transform import TransformRegistry


def _header() -> str:
    return (
        f"{'SERVICE':<20}  {'INJECT HEADERS':<22}  "
        f"{'STRIP HEADERS':<22}  {'BODY REWRITES':>13}"
    )


def _row(service: str, registry: TransformRegistry) -> str:
    cfg = registry.get(service)
    if cfg is None:
        return f"{service:<20}  {'—':<22}  {'—':<22}  {'—':>13}"

    inject = ", ".join(cfg.inject_request_headers.keys()) or "—"
    strip = ", ".join(cfg.strip_response_headers) or "—"
    rewrites = str(len(cfg.response_body_rewrites))

    # Truncate long lists for display
    if len(inject) > 22:
        inject = inject[:19] + "..."
    if len(strip) > 22:
        strip = strip[:19] + "..."

    return f"{service:<20}  {inject:<22}  {strip:<22}  {rewrites:>13}"


def run_transform(
    registry: TransformRegistry,
    services: Optional[list] = None,
    *,
    verbose: bool = False,
) -> None:
    """Print a summary of all transform rules to stdout."""
    targets = services or list(registry._configs.keys())
    if not targets:
        print("No transform rules registered.")
        return

    print(_header())
    print("-" * 82)
    for svc in sorted(targets):
        print(_row(svc, registry))

    if verbose:
        print()
        for svc in sorted(targets):
            cfg = registry.get(svc)
            if cfg and cfg.response_body_rewrites:
                print(f"[{svc}] body rewrites:")
                for rule in cfg.response_body_rewrites:
                    print(f"  find={rule['find']!r}  replace={rule['replace']!r}")
