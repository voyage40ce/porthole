"""Tests for porthole.watcher.ConfigWatcher."""

import time
from pathlib import Path

import pytest

from porthole.watcher import ConfigWatcher


@pytest.fixture()
def config_file(tmp_path: Path) -> Path:
    p = tmp_path / "porthole.toml"
    p.write_text("[porthole]\nport = 8080\n")
    return p


def test_watcher_detects_change(config_file: Path) -> None:
    """Callback is invoked when the file is modified."""
    calls: list[Path] = []

    def on_change(p: Path) -> None:
        calls.append(p)

    with ConfigWatcher(config_file, on_change, poll_interval=0.1):
        time.sleep(0.15)  # let watcher initialise
        config_file.write_text("[porthole]\nport = 9090\n")
        time.sleep(0.3)  # wait for at least one poll cycle

    assert len(calls) >= 1
    assert calls[0] == config_file


def test_watcher_no_spurious_calls(config_file: Path) -> None:
    """Callback is NOT invoked when the file is untouched."""
    calls: list[Path] = []

    with ConfigWatcher(config_file, lambda p: calls.append(p), poll_interval=0.1):
        time.sleep(0.4)

    assert calls == []


def test_watcher_missing_file_does_not_crash(tmp_path: Path) -> None:
    """Watcher tolerates a config file that does not exist yet."""
    missing = tmp_path / "missing.toml"
    calls: list[Path] = []

    with ConfigWatcher(missing, lambda p: calls.append(p), poll_interval=0.1):
        time.sleep(0.25)
        missing.write_text("[porthole]\nport = 8080\n")
        time.sleep(0.25)

    assert len(calls) >= 1


def test_watcher_context_manager_stops_thread(config_file: Path) -> None:
    """Thread is no longer alive after __exit__."""
    watcher = ConfigWatcher(config_file, lambda p: None, poll_interval=0.1)
    with watcher:
        assert watcher._thread is not None
        assert watcher._thread.is_alive()
    assert not watcher._thread.is_alive()


def test_watcher_callback_exception_does_not_stop_watcher(config_file: Path) -> None:
    """An exception in the callback is caught and the watcher keeps running."""
    call_count = 0

    def bad_callback(p: Path) -> None:
        nonlocal call_count
        call_count += 1
        raise RuntimeError("boom")

    with ConfigWatcher(config_file, bad_callback, poll_interval=0.1) as w:
        time.sleep(0.15)
        config_file.write_text("[porthole]\nport = 1111\n")
        time.sleep(0.25)
        assert w._thread is not None
        assert w._thread.is_alive()

    assert call_count >= 1
