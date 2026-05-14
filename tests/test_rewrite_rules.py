"""Tests for porthole.rewrite_rules and porthole.rewrite_rules_command."""
from __future__ import annotations

import pytest

from porthole.rewrite_rules import (
    RewriteRule,
    RewriteRulesConfig,
    RewriteRulesRegistry,
)
from porthole.rewrite_rules_command import run_rewrite_rules


# ---------------------------------------------------------------------------
# RewriteRule
# ---------------------------------------------------------------------------

def test_rule_rejects_invalid_regex() -> None:
    with pytest.raises(ValueError, match="Invalid regex"):
        RewriteRule(pattern="[", replacement="/new")


def test_rule_matches_path() -> None:
    rule = RewriteRule(pattern=r"^/api/v1", replacement="/api/v2")
    assert rule.matches("/api/v1/users")
    assert not rule.matches("/api/v2/users")


def test_rule_apply_substitutes_path() -> None:
    rule = RewriteRule(pattern=r"^/api/v1", replacement="/api/v2")
    assert rule.apply("/api/v1/users") == "/api/v2/users"


def test_rule_apply_only_first_occurrence() -> None:
    rule = RewriteRule(pattern=r"foo", replacement="bar")
    assert rule.apply("/foo/foo") == "/bar/foo"


def test_rule_apply_no_match_returns_original() -> None:
    rule = RewriteRule(pattern=r"^/old", replacement="/new")
    assert rule.apply("/other") == "/other"


# ---------------------------------------------------------------------------
# RewriteRulesConfig
# ---------------------------------------------------------------------------

def test_config_rejects_empty_rules() -> None:
    with pytest.raises(ValueError, match="at least one rule"):
        RewriteRulesConfig(rules=[])


def test_config_accepts_valid() -> None:
    cfg = RewriteRulesConfig(rules=[RewriteRule(r"^/old", "/new")])
    assert len(cfg.rules) == 1


# ---------------------------------------------------------------------------
# RewriteRulesRegistry
# ---------------------------------------------------------------------------

@pytest.fixture()
def registry() -> RewriteRulesRegistry:
    reg = RewriteRulesRegistry()
    reg.register(
        "svc-a",
        RewriteRulesConfig(rules=[
            RewriteRule(r"^/api/v1", "/api/v2"),
            RewriteRule(r"^/legacy", "/current"),
        ]),
    )
    return reg


def test_get_missing_returns_none(registry: RewriteRulesRegistry) -> None:
    assert registry.get("unknown") is None


def test_services_lists_registered(registry: RewriteRulesRegistry) -> None:
    assert "svc-a" in registry.services()


def test_apply_first_matching_rule(registry: RewriteRulesRegistry) -> None:
    new_path, rewritten = registry.apply("svc-a", "/api/v1/items")
    assert rewritten is True
    assert new_path == "/api/v2/items"


def test_apply_second_rule_when_first_does_not_match(registry: RewriteRulesRegistry) -> None:
    new_path, rewritten = registry.apply("svc-a", "/legacy/endpoint")
    assert rewritten is True
    assert new_path == "/current/endpoint"


def test_apply_no_match_returns_original(registry: RewriteRulesRegistry) -> None:
    new_path, rewritten = registry.apply("svc-a", "/unrelated")
    assert rewritten is False
    assert new_path == "/unrelated"


def test_apply_unknown_service_returns_original(registry: RewriteRulesRegistry) -> None:
    new_path, rewritten = registry.apply("ghost", "/api/v1/x")
    assert rewritten is False
    assert new_path == "/api/v1/x"


# ---------------------------------------------------------------------------
# run_rewrite_rules command
# ---------------------------------------------------------------------------

def test_run_rewrite_rules_no_services_prints_message(capsys: pytest.CaptureFixture) -> None:
    run_rewrite_rules(RewriteRulesRegistry())
    out = capsys.readouterr().out
    assert "No rewrite rules" in out


def test_run_rewrite_rules_shows_service(capsys: pytest.CaptureFixture, registry: RewriteRulesRegistry) -> None:
    run_rewrite_rules(registry)
    out = capsys.readouterr().out
    assert "svc-a" in out
    assert "/api/v2" in out
    assert "/current" in out
