"""CLI command to display active IP filter rules."""
from __future__ import annotations

from porthole.ip_filter import IPFilterRegistry


def _header() -> str:
    return f"{'SERVICE':<20} {'MODE':<10} {'RULES'}"


def _row(service: str, mode: str, rules: list[str]) -> str:
    rules_str = ", ".join(rules) if rules else "(none)"
    return f"{service:<20} {mode:<10} {rules_str}"


def run_ip_filter(registry: IPFilterRegistry) -> None:
    """Print a summary of IP filter rules to stdout."""
    configs = {
        svc: cfg
        for svc, cfg in registry._configs.items()
    }

    if not configs:
        print("No IP filter rules configured.")
        return

    print(_header())
    print("-" * 60)
    for service, cfg in sorted(configs.items()):
        if cfg.allowlist:
            mode = "allowlist"
            rules = cfg.allowlist
        elif cfg.blocklist:
            mode = "blocklist"
            rules = cfg.blocklist
        else:
            mode = "open"
            rules = []
        print(_row(service, mode, rules))
