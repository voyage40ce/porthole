"""Tests for porthole.proxy routing and handler logic."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from porthole.config import PortholeConfig, ServiceConfig
from porthole.proxy import _find_service, _make_handler


@pytest.fixture()
def config() -> PortholeConfig:
    return PortholeConfig(
        listen_host="127.0.0.1",
        listen_port=8080,
        services=[
            ServiceConfig(name="api", host="api.local", target_host="127.0.0.1", target_port=3001),
            ServiceConfig(name="web", host="web.local", target_host="127.0.0.1", target_port=3000),
        ],
    )


class TestFindService:
    def test_exact_match(self, config: PortholeConfig) -> None:
        svc = _find_service(config, "api.local")
        assert svc is not None
        assert svc.name == "api"

    def test_host_with_port_stripped(self, config: PortholeConfig) -> None:
        svc = _find_service(config, "web.local:8080")
        assert svc is not None
        assert svc.name == "web"

    def test_unknown_host_returns_none(self, config: PortholeConfig) -> None:
        assert _find_service(config, "unknown.local") is None

    def test_empty_host_returns_none(self, config: PortholeConfig) -> None:
        assert _find_service(config, "") is None


class TestProxyHandler:
    """Unit-test the generated handler class without starting a real server."""

    def _make_mock_handler(self, config: PortholeConfig, host: str) -> MagicMock:
        """Build a handler instance with mocked socket internals."""
        handler_cls = _make_handler(config)
        handler = handler_cls.__new__(handler_cls)
        handler.headers = {"Host": host, "Content-Length": "0"}
        handler.path = "/ping"
        handler.command = "GET"
        handler.rfile = MagicMock()
        handler.wfile = MagicMock()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.send_error = MagicMock()
        return handler

    def test_unknown_host_sends_502(self, config: PortholeConfig) -> None:
        handler = self._make_mock_handler(config, "nope.local")
        handler._proxy_request()
        handler.send_error.assert_called_once()
        code = handler.send_error.call_args[0][0]
        assert code == 502

    def test_upstream_error_sends_502(self, config: PortholeConfig) -> None:
        handler = self._make_mock_handler(config, "api.local")
        with patch("porthole.proxy.http.client.HTTPConnection") as mock_conn_cls:
            mock_conn_cls.return_value.request.side_effect = OSError("refused")
            handler._proxy_request()
        handler.send_error.assert_called_once()
        assert handler.send_error.call_args[0][0] == 502

    def test_successful_proxy(self, config: PortholeConfig) -> None:
        handler = self._make_mock_handler(config, "api.local")
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.getheaders.return_value = [("Content-Type", "application/json")]
        mock_resp.read.return_value = b'{"ok": true}'

        with patch("porthole.proxy.http.client.HTTPConnection") as mock_conn_cls:
            mock_conn_cls.return_value.getresponse.return_value = mock_resp
            handler._proxy_request()

        handler.send_response.assert_called_once_with(200)
        handler.wfile.write.assert_called_once_with(b'{"ok": true}')
