"""Make read-only review decisions; this project never executes a command."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass(frozen=True)
class ReviewPolicy:
    root: Path


@dataclass(frozen=True)
class ReviewDecision:
    allowed: bool
    normalized_target: str | None
    reason: str


def review_request(policy: ReviewPolicy, intent: str, target: str) -> ReviewDecision:
    """Approve only known read-only intents whose relative target stays in root."""
    if intent not in {"read", "search", "list"}:
        return ReviewDecision(False, None, "intent is not read-only")
    if not isinstance(target, str) or not target or "\x00" in target:
        return ReviewDecision(False, None, "target must be non-empty text")
    candidate = PurePosixPath(target)
    if candidate.is_absolute() or ".." in candidate.parts:
        return ReviewDecision(False, None, "target escapes the review root")
    root = policy.root.resolve()
    return ReviewDecision(True, str(root / Path(*candidate.parts)), "allowed")
