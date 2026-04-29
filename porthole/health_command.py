"""CLI sub-command: porthole health — report reachability of configured services."""

import sys
from typing import Optional

from porthole.config import load_config, PortholeConfig
from porthole.healthcheck import check_all, HealthStatus


def run_health(
    config_path: str,
    timeout: float = 2.0,
    output=sys.stdout,
    err_output=sys.stderr,
) -> int:
    """Load config, probe each service, print results.

    Returns exit code: 0 if all healthy, 1 if any unreachable.
    """
    try:
        cfg: PortholeConfig = load_config(config_path)
    except FileNotFoundError:
        print(f"Config file not found: {config_path}", file=err_output)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to load config: {exc}", file=err_output)
        return 2

    if not cfg.services:
        print("No services configured.", file=output)
        return 0

    results: list[HealthStatus] = check_all(cfg.services, timeout=timeout)

    all_ok = True
    for status in results:
        print(str(status), file=output)
        if not status.reachable:
            all_ok = False

    return 0 if all_ok else 1
