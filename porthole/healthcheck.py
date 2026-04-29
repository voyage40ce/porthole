"""Health check utilities for proxied services."""

import http.client
import socket
import urllib.parse
from dataclasses import dataclass
from typing import Optional

from porthole.config import ServiceConfig


@dataclass
class HealthStatus:
    service_name: str
    target: str
    reachable: bool
    status_code: Optional[int] = None
    error: Optional[str] = None

    def __str__(self) -> str:
        if self.reachable:
            return f"[OK]  {self.service_name} -> {self.target} (HTTP {self.status_code})"
        return f"[ERR] {self.service_name} -> {self.target} ({self.error})"


def check_service(service: ServiceConfig, timeout: float = 2.0) -> HealthStatus:
    """Attempt a lightweight TCP/HTTP probe against a service target."""
    parsed = urllib.parse.urlsplit(service.target)
    host = parsed.hostname or service.target
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/"

    try:
        conn: http.client.HTTPConnection
        if parsed.scheme == "https":
            conn = http.client.HTTPSConnection(host, port, timeout=timeout)
        else:
            conn = http.client.HTTPConnection(host, port, timeout=timeout)

        conn.request("HEAD", path)
        resp = conn.getresponse()
        return HealthStatus(
            service_name=service.name,
            target=service.target,
            reachable=True,
            status_code=resp.status,
        )
    except (ConnectionRefusedError, socket.timeout, OSError) as exc:
        return HealthStatus(
            service_name=service.name,
            target=service.target,
            reachable=False,
            error=str(exc),
        )


def check_all(services: list[ServiceConfig], timeout: float = 2.0) -> list[HealthStatus]:
    """Run health checks against every service in the list."""
    return [check_service(s, timeout=timeout) for s in services]
