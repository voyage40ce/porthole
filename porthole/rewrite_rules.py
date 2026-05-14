"""URL path rewrite rules for proxied requests."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class RewriteRule:
    """A single find-and-replace rule applied to the request path."""

    pattern: str
    replacement: str
    _compiled: re.Pattern = field(init=False, repr=False)

    def __post_init__(self) -> None:
        try:
            self._compiled = re.compile(self.pattern)
        except re.error as exc:
            raise ValueError(f"Invalid regex pattern {self.pattern!r}: {exc}") from exc

    def apply(self, path: str) -> str:
        """Return *path* with the first matching occurrence rewritten."""
        return self._compiled.sub(self.replacement, path, count=1)

    def matches(self, path: str) -> bool:
        return bool(self._compiled.search(path))


@dataclass
class RewriteRulesConfig:
    """Ordered list of rewrite rules for one service."""

    rules: List[RewriteRule] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.rules:
            raise ValueError("RewriteRulesConfig requires at least one rule.")


class RewriteRulesRegistry:
    """Holds per-service rewrite rule configurations."""

    def __init__(self) -> None:
        self._configs: Dict[str, RewriteRulesConfig] = {}

    def register(self, service: str, config: RewriteRulesConfig) -> None:
        self._configs[service] = config

    def get(self, service: str) -> Optional[RewriteRulesConfig]:
        return self._configs.get(service)

    def services(self) -> List[str]:
        return list(self._configs.keys())

    def apply(self, service: str, path: str) -> Tuple[str, bool]:
        """Apply the first matching rule for *service* to *path*.

        Returns ``(new_path, was_rewritten)``.
        """
        cfg = self._configs.get(service)
        if cfg is None:
            return path, False
        for rule in cfg.rules:
            if rule.matches(path):
                return rule.apply(path), True
        return path, False
