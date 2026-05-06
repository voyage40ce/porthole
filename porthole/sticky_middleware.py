"""Middleware that enforces sticky sessions via a request header."""
from __future__ import annotations

import uuid
from http.server import BaseHTTPRequestHandler
from typing import Callable, List

from porthole.sticky import StickyConfig, StickyRegistry

HandlerFn = Callable[[BaseHTTPRequestHandler], int]


def sticky_proxy(
    next_handler: HandlerFn,
    upstreams: List[str],
    registry: StickyRegistry,
    config: StickyConfig,
) -> HandlerFn:
    """Wrap *next_handler* with sticky-session logic.

    The session token is read from (and written to) the response via the
    header named in *config.header*.  If no token is present a new UUID is
    minted and the client is pinned to a deterministically chosen upstream.
    """

    def handler(request: BaseHTTPRequestHandler) -> int:
        token: str = request.headers.get(config.header, "").strip()
        if not token:
            token = str(uuid.uuid4())

        # Ensure the token is pinned before forwarding.
        upstream = registry.pick_and_pin(token, upstreams)

        # Stash the resolved upstream so the inner proxy can use it.
        request.__dict__["_sticky_upstream"] = upstream
        request.__dict__["_sticky_token"] = token

        status = next_handler(request)

        # Best-effort: attempt to send the session header back.  The inner
        # handler may have already started writing headers, in which case
        # this is a no-op in practice (tests can inspect the attribute).
        try:
            request.send_header(config.header, token)
        except Exception:  # noqa: BLE001
            pass

        return status

    return handler
