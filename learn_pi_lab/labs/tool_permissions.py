"""A course-local permission teaching model, not Pi's permission API."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable


_READ_ONLY_COMMANDS = frozenset({"ls", "cat", "grep"})
_SHELL_OPERATORS = frozenset(";|&><$`")
_COMMAND_SHAPE_REASON = "command_must_be_a_single_allowlisted_token"


@dataclass(frozen=True)
class CommandRequest:
    """An immutable command token and immutable sequence of requested paths."""

    command: str
    paths: tuple[Path | str, ...] = ()

    def __post_init__(self) -> None:
        raw_paths = self.paths
        if isinstance(raw_paths, (str, Path)):
            normalized_paths: tuple[Path | str, ...] = (raw_paths,)
        else:
            try:
                normalized_paths = tuple(raw_paths)
            except TypeError:
                normalized_paths = (raw_paths,)  # type: ignore[assignment]
        object.__setattr__(self, "paths", normalized_paths)


@dataclass(frozen=True)
class Policy:
    """A read-only allowlist rooted at one resolved course directory."""

    root: Path
    allowed_commands: frozenset[str] = _READ_ONLY_COMMANDS

    @classmethod
    def read_only(cls, root: Path) -> Policy:
        """Allow only ``ls``, ``cat``, and ``grep`` beneath ``root``."""
        return cls(root=Path(root).resolve(), allowed_commands=_READ_ONLY_COMMANDS)


@dataclass(frozen=True)
class Decision:
    """An immutable, actionable policy result for one command request."""

    allowed: bool
    reason: str
    request: CommandRequest


@dataclass(frozen=True)
class DispatchResult:
    """A policy decision plus an optional result from an injected executor."""

    decision: Decision
    result: object | None
    executed: bool


Executor = Callable[[CommandRequest], object]


def evaluate_request(request: CommandRequest, policy: Policy) -> Decision:
    """Evaluate a request without executing a command or inspecting a network."""
    token, problem = _command_token(request.command)
    if problem is not None:
        return Decision(False, problem, request)

    if token not in _READ_ONLY_COMMANDS or token not in policy.allowed_commands:
        allowed = ", ".join(sorted(policy.allowed_commands))
        return Decision(
            False,
            f"command_not_allowed: '{token}' is not in the read-only allowlist ({allowed}).",
            request,
        )

    normalized_paths: list[Path] = []
    for requested_path in request.paths:
        normalized_path, path_problem = _normalized_path(requested_path, policy.root)
        if path_problem is not None:
            return Decision(False, path_problem, request)
        assert normalized_path is not None
        normalized_paths.append(normalized_path)

    normalized_request = CommandRequest(token, tuple(normalized_paths))

    return Decision(
        True,
        f"allowed: '{token}' is in the read-only allowlist.",
        normalized_request,
    )


def dispatch_if_allowed(
    request: CommandRequest,
    policy: Policy,
    executor: Executor,
) -> DispatchResult:
    """Call an injected executor once only after the policy allows the request."""
    decision = evaluate_request(request, policy)
    if not decision.allowed:
        return DispatchResult(decision=decision, result=None, executed=False)
    return DispatchResult(decision=decision, result=executor(decision.request), executed=True)


def _command_token(command: object) -> tuple[str | None, str | None]:
    """Accept only one bare command token with no shell syntax or operands."""
    if not isinstance(command, str) or not command:
        return None, _COMMAND_SHAPE_REASON
    if any(character.isspace() or character in _SHELL_OPERATORS for character in command):
        return None, _COMMAND_SHAPE_REASON
    return command, None


def _normalized_path(requested_path: object, root: Path) -> tuple[Path | None, str | None]:
    """Resolve one requested path and reject values outside the policy root."""
    if not isinstance(requested_path, (str, Path)):
        return None, "invalid_path: paths must be strings or pathlib.Path values."

    path = Path(requested_path)
    if ".." in path.parts:
        return None, "path_outside_root: traversal components are not allowed."

    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return None, "path_outside_root: requested paths must resolve beneath the policy root."
    return resolved, None
