"""Tests for porthole config loader."""

import textwrap
from pathlib import Path

import pytest

from porthole.config import (
    PortholeConfig,
    ServiceConfig,
    load_config,
)


MINIMAL_TOML = textwrap.dedent("""\
    [services.api]
    target = "http://localhost:3000"
    port = 3000
""")

FULL_TOML = textwrap.dedent("""\
    [proxy]
    host = "0.0.0.0"
    port = 9090
    log_level = "debug"

    [services.api]
    target = "http://localhost:3000"
    port = 3000
    prefix = "/api"
    strip_prefix = true

    [services.api.headers]
    X-Custom = "yes"
""")


@pytest.fixture
def tmp_toml(tmp_path):
    def _write(content: str) -> Path:
        p = tmp_path / "porthole.toml"
        p.write_text(content)
        return p
    return _write


def test_load_minimal_config(tmp_toml):
    cfg = load_config(tmp_toml(MINIMAL_TOML))
    assert isinstance(cfg, PortholeConfig)
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 8080
    assert len(cfg.services) == 1
    svc = cfg.services[0]
    assert svc.name == "api"
    assert svc.target == "http://localhost:3000"
    assert svc.port == 3000
    assert svc.strip_prefix is False


def test_load_full_config(tmp_toml):
    cfg = load_config(tmp_toml(FULL_TOML))
    assert cfg.host == "0.0.0.0"
    assert cfg.port == 9090
    assert cfg.log_level == "debug"
    svc = cfg.services[0]
    assert svc.prefix == "/api"
    assert svc.strip_prefix is True
    assert svc.headers == {"X-Custom": "yes"}


def test_missing_config_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="No porthole config found"):
        load_config(tmp_path / "nonexistent.toml")


def test_invalid_target_raises():
    with pytest.raises(ValueError, match="target must start with"):
        ServiceConfig(name="bad", target="localhost:3000", port=3000)


def test_invalid_port_raises():
    with pytest.raises(ValueError, match="port must be between"):
        ServiceConfig(name="bad", target="http://localhost:3000", port=99999)
