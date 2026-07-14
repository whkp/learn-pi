"""Dependency-injected retry logic for an offline reliability lesson."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TypeVar


T = TypeVar("T")


class RetryExhausted(RuntimeError):
    """A bounded error that deliberately omits an operation's exception text."""

    def __init__(self, attempts: int, error_type: str) -> None:
        self.attempts = attempts
        self.error_type = error_type
        super().__init__(f"operation failed after {attempts} attempts ({error_type})")


@dataclass(frozen=True)
class RetryResult:
    """A successful result with deterministic retry metadata."""

    value: T
    attempts: int
    delays: tuple[float, ...]


def retry(
    operation: Callable[[], T],
    *,
    attempts: int,
    base_delay: float,
    sleep: Callable[[float], None] | None = None,
) -> RetryResult[T]:
    """Run an operation with exponential backoff and no hidden real sleeping."""
    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts < 1:
        raise ValueError("attempts must be a positive integer")
    if isinstance(base_delay, bool) or not isinstance(base_delay, (int, float)) or base_delay < 0:
        raise ValueError("base delay must be a non-negative number")
    if not callable(operation):
        raise TypeError("operation must be callable")
    if sleep is not None and not callable(sleep):
        raise TypeError("sleep must be callable")

    delays: list[float] = []
    for current_attempt in range(1, attempts + 1):
        try:
            return RetryResult(operation(), current_attempt, tuple(delays))
        except Exception as error:
            if current_attempt == attempts:
                raise RetryExhausted(current_attempt, type(error).__name__) from error
            delay = float(base_delay) * (2 ** (current_attempt - 1))
            delays.append(delay)
            if sleep is not None:
                sleep(delay)

    raise AssertionError("unreachable")
