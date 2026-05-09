"""Mock response module: serve static/canned responses for a service without
hitting a real upstream.  Useful for local development when a dependency is
not running."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class MockResponseConfig:
    """Configuration for a single mocked service endpoint."""

    status: int = 200
    body: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    content_type: str = "application/json"

    def __post_init__(self) -> None:
        if not (100 <= self.status <= 599):
            raise ValueError(f"status must be 100-599, got {self.status}")
        if not self.content_type:
            raise ValueError("content_type must not be empty")

    # ------------------------------------------------------------------
    # Convenience constructors
    # ------------------------------------------------------------------

    @classmethod
    def json(cls, payload: Any, status: int = 200) -> "MockResponseConfig":
        """Build a config that returns *payload* serialised as JSON."""
        return cls(
            status=status,
            body=json.dumps(payload),
            content_type="application/json",
        )

    @classmethod
    def text(cls, message: str, status: int = 200) -> "MockResponseConfig":
        """Build a config that returns plain text."""
        return cls(
            status=status,
            body=message,
            content_type="text/plain",
        )


@dataclass
class MockRegistry:
    """Maps service names to their MockResponseConfig."""

    _mocks: Dict[str, MockResponseConfig] = field(default_factory=dict)

    def register(self, service: str, cfg: MockResponseConfig) -> None:
        if not service:
            raise ValueError("service name must not be empty")
        self._mocks[service] = cfg

    def get(self, service: str) -> Optional[MockResponseConfig]:
        return self._mocks.get(service)

    def all_services(self) -> Dict[str, MockResponseConfig]:
        return dict(self._mocks)

    def remove(self, service: str) -> bool:
        if service in self._mocks:
            del self._mocks[service]
            return True
        return False

    def clear(self) -> None:
        self._mocks.clear()
