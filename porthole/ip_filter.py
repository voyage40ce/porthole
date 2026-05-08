"""IP allowlist/blocklist filtering middleware for Porthole."""
from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from typing import Callable, List, Optional


@dataclass
class IPFilterConfig:
    """Configuration for IP-based access control."""

    allowlist: List[str] = field(default_factory=list)
    blocklist: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.allowlist and self.blocklist:
            raise ValueError("Specify either allowlist or blocklist, not both")
        # Validate all entries are parseable networks or addresses
        for entry in self.allowlist + self.blocklist:
            try:
                ipaddress.ip_network(entry, strict=False)
            except ValueError as exc:
                raise ValueError(f"Invalid IP/CIDR entry {entry!r}: {exc}") from exc

    def is_allowed(self, client_ip: str) -> bool:
        """Return True if *client_ip* should be allowed through."""
        try:
            addr = ipaddress.ip_address(client_ip)
        except ValueError:
            return False

        if self.blocklist:
            for entry in self.blocklist:
                if addr in ipaddress.ip_network(entry, strict=False):
                    return False
            return True

        if self.allowlist:
            for entry in self.allowlist:
                if addr in ipaddress.ip_network(entry, strict=False):
                    return True
            return False

        # No rules configured — allow all
        return True


class IPFilterRegistry:
    """Holds per-service IP filter configurations."""

    def __init__(self) -> None:
        self._configs: dict[str, IPFilterConfig] = {}

    def register(self, service: str, config: IPFilterConfig) -> None:
        self._configs[service] = config

    def get(self, service: str) -> Optional[IPFilterConfig]:
        return self._configs.get(service)


def ip_filter_proxy(
    registry: IPFilterRegistry,
    service: str,
    next_handler: Callable,
) -> Callable:
    """Middleware that enforces IP filtering before forwarding the request."""

    def handler(request_handler):
        config = registry.get(service)
        client_ip = request_handler.client_address[0]

        if config is not None and not config.is_allowed(client_ip):
            request_handler.send_response(403)
            request_handler.end_headers()
            request_handler.wfile.write(b"Forbidden: IP not permitted\n")
            return 403

        return next_handler(request_handler)

    return handler
