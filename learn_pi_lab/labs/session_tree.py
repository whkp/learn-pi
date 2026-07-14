"""A course-local transcript-tree teaching model, not Pi's JSONL v3 session format."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class TranscriptEntry:
    """One simple, immutable entry in a teaching transcript tree."""

    id: str
    parent_id: str | None
    text: str


class MalformedTranscript(ValueError):
    """Raised when simple course transcript entries do not form a valid tree."""


class UnknownTranscriptEntry(KeyError):
    """A structured error for a requested leaf ID that is absent from a tree."""

    def __init__(self, entry_id: str) -> None:
        self.entry_id = entry_id
        super().__init__(entry_id)

    def __str__(self) -> str:
        return f"unknown transcript entry: {self.entry_id!r}"


class TranscriptTree:
    """An immutable snapshot of validated course transcript entries."""

    def __init__(self, entries: Iterable[TranscriptEntry]) -> None:
        self._entries = tuple(entries)
        self._entries_by_id: dict[str, TranscriptEntry] = {}
        self.validate()

    def validate(self) -> None:
        """Eagerly validate IDs, parents, and acyclic ancestry."""
        entries_by_id: dict[str, TranscriptEntry] = {}

        for entry in self._entries:
            if not isinstance(entry, TranscriptEntry):
                raise MalformedTranscript("entries must be TranscriptEntry values")
            if not entry.id:
                raise MalformedTranscript("empty id is not allowed")
            if entry.id in entries_by_id:
                raise MalformedTranscript(f"duplicate id: {entry.id!r}")
            entries_by_id[entry.id] = entry

        for entry in self._entries:
            if entry.parent_id == entry.id:
                raise MalformedTranscript(f"self parent is not allowed: {entry.id!r}")
            if entry.parent_id is not None and entry.parent_id not in entries_by_id:
                raise MalformedTranscript(
                    f"dangling parent for {entry.id!r}: {entry.parent_id!r}"
                )

        for entry in self._entries:
            visited: set[str] = set()
            current = entry
            while current.parent_id is not None:
                if current.id in visited:
                    raise MalformedTranscript(f"cycle detected involving entry {current.id!r}")
                visited.add(current.id)
                current = entries_by_id[current.parent_id]

        self._entries_by_id = entries_by_id

    def path_to(self, leaf_id: str) -> tuple[TranscriptEntry, ...]:
        """Return the root-to-leaf branch for one known teaching entry ID."""
        try:
            current = self._entries_by_id[leaf_id]
        except KeyError as error:
            raise UnknownTranscriptEntry(leaf_id) from error

        branch: list[TranscriptEntry] = []
        while True:
            branch.append(current)
            if current.parent_id is None:
                break
            current = self._entries_by_id[current.parent_id]
        return tuple(reversed(branch))

    def branch_ids(self) -> tuple[str, ...]:
        """Return immutable entry IDs in the snapshot's input order."""
        return tuple(entry.id for entry in self._entries)


SESSION_TREE_FIXTURE = (
    TranscriptEntry("root", None, "Root"),
    TranscriptEntry("child", "root", "Child"),
    TranscriptEntry("leaf", "child", "Leaf"),
    TranscriptEntry("sibling", "root", "Sibling"),
)
