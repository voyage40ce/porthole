"""Configuration loader for porthole proxy manager."""

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


DEFAULT_CONFIG_PATHS = [
    Path("porthole.toml"),
    Path(".porthole.toml"),
    Path(os.path.expanduser("~/.config/porthole/config.toml")),
]


@dataclass
class ServiceConfig:
    name: str
    target: str
    port: int
    prefix: str = "/"
    strip_prefix: bool = False
    headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not self.target.startswith(("http://", "https://")):
            raise ValueError(f"Service '{self.name}' target must start with http:// or https://")
        if not (1 <= self.port <= 65535):
            raise ValueError(f"Service '{self.name}' port must be between 1 and 65535")


@dataclass
class PortholeConfig:
    host: str = "127.0.0.1"
    port: int = 8080
    log_level: str = "info"
    services: list[ServiceConfig] = field(default_factory=list)


def load_config(path: Optional[Path] = None) -> PortholeConfig:
    """Load configuration from a TOML file."""
    config_path = path
    if config_path is None:
        for candidate in DEFAULT_CONFIG_PATHS:
            if candidate.exists():
                config_path = candidate
                break

    if config_path is None or not config_path.exists():
        raise FileNotFoundError(
            "No porthole config found. Create porthole.toml or pass --config."
        )

    with open(config_path, "rb") as f:
        raw = tomllib.load(f)

    proxy = raw.get("proxy", {})
    services = [
        ServiceConfig(
            name=name,
            target=svc["target"],
            port=svc["port"],
            prefix=svc.get("prefix", "/"),
            strip_prefix=svc.get("strip_prefix", False),
            headers=svc.get("headers", {}),
        )
        for name, svc in raw.get("services", {}).items()
    ]

    return PortholeConfig(
        host=proxy.get("host", "127.0.0.1"),
        port=proxy.get("port", 8080),
        log_level=proxy.get("log_level", "info"),
        services=services,
    )
