"""A course-local compaction teaching model, NOT Pi token counting or LLM compaction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


TEXT_PREVIEW_LIMIT = 40


@dataclass(frozen=True)
class TranscriptUnit:
    """One immutable teaching transcript unit with an optional paired operation ID."""

    id: str
    text: str
    pair_id: str | None = None
    role: str = "message"


@dataclass(frozen=True)
class CompactionSummary:
    """Deterministic local metadata for units selected for summary."""

    count: int
    unit_ids: tuple[str, ...]
    roles: tuple[str, ...]
    text_preview: tuple[str, ...]


@dataclass(frozen=True)
class CompactionPlan:
    """An immutable split between newest kept units and summarized older units."""

    kept: tuple[TranscriptUnit, ...]
    summarized: tuple[TranscriptUnit, ...]
    summary: CompactionSummary


class MalformedPair(ValueError):
    """Raised when a course pair ID does not identify exactly two units."""


def choose_cut(entries: Iterable[TranscriptUnit], keep_units: int) -> tuple[TranscriptUnit, ...]:
    """Keep a newest suffix, expanding it only when its boundary splits a pair.

    A zero budget intentionally retains no units, including complete pairs.
    """
    units = tuple(entries)
    _validate_keep_units(keep_units)
    pair_indices = _pair_indices(units)
    start = max(0, len(units) - keep_units)

    while True:
        expanded_start = start
        for indices in pair_indices.values():
            includes_pair_unit = any(index >= start for index in indices)
            excludes_pair_unit = any(index < start for index in indices)
            if includes_pair_unit and excludes_pair_unit:
                expanded_start = min(expanded_start, min(indices))
        if expanded_start == start:
            break
        start = expanded_start

    return units[start:]


def make_summary(entries: Iterable[TranscriptUnit]) -> CompactionSummary:
    """Return bounded, deterministic structured metadata without external calls."""
    units = tuple(entries)
    return CompactionSummary(
        count=len(units),
        unit_ids=tuple(unit.id for unit in units),
        roles=tuple(unit.role for unit in units),
        text_preview=tuple(unit.text[:TEXT_PREVIEW_LIMIT] for unit in units),
    )


def compact(entries: Iterable[TranscriptUnit], keep_units: int) -> CompactionPlan:
    """Split entries into a kept suffix and its ordered summarized complement."""
    units = tuple(entries)
    kept = choose_cut(units, keep_units)
    summarized = units[: len(units) - len(kept)]
    return CompactionPlan(
        kept=kept,
        summarized=summarized,
        summary=make_summary(summarized),
    )


def _validate_keep_units(keep_units: int) -> None:
    if not isinstance(keep_units, int) or keep_units < 0:
        raise ValueError("keep_units must be a nonnegative integer")


def _pair_indices(units: tuple[TranscriptUnit, ...]) -> dict[str, tuple[int, int]]:
    grouped: dict[str, list[int]] = {}
    for index, unit in enumerate(units):
        if unit.pair_id is not None:
            grouped.setdefault(unit.pair_id, []).append(index)

    pairs: dict[str, tuple[int, int]] = {}
    for pair_id, indices in grouped.items():
        if len(indices) != 2:
            raise MalformedPair(
                f"pair_id {pair_id!r} must identify exactly two units, found {len(indices)}"
            )
        pairs[pair_id] = (indices[0], indices[1])
    return pairs


COMPACTION_FIXTURE = (
    TranscriptUnit("intro", "Older context"),
    TranscriptUnit("call", "Call tool", pair_id="tool-1", role="tool_call"),
    TranscriptUnit("result", "Tool result", pair_id="tool-1", role="tool_result"),
    TranscriptUnit("latest", "Latest context"),
)
