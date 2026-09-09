"""Find broken relative Markdown links without following network URLs.

Heading anchors use a documented GitHub-style subset: ATX heading text is
lowercased, whitespace becomes ``-``, and punctuation other than ``-`` and
``_`` is removed. Repeated heading slugs gain ``-1``, ``-2``, and so on.
Inline-link destinations support balanced parentheses; a ``#fragment`` is
recognized only when it occurs outside those parentheses.
Relative local destinations must resolve within the checked repository.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from urllib.parse import unquote


FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
INLINE_CODE = re.compile(r"`[^`\n]*`")
HEADING = re.compile(r"^\s{0,3}#{1,6}(?:[ \t]+|$)(.*)$")
TRAILING_HEADING_MARKERS = re.compile(r"[ \t]+#+[ \t]*$")


@dataclass
class ValidationResult:
    """A reusable result shape for command-line validation scripts."""

    errors: list[str]


def find_broken_links(root: Path | str) -> list[str]:
    """Return missing targets referenced by relative local Markdown links."""
    repository = Path(root).resolve()
    errors: list[str] = []

    for markdown_file in sorted(_markdown_files(repository)):
        contents = markdown_file.read_text(encoding="utf-8")
        for target in _link_targets(contents):
            if _ignore_target(target):
                continue

            target_path, fragment = _target_path(markdown_file, target)
            if target_path is None:
                continue

            relative_markdown_path = markdown_file.relative_to(repository).as_posix()
            if not _is_within_repository(target_path, repository):
                errors.append(f"{relative_markdown_path}: {target}")
            elif not target_path.exists():
                errors.append(f"{relative_markdown_path}: {target}")
            elif fragment and not _has_heading_anchor(target_path, fragment):
                errors.append(f"{relative_markdown_path}: {target}")
    return errors


IGNORED_DIRS = frozenset(
    {".git", ".workbuddy", "node_modules", "dist", "src", "book", "__pycache__", ".venv"}
)


def _markdown_files(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return [
        path
        for path in root.rglob("*.md")
        if path.is_file()
        and not IGNORED_DIRS.intersection(path.parts)
    ]


def _link_targets(contents: str) -> list[str]:
    targets: list[str] = []
    in_fence: str | None = None

    for original_line in contents.splitlines():
        fence_match = FENCE.match(original_line)
        if in_fence is not None:
            if fence_match and fence_match.group(1)[0] == in_fence:
                in_fence = None
            continue
        if fence_match:
            in_fence = fence_match.group(1)[0]
            continue

        line = INLINE_CODE.sub("", original_line)
        targets.extend(_line_link_targets(line))
    return targets


def _line_link_targets(line: str) -> list[str]:
    targets: list[str] = []
    position = 0

    while position < len(line):
        opening_bracket = line.find("[", position)
        if opening_bracket == -1:
            break
        if opening_bracket > 0 and line[opening_bracket - 1] == "!":
            position = opening_bracket + 1
            continue

        closing_bracket = _matching_bracket(line, opening_bracket)
        if closing_bracket is None or closing_bracket + 1 >= len(line):
            position = opening_bracket + 1
            continue
        if line[closing_bracket + 1] != "(":
            position = opening_bracket + 1
            continue

        closing_parenthesis = _matching_parenthesis(line, closing_bracket + 1)
        if closing_parenthesis is None:
            position = closing_bracket + 1
            continue

        label = line[opening_bracket + 1 : closing_bracket].lstrip()
        if not label.startswith("!"):
            destination = _destination(line[closing_bracket + 2 : closing_parenthesis])
            if destination:
                targets.append(destination)
        position = closing_parenthesis + 1

    return targets


def _matching_bracket(line: str, opening_bracket: int) -> int | None:
    depth = 1
    position = opening_bracket + 1

    while position < len(line):
        character = line[position]
        if character == "\\":
            position += 2
            continue
        if character == "[":
            depth += 1
        elif character == "]":
            depth -= 1
            if depth == 0:
                return position
        position += 1
    return None


def _matching_parenthesis(line: str, opening_parenthesis: int) -> int | None:
    depth = 1
    position = opening_parenthesis + 1

    while position < len(line):
        character = line[position]
        if character == "\\":
            position += 2
            continue
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth == 0:
                return position
        position += 1
    return None


def _destination(raw_destination: str) -> str:
    destination = raw_destination.strip()
    if destination.startswith("<") and ">" in destination:
        return destination[1 : destination.index(">")]
    return _without_quoted_title(destination)


def _without_quoted_title(destination: str) -> str:
    depth = 0
    for position, character in enumerate(destination):
        if character == "(":
            depth += 1
        elif character == ")" and depth:
            depth -= 1
        elif character.isspace() and depth == 0:
            title = destination[position:].strip()
            if len(title) >= 2 and title[0] in "\"'" and title[-1] == title[0]:
                return destination[:position].rstrip()
    return destination


def _ignore_target(target: str) -> bool:
    lower_target = target.lower()
    return (
        not target
        or target.startswith("/")
        or lower_target.startswith(("http://", "https://", "mailto:"))
        or bool(re.match(r"^[a-z][a-z0-9+.-]*:", lower_target))
    )


def _target_path(markdown_file: Path, target: str) -> tuple[Path | None, str | None]:
    path_part, fragment, has_fragment = _split_outside_parentheses(target, "#")
    path_part, _, _ = _split_outside_parentheses(path_part, "?")
    if not path_part:
        return markdown_file.resolve(), fragment if has_fragment else None
    return (markdown_file.parent / unquote(path_part)).resolve(), fragment if has_fragment else None


def _is_within_repository(path: Path, repository: Path) -> bool:
    try:
        path.relative_to(repository)
    except ValueError:
        return False
    return True


def _split_outside_parentheses(value: str, delimiter: str) -> tuple[str, str, bool]:
    depth = 0
    position = 0

    while position < len(value):
        character = value[position]
        if character == "\\":
            position += 2
            continue
        if character == "(":
            depth += 1
        elif character == ")" and depth:
            depth -= 1
        elif character == delimiter and depth == 0:
            return value[:position], value[position + 1 :], True
        position += 1
    return value, "", False


def _has_heading_anchor(path: Path, fragment: str) -> bool:
    if path.suffix.lower() != ".md":
        return False
    try:
        contents = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return unquote(fragment).lower() in _heading_slugs(contents)


def _heading_slugs(contents: str) -> set[str]:
    slugs: set[str] = set()
    counts: dict[str, int] = {}
    in_fence: str | None = None

    for line in contents.splitlines():
        fence_match = FENCE.match(line)
        if in_fence is not None:
            if fence_match and fence_match.group(1)[0] == in_fence:
                in_fence = None
            continue
        if fence_match:
            in_fence = fence_match.group(1)[0]
            continue

        heading_match = HEADING.match(line)
        if not heading_match:
            continue
        slug = _heading_slug(TRAILING_HEADING_MARKERS.sub("", heading_match.group(1)))
        if not slug:
            continue
        duplicate_count = counts.get(slug, 0)
        counts[slug] = duplicate_count + 1
        slugs.add(slug if duplicate_count == 0 else f"{slug}-{duplicate_count}")
    return slugs


def _heading_slug(heading: str) -> str:
    """Return the supported GitHub-style slug for one ATX heading."""
    characters: list[str] = []
    for character in heading.lower():
        if character.isspace():
            characters.append("-")
        elif character.isalnum() or character in "-_":
            characters.append(character)
    return "".join(characters).strip("-")


def main() -> int:
    """Run the local Markdown-link check for this repository."""
    root = Path(__file__).resolve().parents[1]
    errors = find_broken_links(root)
    if errors:
        print("\n".join(errors))
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
