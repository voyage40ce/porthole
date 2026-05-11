"""Tests for porthole.tracing."""
from __future__ import annotations

import pytest

from porthole.tracing import (
    TracingConfig,
    _TraceStore,
    generate_trace_id,
    get_store,
    tracing_proxy,
)


# ---------------------------------------------------------------------------
# TracingConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = TracingConfig()
    assert cfg.request_header == "X-Trace-Id"
    assert cfg.response_header == "X-Trace-Id"
    assert cfg.propagate_incoming is True


def test_config_rejects_empty_request_header():
    with pytest.raises(ValueError, match="request_header"):
        TracingConfig(request_header="   ")


def test_config_rejects_empty_response_header():
    with pytest.raises(ValueError, match="response_header"):
        TracingConfig(response_header="")


def test_config_normalises_whitespace():
    cfg = TracingConfig(request_header="  X-My-Trace  ")
    assert cfg.request_header == "X-My-Trace"


# ---------------------------------------------------------------------------
# generate_trace_id
# ---------------------------------------------------------------------------

def test_generate_trace_id_is_hex():
    tid = generate_trace_id()
    assert len(tid) == 32
    int(tid, 16)  # raises if not valid hex


def test_generate_trace_id_is_unique():
    assert generate_trace_id() != generate_trace_id()


# ---------------------------------------------------------------------------
# _TraceStore
# ---------------------------------------------------------------------------

def test_store_record_and_latest():
    store = _TraceStore()
    store.record("svc-a", "abc123")
    assert store.latest("svc-a") == "abc123"


def test_store_missing_returns_none():
    store = _TraceStore()
    assert store.latest("unknown") is None


def test_store_evicts_oldest_when_full():
    store = _TraceStore(max_entries=2)
    store.record("a", "1")
    store.record("b", "2")
    store.record("c", "3")  # should evict "a"
    assert store.latest("a") is None
    assert store.latest("b") == "2"
    assert store.latest("c") == "3"


def test_store_all_ids():
    store = _TraceStore()
    store.record("x", "id-x")
    store.record("y", "id-y")
    ids = store.all_ids()
    assert ids == {"x": "id-x", "y": "id-y"}


# ---------------------------------------------------------------------------
# tracing_proxy middleware
# ---------------------------------------------------------------------------

class _FakeRequest:
    def __init__(self, headers=None):
        self.headers = headers or {}


class _FakeResponse:
    def __init__(self):
        self.headers = {}


def test_middleware_injects_trace_id():
    cfg = TracingConfig()
    req = _FakeRequest()
    resp = _FakeResponse()

    handler = tracing_proxy(cfg, "my-svc", lambda r: resp)
    handler(req)

    assert cfg.request_header in req.headers
    assert len(req.headers[cfg.request_header]) == 32


def test_middleware_propagates_incoming_trace_id():
    cfg = TracingConfig(propagate_incoming=True)
    req = _FakeRequest(headers={cfg.request_header: "existing-id"})
    resp = _FakeResponse()

    handler = tracing_proxy(cfg, "my-svc", lambda r: resp)
    handler(req)

    assert req.headers[cfg.request_header] == "existing-id"


def test_middleware_ignores_incoming_when_disabled():
    cfg = TracingConfig(propagate_incoming=False)
    req = _FakeRequest(headers={cfg.request_header: "caller-id"})
    resp = _FakeResponse()

    handler = tracing_proxy(cfg, "my-svc", lambda r: resp)
    handler(req)

    assert req.headers[cfg.request_header] != "caller-id"


def test_middleware_records_trace_in_store():
    store = get_store()
    cfg = TracingConfig()
    req = _FakeRequest()
    resp = _FakeResponse()

    handler = tracing_proxy(cfg, "store-svc", lambda r: resp)
    handler(req)

    assert store.latest("store-svc") == req.headers[cfg.request_header]


def test_middleware_echoes_trace_in_response():
    cfg = TracingConfig(response_header="X-Response-Trace")
    req = _FakeRequest()
    resp = _FakeResponse()

    handler = tracing_proxy(cfg, "echo-svc", lambda r: resp)
    handler(req)

    assert resp.headers.get("X-Response-Trace") == req.headers[cfg.request_header]
