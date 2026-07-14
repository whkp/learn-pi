"""A course-local extension-event model, not Pi's ``pi.on`` or ExtensionAPI.

The model demonstrates deterministic callback ordering and error isolation.  It is
deliberately smaller than Pi's extension system and does not establish API parity.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType


EventHandler = Callable[[object], object]


@dataclass(frozen=True)
class EventOutcome:
    """The result of one handler invocation during a teaching event."""

    status: str
    handler_index: int
    value: object | None = None
    error: str | None = None


class Subscription:
    """An idempotent handle that removes only its own registration."""

    def __init__(self, bus: LessonEventBus, event: str, registration_id: int) -> None:
        self._bus = bus
        self._event = event
        self._registration_id = registration_id
        self._active = True

    def unsubscribe(self) -> None:
        """Remove this handler once; future calls cannot affect newer handlers."""
        if not self._active:
            return
        self._bus._remove(self._event, self._registration_id)
        self._active = False


class LessonEventBus:
    """A deterministic, single-threaded bus for course exercises."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[tuple[int, EventHandler]]] = {}
        self._next_registration_id = 0

    def on(self, event: str, callback: EventHandler) -> Subscription:
        """Register one callable handler and return its isolated subscription."""
        if not isinstance(event, str) or not event.strip():
            raise ValueError("event name must be a nonblank string")
        if not callable(callback):
            raise TypeError("event handler must be callable")

        registration_id = self._next_registration_id
        self._next_registration_id += 1
        self._handlers.setdefault(event, []).append((registration_id, callback))
        return Subscription(self, event, registration_id)

    def emit(self, event: str, payload: Mapping[str, object]) -> tuple[EventOutcome, ...]:
        """Run an immutable payload snapshot through handlers in registration order.

        Ordinary ``Exception`` failures become data so later handlers can run.
        ``KeyboardInterrupt`` and ``SystemExit`` intentionally inherit from
        ``BaseException`` and are not intercepted.
        """
        if not isinstance(event, str) or not event.strip():
            raise ValueError("event name must be a nonblank string")
        if not isinstance(payload, Mapping):
            raise TypeError("event payload must be a mapping")

        snapshot = _freeze_value(payload)
        handlers = tuple(self._handlers.get(event, ()))
        outcomes: list[EventOutcome] = []
        for handler_index, (_registration_id, callback) in enumerate(handlers):
            try:
                outcomes.append(
                    EventOutcome(
                        status="ok",
                        handler_index=handler_index,
                        value=callback(snapshot),
                    )
                )
            except Exception as error:
                outcomes.append(
                    EventOutcome(
                        status="error",
                        handler_index=handler_index,
                        error=f"{type(error).__name__}: {error}",
                    )
                )
        return tuple(outcomes)

    def _remove(self, event: str, registration_id: int) -> None:
        """Remove one matching registration without changing relative order."""
        handlers = self._handlers.get(event)
        if handlers is None:
            return
        self._handlers[event] = [
            item for item in handlers if item[0] != registration_id
        ]


def _freeze_value(value: object) -> object:
    """Snapshot only values the teaching bus can make safely immutable.

    The course model intentionally accepts JSON-like values plus bytes-like
    buffers.  Rejecting arbitrary custom objects is safer than claiming a
    deep-freeze guarantee that Python cannot provide for them generically.
    """
    if value is None or isinstance(value, (bool, int, float, str, bytes)):
        return value
    if isinstance(value, (bytearray, memoryview)):
        return bytes(value)
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("event payload mapping keys must be strings")
        return MappingProxyType({key: _freeze_value(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze_value(item) for item in value)
    if isinstance(value, frozenset):
        return frozenset(_freeze_value(item) for item in value)
    raise TypeError(
        "event payload values must be snapshot-safe JSON-like values, bytes, or bytearray"
    )
