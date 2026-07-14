"""Inspect a Pi-style JSONL session file without changing it."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class SessionReport:
    entries: int
    roles: tuple[tuple[str, int], ...]
    compactions: int


def inspect_session_jsonl(path: Path | str) -> SessionReport:
    """Count record kinds and message roles; never execute file content."""
    session_path = Path(path)
    roles: Counter[str] = Counter()
    entries = 0
    compactions = 0
    with session_path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid JSON on line {line_number}") from error
            if not isinstance(record, dict):
                raise ValueError(f"record on line {line_number} is not an object")
            entries += 1
            if record.get("type") == "compaction":
                compactions += 1
            message = record.get("message")
            if isinstance(message, dict) and isinstance(message.get("role"), str):
                roles[message["role"]] += 1
    return SessionReport(entries, tuple(sorted(roles.items())), compactions)
