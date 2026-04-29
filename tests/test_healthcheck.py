"""Tests for porthole.healthcheck and porthole.health_command."""

import io
import textwrap
from unittest.mock import MagicMock, patch

import pytest

from porthole.config import ServiceConfig
from porthole.healthcheck import HealthStatus, check_service, check_all
from porthole.health_command import run_health


# ---------------------------------------------------------------------------
# HealthStatus.__str__
# ---------------------------------------------------------------------------

def test_health_status_ok_str():
    s = HealthStatus(service_name="api", target="http://localhost:8000", reachable=True, status_code=200)
    assert "[OK]" in str(s)
    assert "api" in str(s)
    assert "200" in str(s)


def test_health_status_err_str():
    s = HealthStatus(service_name="db", target="http://localhost:5432", reachable=False, error="refused")
    assert "[ERR]" in str(s)
    assert "refused" in str(s)


# ---------------------------------------------------------------------------
# check_service — mocked HTTP
# ---------------------------------------------------------------------------

def _make_service(name="svc", target="http://localhost:9000"):
    return ServiceConfig(name=name, host=f"{name}.local", target=target)


def test_check_service_success():
    mock_resp = MagicMock(status=200)
    mock_conn = MagicMock()
    mock_conn.getresponse.return_value = mock_resp

    with patch("porthole.healthcheck.http.client.HTTPConnection", return_value=mock_conn):
        result = check_service(_make_service())

    assert result.reachable is True
    assert result.status_code == 200


def test_check_service_connection_refused():
    mock_conn = MagicMock()
    mock_conn.request.side_effect = ConnectionRefusedError("refused")

    with patch("porthole.healthcheck.http.client.HTTPConnection", return_value=mock_conn):
        result = check_service(_make_service())

    assert result.reachable is False
    assert result.error is not None


def test_check_all_returns_one_per_service():
    services = [_make_service("a", "http://localhost:8001"), _make_service("b", "http://localhost:8002")]
    mock_resp = MagicMock(status=204)
    mock_conn = MagicMock()
    mock_conn.getresponse.return_value = mock_resp

    with patch("porthole.healthcheck.http.client.HTTPConnection", return_value=mock_conn):
        results = check_all(services)

    assert len(results) == 2
    assert all(r.reachable for r in results)


# ---------------------------------------------------------------------------
# run_health command
# ---------------------------------------------------------------------------

def test_run_health_missing_config():
    out, err = io.StringIO(), io.StringIO()
    code = run_health("/nonexistent/porthole.toml", output=out, err_output=err)
    assert code == 2
    assert "not found" in err.getvalue()


def test_run_health_all_ok(tmp_path):
    cfg_file = tmp_path / "porthole.toml"
    cfg_file.write_text(textwrap.dedent("""
        [porthole]
        port = 8080

        [[services]]
        name = "web"
        host = "web.local"
        target = "http://localhost:3000"
    """))

    mock_resp = MagicMock(status=200)
    mock_conn = MagicMock()
    mock_conn.getresponse.return_value = mock_resp

    out, err = io.StringIO(), io.StringIO()
    with patch("porthole.healthcheck.http.client.HTTPConnection", return_value=mock_conn):
        code = run_health(str(cfg_file), output=out, err_output=err)

    assert code == 0
    assert "[OK]" in out.getvalue()
