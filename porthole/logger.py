"""Structured request/event logging for porthole."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

_LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}


def configure_logging(level: str = "info", json_output: bool = False) -> None:
    """Configure root logger with optional JSON formatting."""
    numeric_level = _LOG_LEVELS.get(level.lower(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    if json_output:
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
    root = logging.getLogger("porthole")
    root.setLevel(numeric_level)
    root.handlers.clear()
    root.addHandler(handler)
    root.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the porthole namespace."""
    return logging.getLogger(f"porthole.{name}")


def log_request(
    logger: logging.Logger,
    method: str,
    host: str,
    path: str,
    status: int,
    duration_ms: float,
) -> None:
    """Emit a structured log line for a proxied request."""
    logger.info(
        "proxied",
        extra={
            "method": method,
            "host": host,
            "path": path,
            "status": status,
            "duration_ms": round(duration_ms, 2),
        },
    )


class _JsonFormatter(logging.Formatter):
    """Emit each log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in logging.LogRecord.__dict__ and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload)
