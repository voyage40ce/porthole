"""Tests for porthole.header_rewrite and porthole.header_rewrite_command."""
from __future__ import annotations

import io
import sys
from unittest.mock import MagicMock

import pytest

from porthole.header_rewrite import (
    HeaderRewriteConfig,
    HeaderRewriteRegistry,
    apply_request_rewrites,
    header_rewrite_proxy,
)
from porthole.header_rewrite_command import run_header_rewrite


# ---------------------------------------------------------------------------
# HeaderRewriteConfig
# ---------------------------------------------------------------------------

def test_config_normalises_header_names():
    cfg = HeaderRewriteConfig(
        add={"X-Custom": "hello"},
        remove=["Authorization"],
        override={"Content-Type": "application/json"},
    )
    assert "x-custom" in cfg.add
    assert "authorization" in cfg.remove
    assert "content-type" in cfg.override


# ---------------------------------------------------------------------------
# apply_request_rewrites
# ---------------------------------------------------------------------------

def test_add_inserts_missing_header():
    cfg = HeaderRewriteConfig(add={"x-request-id": "abc"})
    result = apply_request_rewrites({"host": "localhost"}, cfg)
    assert result["x-request-id"] == "abc"


def test_add_does_not_overwrite_existing():
    cfg = HeaderRewriteConfig(add={"x-request-id": "new"})
    result = apply_request_rewrites({"x-request-id": "existing"}, cfg)
    assert result["x-request-id"] == "existing"


def test_override_replaces_existing():
    cfg = HeaderRewriteConfig(override={"content-type": "text/plain"})
    result = apply_request_rewrites({"content-type": "application/json"}, cfg)
    assert result["content-type"] == "text/plain"


def test_remove_deletes_header():
    cfg = HeaderRewriteConfig(remove=["authorization"])
    result = apply_request_rewrites({"authorization": "Bearer token", "host": "svc"}, cfg)
    assert "authorization" not in result
    assert "host" in result


def test_remove_missing_header_is_noop():
    cfg = HeaderRewriteConfig(remove=["x-does-not-exist"])
    result = apply_request_rewrites({"host": "svc"}, cfg)
    assert result == {"host": "svc"}


def test_original_headers_not_mutated():
    original = {"host": "svc", "authorization": "secret"}
    cfg = HeaderRewriteConfig(remove=["authorization"])
    apply_request_rewrites(original, cfg)
    assert "authorization" in original


# ---------------------------------------------------------------------------
# HeaderRewriteRegistry
# ---------------------------------------------------------------------------

def test_registry_returns_none_for_unknown():
    reg = HeaderRewriteRegistry()
    assert reg.get("missing") is None


def test_registry_stores_and_retrieves():
    reg = HeaderRewriteRegistry()
    cfg = HeaderRewriteConfig(add={"x-env": "dev"})
    reg.register("api", cfg)
    assert reg.get("api") is cfg


# ---------------------------------------------------------------------------
# header_rewrite_proxy middleware
# ---------------------------------------------------------------------------

def test_middleware_applies_rules():
    reg = HeaderRewriteRegistry()
    reg.register("api", HeaderRewriteConfig(add={"x-forwarded-by": "porthole"}))

    captured = {}

    def next_handler(self, method, url, headers, body):
        captured["headers"] = headers
        return 200

    handler = header_rewrite_proxy("api", reg, next_handler)
    handler(None, "GET", "http://api/path", {"host": "api"}, b"")
    assert captured["headers"]["x-forwarded-by"] == "porthole"


def test_middleware_passthrough_when_no_rules():
    reg = HeaderRewriteRegistry()  # no rules registered
    original = {"host": "svc", "accept": "*/*"}

    captured = {}

    def next_handler(self, method, url, headers, body):
        captured["headers"] = headers
        return 200

    handler = header_rewrite_proxy("svc", reg, next_handler)
    handler(None, "GET", "http://svc/", original, b"")
    assert captured["headers"]["host"] == "svc"


# ---------------------------------------------------------------------------
# run_header_rewrite command
# ---------------------------------------------------------------------------

def test_run_header_rewrite_no_rules(capsys):
    reg = HeaderRewriteRegistry()
    run_header_rewrite(reg, ["api"])
    out = capsys.readouterr().out
    assert "No header rewrite rules configured" in out


def test_run_header_rewrite_shows_rules(capsys):
    reg = HeaderRewriteRegistry()
    reg.register("api", HeaderRewriteConfig(
        add={"x-env": "dev"},
        override={"content-type": "application/json"},
        remove=["authorization"],
    ))
    run_header_rewrite(reg, ["api"])
    out = capsys.readouterr().out
    assert "x-env" in out
    assert "add" in out
    assert "override" in out
    assert "remove" in out
    assert "authorization" in out
