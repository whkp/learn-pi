"""A course-local agent-loop teaching model, not a Pi SDK, binding, or port."""

from __future__ import annotations

from collections.abc import Mapping as MappingABC
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Callable, Mapping, Sequence


ToolExecutor = Callable[[Mapping[str, object]], object]


@dataclass(frozen=True)
class ToolRequest:
    """A scripted request with a nonempty string name and string-keyed mapping input.

    Inputs are snapshotted into immutable values when the request is constructed.
    Invalid shapes remain representable so the runner can report a structured error.
    """

    name: object
    arguments: object = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _freeze_value(self.name))
        object.__setattr__(self, "arguments", _freeze_value(self.arguments))


@dataclass(frozen=True)
class FinalText:
    """A scripted final response that ends the teaching loop."""

    text: str


@dataclass(frozen=True)
class RunError:
    """A structured, deterministic failure recorded by a teaching run."""

    code: str
    message: str
    turn: int
    tool_name: str | None = None


@dataclass(frozen=True)
class RunTrace:
    """The observable result of a deterministic scripted teaching run."""

    prompt: str
    final_text: str | None
    tool_names: tuple[str, ...]
    turns: int
    errors: tuple[RunError, ...]


ScriptedStep = FinalText | ToolRequest | str


class ScriptedModel:
    """Return prewritten final-text and tool-request steps in sequence."""

    def __init__(self, steps: Sequence[ScriptedStep]) -> None:
        self._steps = tuple(self._snapshot_step(step) for step in steps)
        self._position = 0

    @staticmethod
    def _snapshot_step(step: ScriptedStep) -> ScriptedStep:
        if isinstance(step, ToolRequest):
            return ToolRequest(step.name, step.arguments)
        if isinstance(step, FinalText):
            return FinalText(step.text)
        return _freeze_value(step)  # type: ignore[return-value]

    @classmethod
    def tool_then_text(
        cls,
        tool_name: str,
        arguments: Mapping[str, object],
        final_text: str,
    ) -> ScriptedModel:
        """Build the common one-tool-then-final scripted exchange."""
        return cls((ToolRequest(tool_name, dict(arguments)), FinalText(final_text)))

    def next_step(self, prompt: str) -> ScriptedStep | None:
        """Return the next fixed step; the prompt is retained by the trace."""
        del prompt
        if self._position >= len(self._steps):
            return None
        step = self._steps[self._position]
        self._position += 1
        return step


def run_scripted_loop(
    prompt: str,
    model: ScriptedModel,
    tools: Mapping[str, ToolExecutor],
    *,
    max_turns: int = 8,
) -> RunTrace:
    """Run scripted replies without performing network, shell, or Pi operations."""
    tool_names: list[str] = []
    errors: list[RunError] = []

    if max_turns < 1:
        errors.append(
            RunError(
                code="invalid_max_turns",
                message="max_turns must be at least 1.",
                turn=0,
            )
        )
        return _trace(prompt, None, tool_names, 0, errors)

    for turn in range(1, max_turns + 1):
        step = model.next_step(prompt)
        if step is None:
            errors.append(
                RunError(
                    code="script_exhausted",
                    message="The scripted model ended without final text.",
                    turn=turn - 1,
                )
            )
            return _trace(prompt, None, tool_names, turn - 1, errors)

        if isinstance(step, str):
            return _trace(prompt, step, tool_names, turn, errors)

        if isinstance(step, FinalText):
            return _trace(prompt, step.text, tool_names, turn, errors)

        if not isinstance(step, ToolRequest):
            errors.append(
                RunError(
                    code="invalid_scripted_step",
                    message="The scripted model returned an unsupported step.",
                    turn=turn,
                )
            )
            return _trace(prompt, None, tool_names, turn, errors)

        if not _is_valid_tool_request(step):
            errors.append(
                RunError(
                    code="invalid_scripted_step",
                    message=(
                        "Tool requests require a nonempty string name and "
                        "a mapping with string keys."
                    ),
                    turn=turn,
                )
            )
            return _trace(prompt, None, tool_names, turn, errors)

        tool_names.append(step.name)
        executor = tools.get(step.name)
        if executor is None:
            errors.append(
                RunError(
                    code="unknown_tool",
                    message=f"No injected executor is available for tool '{step.name}'.",
                    turn=turn,
                    tool_name=step.name,
                )
            )
            return _trace(prompt, None, tool_names, turn, errors)

        try:
            executor(dict(step.arguments))
        except Exception as error:
            errors.append(
                RunError(
                    code="tool_execution_failed",
                    message=f"Tool '{step.name}' raised {type(error).__name__}: {error}",
                    turn=turn,
                    tool_name=step.name,
                )
            )
            return _trace(prompt, None, tool_names, turn, errors)

    errors.append(
        RunError(
            code="max_turns_exceeded",
            message=f"The scripted loop did not reach final text within {max_turns} turns.",
            turn=max_turns,
        )
    )
    return _trace(prompt, None, tool_names, max_turns, errors)


def _freeze_value(value: object) -> object:
    """Recursively snapshot mutable script values without executing anything."""
    if isinstance(value, MappingABC):
        return MappingProxyType({key: _freeze_value(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze_value(item) for item in value)
    return value


def _is_valid_tool_request(step: ToolRequest) -> bool:
    """Check the documented request shape before using it as a tool lookup key."""
    return (
        isinstance(step.name, str)
        and bool(step.name)
        and isinstance(step.arguments, MappingABC)
        and all(isinstance(key, str) for key in step.arguments)
    )


def _trace(
    prompt: str,
    final_text: str | None,
    tool_names: list[str],
    turns: int,
    errors: list[RunError],
) -> RunTrace:
    """Freeze public trace collections at the course-lab boundary."""
    return RunTrace(prompt, final_text, tuple(tool_names), turns, tuple(errors))
