"""CLI sub-command: display circuit-breaker states for all known services."""
from __future__ import annotations

from porthole.circuit_breaker import CircuitBreakerRegistry, CircuitState
from porthole.config import PortholeConfig

_STATE_SYMBOL = {
    CircuitState.CLOSED: "✔ closed",
    CircuitState.OPEN: "✖ open",
    CircuitState.HALF_OPEN: "~ half-open",
}


def _header() -> str:
    return f"{'SERVICE':<25} {'STATE':<14} {'FAILURES':>8}  {'SUCCESSES':>9}"


def _row(name: str, state: CircuitState, failures: int, successes: int) -> str:
    return f"{name:<25} {_STATE_SYMBOL[state]:<14} {failures:>8}  {successes:>9}"


def run_circuit_breaker(
    config: PortholeConfig,
    registry: CircuitBreakerRegistry,
) -> None:
    """Print a table of circuit-breaker states for every configured service."""
    service_names = [s.name for s in config.services]

    if not service_names:
        print("No services configured.")
        return

    print(_header())
    print("-" * 62)

    for name in service_names:
        breaker = registry._get(name)  # noqa: SLF001
        print(
            _row(
                name,
                breaker.state,
                breaker.failure_count,
                breaker.success_count,
            )
        )
