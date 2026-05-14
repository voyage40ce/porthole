"""CLI command: display registered URL rewrite rules."""
from __future__ import annotations

from porthole.rewrite_rules import RewriteRulesRegistry

_COL_SERVICE = 20
_COL_PATTERN = 30
_COL_REPLACEMENT = 30


def _header() -> str:
    return (
        f"{'SERVICE':<{_COL_SERVICE}}  "
        f"{'PATTERN':<{_COL_PATTERN}}  "
        f"{'REPLACEMENT':<{_COL_REPLACEMENT}}"
    )


def _row(service: str, pattern: str, replacement: str) -> str:
    return (
        f"{service:<{_COL_SERVICE}}  "
        f"{pattern:<{_COL_PATTERN}}  "
        f"{replacement:<{_COL_REPLACEMENT}}"
    )


def run_rewrite_rules(registry: RewriteRulesRegistry) -> None:
    """Print a table of all registered rewrite rules to stdout."""
    services = registry.services()
    if not services:
        print("No rewrite rules registered.")
        return

    print(_header())
    print("-" * (_COL_SERVICE + _COL_PATTERN + _COL_REPLACEMENT + 4))

    for svc in sorted(services):
        cfg = registry.get(svc)
        if cfg is None:
            continue
        for idx, rule in enumerate(cfg.rules):
            label = svc if idx == 0 else ""
            print(_row(label, rule.pattern, rule.replacement))
