"""Tests for porthole.reload.ReloadCoordinator."""

import time
from pathlib import Path

import pytest

from porthole.reload import ReloadCoordinator

_MINIMAL = """
[porthole]
port = 8080

[[services]]
name = "api"
host = "api.local"
target = "http://localhost:3000"
"""

_UPDATED = """
[porthole]
port = 8080

[[services]]
name = "api"
host = "api.local"
target = "http://localhost:4000"

[[services]]
name = "web"
host = "web.local"
target = "http://localhost:5000"
"""


@pytest.fixture()
def cfg_file(tmp_path: Path) -> Path:
    p = tmp_path / "porthole.toml"
    p.write_text(_MINIMAL)
    return p


def test_load_initial(cfg_file: Path) -> None:
    coord = ReloadCoordinator(cfg_file, poll_interval=0.1)
    cfg = coord.load_initial()
    assert cfg.porthole.port == 8080
    assert len(cfg.services) == 1


def test_config_property_before_load(cfg_file: Path) -> None:
    coord = ReloadCoordinator(cfg_file, poll_interval=0.1)
    assert coord.config is None


def test_hot_reload_updates_config(cfg_file: Path) -> None:
    with ReloadCoordinator(cfg_file, poll_interval=0.1) as coord:
        assert coord.config is not None
        assert len(coord.config.services) == 1

        cfg_file.write_text(_UPDATED)
        time.sleep(0.4)

        assert coord.config is not None
        assert len(coord.config.services) == 2


def test_reload_callback_invoked(cfg_file: Path) -> None:
    received = []

    with ReloadCoordinator(cfg_file, poll_interval=0.1) as coord:
        coord.register_reload_callback(lambda cfg: received.append(cfg))
        cfg_file.write_text(_UPDATED)
        time.sleep(0.4)

    assert len(received) >= 1
    assert len(received[-1].services) == 2


def test_bad_callback_does_not_break_reload(cfg_file: Path) -> None:
    good = []

    def bad(_cfg) -> None:  # type: ignore[type-arg]
        raise ValueError("oops")

    with ReloadCoordinator(cfg_file, poll_interval=0.1) as coord:
        coord.register_reload_callback(bad)
        coord.register_reload_callback(lambda cfg: good.append(cfg))
        cfg_file.write_text(_UPDATED)
        time.sleep(0.4)

    assert len(good) >= 1
