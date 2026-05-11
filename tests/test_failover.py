"""Tests for porthole.failover and porthole.failover_command."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from porthole.failover import FailoverConfig, FailoverRegistry
from porthole.failover_command import run_failover, _header, _row


# ---------------------------------------------------------------------------
# FailoverConfig validation
# ---------------------------------------------------------------------------

def test_config_rejects_empty_backups():
    with pytest.raises(ValueError, match="backups"):
        FailoverConfig(backups=[])


def test_config_rejects_bad_url():
    with pytest.raises(ValueError, match="http"):
        FailoverConfig(backups=["ftp://bad"])


def test_config_rejects_non_positive_timeout():
    with pytest.raises(ValueError, match="timeout"):
        FailoverConfig(backups=["http://b1"], timeout_seconds=0)


def test_config_accepts_valid():
    cfg = FailoverConfig(backups=["http://b1", "http://b2"], timeout_seconds=1.5)
    assert len(cfg.backups) == 2
    assert cfg.timeout_seconds == 1.5


# ---------------------------------------------------------------------------
# FailoverRegistry
# ---------------------------------------------------------------------------

@pytest.fixture()
def registry():
    reg = FailoverRegistry()
    cfg = FailoverConfig(backups=["http://backup1", "http://backup2"])
    reg.register("api", cfg)
    return reg


def test_get_returns_config(registry):
    cfg = registry.get("api")
    assert cfg is not None
    assert "http://backup1" in cfg.backups


def test_get_unknown_returns_none(registry):
    assert registry.get("unknown") is None


def test_active_backup_initially_none(registry):
    assert registry.active_backup("api") is None


def test_set_active_backup(registry):
    registry.set_active_backup("api", "http://backup1")
    assert registry.active_backup("api") == "http://backup1"


def test_resolve_url_uses_primary_when_healthy(registry):
    with patch("porthole.failover.urllib.request.urlopen") as mock_open:
        resp = MagicMock()
        resp.status = 200
        resp.__enter__ = lambda s: resp
        resp.__exit__ = MagicMock(return_value=False)
        mock_open.return_value = resp
        result = registry.resolve_url("api", "http://primary")
    assert result == "http://primary"
    assert registry.active_backup("api") is None


def test_resolve_url_falls_back_when_primary_fails(registry):
    call_count = [0]

    def _side_effect(url, timeout):
        call_count[0] += 1
        if "primary" in url:
            raise OSError("refused")
        resp = MagicMock()
        resp.status = 200
        resp.__enter__ = lambda s: resp
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    with patch("porthole.failover.urllib.request.urlopen", side_effect=_side_effect):
        result = registry.resolve_url("api", "http://primary")

    assert result == "http://backup1"
    assert registry.active_backup("api") == "http://backup1"


# ---------------------------------------------------------------------------
# failover_command
# ---------------------------------------------------------------------------

def test_header_contains_columns():
    h = _header()
    assert "SERVICE" in h
    assert "BACKUPS" in h
    assert "ACTIVE BACKUP" in h


def test_row_formats_values():
    r = _row("api", ["http://b1"], "(primary)")
    assert "api" in r
    assert "http://b1" in r
    assert "(primary)" in r


def test_run_failover_no_services_prints_message(capsys):
    run_failover(FailoverRegistry())
    out = capsys.readouterr().out
    assert "No failover" in out


def test_run_failover_shows_service(capsys, registry):
    run_failover(registry)
    out = capsys.readouterr().out
    assert "api" in out
    assert "backup1" in out
