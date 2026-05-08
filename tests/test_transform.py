"""Tests for porthole.transform and porthole.transform_command."""
from __future__ import annotations

import io
import sys
import pytest

from porthole.transform import TransformConfig, TransformRegistry
from porthole.transform_command import _header, _row, run_transform


# ---------------------------------------------------------------------------
# TransformConfig validation
# ---------------------------------------------------------------------------

def test_config_rejects_missing_find_key():
    with pytest.raises(ValueError, match="'find' and 'replace'"):
        TransformConfig(service="svc", response_body_rewrites=[{"replace": "x"}])


def test_config_rejects_invalid_regex():
    with pytest.raises(ValueError, match="Invalid regex"):
        TransformConfig(
            service="svc", response_body_rewrites=[{"find": "[unclosed", "replace": ""}]
        )


def test_config_normalises_strip_headers():
    cfg = TransformConfig(service="svc", strip_response_headers=["X-Powered-By", "Server"])
    assert "x-powered-by" in cfg.strip_response_headers
    assert "server" in cfg.strip_response_headers


# ---------------------------------------------------------------------------
# TransformRegistry – request headers
# ---------------------------------------------------------------------------

@pytest.fixture()
def registry() -> TransformRegistry:
    reg = TransformRegistry()
    reg.register(
        TransformConfig(
            service="api",
            inject_request_headers={"X-Porthole": "1", "X-Env": "dev"},
            strip_response_headers=["X-Powered-By"],
            response_body_rewrites=[
                {"find": r"localhost", "replace": "example.com"}
            ],
        )
    )
    return reg


def test_apply_request_headers_merges(registry):
    result = registry.apply_request_headers("api", {"Accept": "application/json"})
    assert result["Accept"] == "application/json"
    assert result["X-Porthole"] == "1"
    assert result["X-Env"] == "dev"


def test_apply_request_headers_unknown_service(registry):
    original = {"Accept": "*/*"}
    result = registry.apply_request_headers("unknown", original)
    assert result == original


# ---------------------------------------------------------------------------
# TransformRegistry – response body
# ---------------------------------------------------------------------------

def test_apply_response_body_rewrites_text(registry):
    body = b"connect to localhost:8080"
    result = registry.apply_response_body("api", body, "text/plain")
    assert b"example.com" in result
    assert b"localhost" not in result


def test_apply_response_body_skips_binary(registry):
    body = b"\x89PNG\r\n\x1a\n"
    result = registry.apply_response_body("api", body, "image/png")
    assert result == body


def test_apply_response_body_unknown_service(registry):
    body = b"hello localhost"
    result = registry.apply_response_body("nope", body, "text/plain")
    assert result == body


# ---------------------------------------------------------------------------
# TransformRegistry – response headers
# ---------------------------------------------------------------------------

def test_filter_response_headers_removes_stripped(registry):
    headers = {"Content-Type": "text/html", "X-Powered-By": "PHP/8"}
    result = registry.filter_response_headers("api", headers)
    assert "Content-Type" in result
    assert "X-Powered-By" not in result


def test_filter_response_headers_unknown_service(registry):
    headers = {"X-Powered-By": "PHP/8"}
    result = registry.filter_response_headers("ghost", headers)
    assert result == headers


# ---------------------------------------------------------------------------
# transform_command
# ---------------------------------------------------------------------------

def test_header_contains_columns():
    hdr = _header()
    assert "SERVICE" in hdr
    assert "INJECT HEADERS" in hdr
    assert "STRIP HEADERS" in hdr
    assert "BODY REWRITES" in hdr


def test_row_formats_service(registry):
    line = _row("api", registry)
    assert "api" in line
    assert "X-Porthole" in line or "x-porthole" in line.lower() or "X-Porthole" in line


def test_run_transform_no_services_prints_message(capsys):
    run_transform(TransformRegistry())
    out = capsys.readouterr().out
    assert "No transform rules" in out


def test_run_transform_shows_service(registry, capsys):
    run_transform(registry)
    out = capsys.readouterr().out
    assert "api" in out


def test_run_transform_verbose_shows_rewrites(registry, capsys):
    run_transform(registry, verbose=True)
    out = capsys.readouterr().out
    assert "localhost" in out
    assert "example.com" in out
