"""Request tracing — attaches a unique trace ID to every proxied request."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

from porthole.logger import get_logger

log = get_logger(__name__)

DEFAULT_REQUEST_HEADER = "X-Trace-Id"
DEFAULT_RESPONSE_HEADER = "X-Trace-Id"


@dataclass
class TracingConfig:
    """Configuration for request tracing."""

    request_header: str = DEFAULT_REQUEST_HEADER
    response_header: str = DEFAULT_RESPONSE_HEADER
    propagate_incoming: bool = True  # re-use caller's trace ID when present

    def __post_init__(self) -> None:
        if not self.request_header.strip():
            raise ValueError("request_header must not be empty")
        if not self.response_header.strip():
            raise ValueError("response_header must not be empty")
        # Normalise to canonical HTTP header capitalisation
        self.request_header = self.request_header.strip()
        self.response_header = self.response_header.strip()


@dataclass
class _TraceStore:
    """In-memory store of the most-recently-seen trace IDs (bounded)."""

    max_entries: int = 1000
    _store: Dict[str, str] = field(default_factory=dict, repr=False)

    def record(self, service: str, trace_id: str) -> None:
        if len(self._store) >= self.max_entries:
            # Evict oldest entry
            oldest = next(iter(self._store))
            del self._store[oldest]
        self._store[service] = trace_id

    def latest(self, service: str) -> Optional[str]:
        return self._store.get(service)

    def all_ids(self) -> Dict[str, str]:
        return dict(self._store)


# Module-level singleton so middleware and tests share state.
_store = _TraceStore()


def get_store() -> _TraceStore:
    return _store


def generate_trace_id() -> str:
    return uuid.uuid4().hex


def tracing_proxy(
    config: TracingConfig,
    service_name: str,
    next_handler: Callable,
) -> Callable:
    """Middleware that injects / propagates a trace ID for *service_name*."""

    def handler(request, *args, **kwargs):
        incoming = request.headers.get(config.request_header) if hasattr(request, "headers") else None
        trace_id = (incoming if config.propagate_incoming and incoming else None) or generate_trace_id()

        # Attach to outgoing request headers
        if hasattr(request, "headers"):
            request.headers[config.request_header] = trace_id

        log.debug("trace_id=%s service=%s", trace_id, service_name)
        _store.record(service_name, trace_id)

        response = next_handler(request, *args, **kwargs)

        # Echo trace ID in response if possible
        if hasattr(response, "headers"):
            response.headers[config.response_header] = trace_id

        return response

    return handler
