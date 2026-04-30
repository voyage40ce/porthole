"""Tests for porthole.logger."""

from __future__ import annotations

import json
import logging

import pytest

from porthole.logger import (
    _JsonFormatter,
    configure_logging,
    get_logger,
    log_request,
)


def test_get_logger_namespace():
    logger = get_logger("proxy")
    assert logger.name == "porthole.proxy"


def test_configure_logging_sets_level():
    configure_logging(level="debug")
    root = logging.getLogger("porthole")
    assert root.level == logging.DEBUG


def test_configure_logging_default_level():
    configure_logging()
    root = logging.getLogger("porthole")
    assert root.level == logging.INFO


def test_configure_logging_invalid_level_defaults_to_info():
    configure_logging(level="nonsense")
    root = logging.getLogger("porthole")
    assert root.level == logging.INFO


def test_configure_logging_clears_handlers():
    configure_logging()
    configure_logging()  # second call should not double-up handlers
    root = logging.getLogger("porthole")
    assert len(root.handlers) == 1


def test_json_formatter_produces_valid_json():
    formatter = _JsonFormatter()
    record = logging.LogRecord(
        name="porthole.test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="hello world",
        args=(),
        exc_info=None,
    )
    output = formatter.format(record)
    data = json.loads(output)
    assert data["msg"] == "hello world"
    assert data["level"] == "info"
    assert "ts" in data


def test_json_formatter_includes_extra_fields():
    formatter = _JsonFormatter()
    record = logging.LogRecord(
        name="porthole.test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="req",
        args=(),
        exc_info=None,
    )
    record.status = 200
    record.duration_ms = 12.5
    output = formatter.format(record)
    data = json.loads(output)
    assert data["status"] == 200
    assert data["duration_ms"] == 12.5


def test_log_request_emits_at_info(caplog):
    configure_logging(level="info")
    logger = get_logger("test_req")
    with caplog.at_level(logging.INFO, logger="porthole.test_req"):
        log_request(logger, "GET", "api.local", "/health", 200, 3.14)
    assert any("proxied" in r.message for r in caplog.records)
