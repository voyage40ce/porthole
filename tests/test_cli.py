"""Tests for the porthole CLI entry point."""

from __future__ import annotations

import signal
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from porthole.cli import _build_parser, main


def test_parser_defaults():
    parser = _build_parser()
    args = parser.parse_args([])
    assert args.host == "127.0.0.1"
    assert args.port == 8080
    assert "porthole.toml" in args.config


def test_parser_custom_values():
    parser = _build_parser()
    args = parser.parse_args(["--host", "0.0.0.0", "--port", "9090", "--config", "my.toml"])
    assert args.host == "0.0.0.0"
    assert args.port == 9090
    assert args.config == "my.toml"


def test_main_wires_components(tmp_path):
    cfg = tmp_path / "porthole.toml"
    cfg.write_text('[proxy]\nlisten_port = 8080\n[[services]]\nname="a"\nhost="a.local"\ntarget="http://localhost:3000"\n')

    mock_coord = MagicMock()
    mock_server = MagicMock()
    mock_watcher = MagicMock()

    with patch("porthole.cli.ReloadCoordinator", return_value=mock_coord) as MockCoord, \
         patch("porthole.cli.ProxyServer", return_value=mock_server) as MockServer, \
         patch("porthole.cli.ConfigWatcher", return_value=mock_watcher) as MockWatcher, \
         patch("porthole.cli.time.sleep", side_effect=SystemExit(0)), \
         patch("porthole.cli.signal.signal"):
        with pytest.raises(SystemExit):
            main(["--config", str(cfg)])

    mock_coord.load_initial.assert_called_once()
    mock_server.start.assert_called_once()
    mock_watcher.start.assert_called_once()
    mock_coord.register_reload_callback.assert_called_once_with(mock_server.restart)
