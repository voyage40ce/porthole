"""Tests for ProxyServer lifecycle management."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from porthole.server import ProxyServer


@pytest.fixture()
def coordinator():
    coord = MagicMock()
    coord.config = MagicMock()
    return coord


@pytest.fixture()
def server(coordinator):
    return ProxyServer(host="127.0.0.1", port=0, coordinator=coordinator)


def test_server_starts_and_is_running(server):
    with patch("porthole.server.HTTPServer") as mock_http, \
         patch("porthole.server.make_proxy_handler"):
        mock_instance = MagicMock()
        mock_http.return_value = mock_instance
        server.start()
        assert server._thread is not None
        server.stop()


def test_is_running_false_before_start(server):
    assert server.is_running is False


def test_stop_before_start_does_not_raise(server):
    server.stop()  # should not raise


def test_restart_calls_stop_then_start(server):
    server.stop = MagicMock()
    server.start = MagicMock()
    server.restart()
    server.stop.assert_called_once()
    server.start.assert_called_once()


def test_server_binds_correct_host_port(coordinator):
    with patch("porthole.server.HTTPServer") as mock_http, \
         patch("porthole.server.make_proxy_handler"):
        mock_http.return_value = MagicMock()
        srv = ProxyServer("0.0.0.0", 9999, coordinator)
        srv.start()
        mock_http.assert_called_once_with(("0.0.0.0", 9999), mock_http.call_args[0][1])
        srv.stop()


def test_make_proxy_handler_called_with_coordinator(coordinator):
    with patch("porthole.server.HTTPServer") as mock_http, \
         patch("porthole.server.make_proxy_handler") as mock_make:
        mock_http.return_value = MagicMock()
        srv = ProxyServer("127.0.0.1", 0, coordinator)
        srv.start()
        mock_make.assert_called_once_with(coordinator)
        srv.stop()
