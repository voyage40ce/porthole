"""CLI helper that prints the active CORS configuration for each service."""

from __future__ import annotations

from porthole.cors import CORSConfig
from porthole.reload import ReloadCoordinator

_COL_SERVICE = 24
_COL_ORIGINS = 30
_COL_METHODS = 36
_COL_CREDS = 8


def _header() -> str:
    return (
        f"{'SERVICE':<{_COL_SERVICE}}"
        f"{'ALLOW_ORIGINS':<{_COL_ORIGINS}}"
        f"{'ALLOW_METHODS':<{_COL_METHODS}}"
        f"{'CREDS':<{_COL_CREDS}}"
    )


def _row(name: str, cfg: CORSConfig) -> str:
    origins = ", ".join(cfg.allow_origins)
    methods = ", ".join(cfg.allow_methods)
    creds = "yes" if cfg.allow_credentials else "no"
    return (
        f"{name:<{_COL_SERVICE}}"
        f"{origins:<{_COL_ORIGINS}}"
        f"{methods:<{_COL_METHODS}}"
        f"{creds:<{_COL_CREDS}}"
    )


def run_cors(coordinator: ReloadCoordinator) -> None:
    """Print CORS settings for every service that has them configured."""
    cfg = coordinator.config
    rows = []
    for svc in cfg.services:
        cors_raw = getattr(svc, "cors", None)
        if cors_raw is None:
            continue
        if isinstance(cors_raw, CORSConfig):
            cors_cfg = cors_raw
        else:
            cors_cfg = CORSConfig(**cors_raw)
        rows.append(_row(svc.name, cors_cfg))

    if not rows:
        print("No CORS configuration found for any service.")
        return

    print(_header())
    print("-" * (_COL_SERVICE + _COL_ORIGINS + _COL_METHODS + _COL_CREDS))
    for row in rows:
        print(row)
