"""Middleware that rewrites the upstream target using the load balancer."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler
from typing import Callable

from porthole.load_balancer import LoadBalancerRegistry


def load_balanced_proxy(
    registry: LoadBalancerRegistry,
    service: str,
    next_handler: Callable[[BaseHTTPRequestHandler, str], int],
) -> Callable[[BaseHTTPRequestHandler, str], int]:
    """Return a handler that picks the next replica before calling *next_handler*.

    If no replicas are registered for *service* the original *target* passed by
    the caller is used unchanged so the middleware degrades gracefully.
    """

    def handler(request: BaseHTTPRequestHandler, target: str) -> int:
        replica = registry.next_replica(service)
        resolved = replica if replica is not None else target
        return next_handler(request, resolved)

    return handler
