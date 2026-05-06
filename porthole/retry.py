"""Retry middleware for upstream request failures."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from porthole.logger import get_logger

logger = get_logger("porthole.retry")


@dataclass
class RetryConfig:
    max_attempts: int = 3
    backoff_base_ms: float = 100.0
    backoff_multiplier: float = 2.0
    retryable_status_codes: list[int] = field(default_factory=lambda: [502, 503, 504])

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.backoff_base_ms < 0:
            raise ValueError("backoff_base_ms must be >= 0")
        if self.backoff_multiplier < 1.0:
            raise ValueError("backoff_multiplier must be >= 1.0")

    def delay_for_attempt(self, attempt: int) -> float:
        """Return sleep time in seconds for a given attempt (0-indexed)."""
        if attempt == 0:
            return 0.0
        return (self.backoff_base_ms * (self.backoff_multiplier ** (attempt - 1))) / 1000.0


def retry_proxy(
    next_handler: Callable[[object, object], int],
    cfg: RetryConfig | None = None,
) -> Callable[[object, object], int]:
    """Wrap *next_handler* with retry logic.

    The wrapped callable has the same signature as the handlers used
    throughout porthole: ``(request_handler, parsed_path) -> status_code``.
    """
    if cfg is None:
        cfg = RetryConfig()

    def handler(request_handler: object, parsed_path: object) -> int:
        last_status = 500
        for attempt in range(cfg.max_attempts):
            delay = cfg.delay_for_attempt(attempt)
            if delay > 0:
                logger.debug(
                    "retry attempt=%d sleeping=%.3fs", attempt, delay
                )
                time.sleep(delay)
            last_status = next_handler(request_handler, parsed_path)
            if last_status not in cfg.retryable_status_codes:
                return last_status
            logger.warning(
                "retryable status=%d attempt=%d/%d",
                last_status,
                attempt + 1,
                cfg.max_attempts,
            )
        return last_status

    return handler
