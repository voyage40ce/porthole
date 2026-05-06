"""CLI helper that prints the current retry configuration."""
from __future__ import annotations

from porthole.reload import ReloadCoordinator
from porthole.retry import RetryConfig


def _header() -> str:
    return f"{'SERVICE':<24} {'MAX_ATTEMPTS':>12} {'BACKOFF_BASE_MS':>16} {'MULTIPLIER':>12} {'RETRYABLE_CODES'}"


def _row(service: str, cfg: RetryConfig) -> str:
    codes = ",".join(str(c) for c in cfg.retryable_status_codes)
    return (
        f"{service:<24}"
        f" {cfg.max_attempts:>12}"
        f" {cfg.backoff_base_ms:>16.1f}"
        f" {cfg.backoff_multiplier:>12.1f}"
        f" {codes}"
    )


def run_retry(coordinator: ReloadCoordinator) -> None:
    """Print retry config for every service that has one."""
    cfg = coordinator.config
    services_with_retry = [
        svc for svc in cfg.services if svc.retry is not None
    ]
    if not services_with_retry:
        print("No retry configuration found for any service.")
        return

    print(_header())
    print("-" * 80)
    for svc in services_with_retry:
        print(_row(svc.name, svc.retry))
