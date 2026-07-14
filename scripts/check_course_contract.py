"""Validate the offline Learn Pi course's pinned source and chapter contract."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


BASELINE_MARKER = (
    "<!-- pi-baseline: version=0.75.3 "
    "commit=144b93861f339ce353531f6873d377a1e4b2f5c4 -->"
)
CHAPTER_HEADINGS = (
    "## 学习目标",
    "## 当前 Pi 行为",
    "## Python 实验",
    "## 验证方式",
    "## 边界与安全",
)
MANIFEST_START = "<!-- course-chapter-manifest:start -->"
MANIFEST_END = "<!-- course-chapter-manifest:end -->"
NUMBERED_CHAPTER = re.compile(r"\d{2}-[^/]+/README\.md\Z")
BASELINE_COMMENT = re.compile(r"<!--\s*pi-baseline:.*?-->", re.DOTALL)


@dataclass
class ValidationResult:
    """The accumulated, human-readable validation errors."""

    errors: list[str]


def validate_source_map(path: Path | str) -> ValidationResult:
    """Require exactly the pinned Pi baseline marker in a source-map document."""
    source_map = Path(path)
    try:
        contents = source_map.read_text(encoding="utf-8")
    except OSError as error:
        return ValidationResult([f"{source_map}: cannot read source map ({error})"])

    markers = BASELINE_COMMENT.findall(contents)
    if not markers:
        return ValidationResult([f"{source_map}: missing Pi baseline marker"])
    if markers != [BASELINE_MARKER]:
        return ValidationResult([f"{source_map}: invalid Pi baseline marker"])
    return ValidationResult([])


def discover_chapters(docs_dir: Path | str) -> list[Path]:
    """Return the course map and its declared numbered chapter README files.

    A map can limit the main chapter set with the documented manifest block.  In
    the absence of that block, every numbered chapter README is considered a
    main chapter so that an omitted manifest cannot silently weaken checks.
    """
    docs = Path(docs_dir)
    course_map = docs / "00-course-map.md"
    chapters = [course_map]
    manifest = _read_manifest(course_map)

    if manifest is None:
        declared = [
            path.relative_to(docs).as_posix()
            for path in sorted(docs.glob("[0-9][0-9]-*/README.md"))
        ]
    else:
        declared = manifest

    for relative_path in declared:
        if relative_path == "00-course-map.md" or not NUMBERED_CHAPTER.fullmatch(relative_path):
            continue
        chapter = docs / relative_path
        if chapter not in chapters:
            chapters.append(chapter)
    return chapters


def validate_chapters(docs_dir: Path | str) -> ValidationResult:
    """Ensure each declared main chapter contains every teaching-contract heading."""
    docs = Path(docs_dir)
    errors: list[str] = []
    manifest = _read_manifest(docs / "00-course-map.md")

    if manifest is not None:
        for relative_path in manifest:
            if relative_path != "00-course-map.md" and not NUMBERED_CHAPTER.fullmatch(relative_path):
                errors.append(
                    "00-course-map.md: invalid manifest chapter "
                    f"{relative_path}"
                )

    for chapter in discover_chapters(docs):
        try:
            relative_path = chapter.relative_to(docs).as_posix()
        except ValueError:
            relative_path = str(chapter)

        try:
            lines = chapter.read_text(encoding="utf-8").splitlines()
        except OSError as error:
            errors.append(f"{relative_path}: cannot read chapter ({error})")
            continue

        headings = {line.strip() for line in lines}
        for heading in CHAPTER_HEADINGS:
            if heading not in headings:
                errors.append(f"{relative_path}: missing heading {heading}")
    return ValidationResult(errors)


def _read_manifest(course_map: Path) -> list[str] | None:
    """Read the optional manifest block from the course map."""
    try:
        contents = course_map.read_text(encoding="utf-8")
    except OSError:
        return None

    start = contents.find(MANIFEST_START)
    end = contents.find(MANIFEST_END)
    if start == -1 or end == -1 or end < start:
        return None

    block = contents[start + len(MANIFEST_START) : end]
    entries: list[str] = []
    for line in block.splitlines():
        entry = line.strip()
        if entry.startswith("- "):
            entry = entry[2:].strip()
        if entry.startswith("`") and entry.endswith("`"):
            entry = entry[1:-1]
        if entry:
            entries.append(entry)
    return entries


def main() -> int:
    """Run the course contract checks for this repository."""
    root = Path(__file__).resolve().parents[1]
    docs_dir = root / "docs"
    result = validate_source_map(docs_dir / "pi-source-map.md")
    result.errors.extend(validate_chapters(docs_dir).errors)

    if result.errors:
        print("\n".join(result.errors))
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
