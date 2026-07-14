"""A teaching model for course context files, not Pi context-file discovery.

Only ``.course-rules.md`` is considered so that this lesson never claims to
parse Pi's ``AGENTS.md`` or ``CLAUDE.md`` conventions.  Discovery skips rule
files that are missing or unreadable, but rejects symlinks with
``UnsafeRulePath`` without reading their targets. If a returned path
disappears, becomes unsafe, or becomes unreadable before ``merge_rules``
reads it, merging rejects the partial result with a diagnostic instead of
silently dropping rules or reading an unexpected target.
"""

from __future__ import annotations

from dataclasses import dataclass
import errno
import os
from pathlib import Path
import stat
from typing import Iterable


DEFAULT_RULE_FILENAME = ".course-rules.md"


class InvalidBoundary(ValueError):
    """Raised when a requested discovery boundary cannot contain the start."""


class InvalidStart(ValueError):
    """Raised when a requested discovery start is not an existing directory."""


class InvalidRuleFilename(ValueError):
    """Raised when a requested rule filename is not one bare filename."""


class RuleFileUnavailable(RuntimeError):
    """Raised when a rule file vanishes or becomes unreadable before merging."""


class UnsafeRulePath(RuntimeError):
    """Raised when a rule path is a symlink or cannot be opened safely."""


@dataclass(frozen=True)
class RuleBundle:
    """The source paths and nonblank rule lines collected in stable order."""

    paths: tuple[Path, ...]
    lines: tuple[str, ...]


def discover_rules(
    start: Path,
    *,
    filename: str = DEFAULT_RULE_FILENAME,
    boundary: Path | None = None,
) -> tuple[Path, ...]:
    """Discover readable course rule files from the rootest directory to ``start``.

    When ``boundary`` is present, discovery examines only the inclusive path
    from ``boundary`` to ``start``.  Without it, discovery reaches the
    filesystem root. The function reads no file content and ignores missing
    or unreadable candidate files, while rejecting unsafe symlinks.
    """
    rule_filename = _validated_filename(filename)
    start_directory = _existing_directory(start, label="start", error_type=InvalidStart)
    boundary_directory: Path | None = None

    if boundary is not None:
        boundary_directory = _existing_directory(
            boundary,
            label="boundary",
            error_type=InvalidBoundary,
        )
        try:
            start_directory.relative_to(boundary_directory)
        except ValueError as error:
            raise InvalidBoundary(
                f"start directory {start_directory} is outside boundary {boundary_directory}"
            ) from error

    containment_root = (
        boundary_directory if boundary_directory is not None else _filesystem_root(start_directory)
    )
    discovered: list[Path] = []
    current = start_directory
    while True:
        candidate = current / rule_filename
        if _is_readable_regular_file(candidate, containment_root):
            discovered.append(candidate)

        if boundary_directory is not None and current == boundary_directory:
            break
        if boundary_directory is None and current.parent == current:
            break
        current = current.parent

    return tuple(reversed(discovered))


def merge_rules(paths: Iterable[Path]) -> RuleBundle:
    """Merge rule files in input order, rejecting unavailable or unsafe files."""
    source_paths = tuple(Path(path) for path in paths)
    lines: list[str] = []

    for path in source_paths:
        contents = _read_regular_file_without_following_symlinks(path)
        lines.extend(line.strip() for line in contents.splitlines() if line.strip())

    return RuleBundle(paths=source_paths, lines=tuple(lines))


def _existing_directory(
    value: Path,
    *,
    label: str,
    error_type: type[InvalidStart] | type[InvalidBoundary],
) -> Path:
    directory = Path(value).resolve()
    if not directory.is_dir():
        raise error_type(f"{label} directory does not exist or is not a directory: {directory}")
    return directory


def _validated_filename(filename: str) -> str:
    """Require one bare filename so a candidate cannot escape its directory."""
    if not isinstance(filename, str):
        raise InvalidRuleFilename("rule filename must be a bare filename")

    candidate = Path(filename)
    if (
        not filename
        or candidate.is_absolute()
        or filename in {".", ".."}
        or "/" in filename
        or "\\" in filename
        or candidate.name != filename
    ):
        raise InvalidRuleFilename("rule filename must be a bare filename")
    return filename


def _filesystem_root(path: Path) -> Path:
    """Return the root directory containing one already resolved path."""
    root = path
    while root.parent != root:
        root = root.parent
    return root


def _is_readable_regular_file(path: Path, containment_root: Path) -> bool:
    """Check candidate readability through a descriptor that follows no symlinks."""
    _require_path_within(path, containment_root)
    try:
        descriptor = _open_absolute_regular_file_without_symlinks(path)
    except FileNotFoundError:
        return False
    except UnsafeRulePath:
        raise
    except OSError:
        return False

    try:
        return stat.S_ISREG(os.fstat(descriptor).st_mode)
    finally:
        os.close(descriptor)


def _require_path_within(path: Path, containment_root: Path) -> None:
    """Reject a candidate that is not lexically inside the discovery root."""
    try:
        path.relative_to(containment_root)
    except ValueError as error:
        raise UnsafeRulePath(f"rule file is outside the discovery root: {path}") from error


def _read_regular_file_without_following_symlinks(path: Path) -> str:
    """Read one regular file through a descriptor that follows no path symlinks."""
    try:
        descriptor = _open_absolute_regular_file_without_symlinks(path)
    except FileNotFoundError as error:
        raise RuleFileUnavailable(f"rule file disappeared before merge: {path}") from error
    except UnsafeRulePath:
        raise
    except OSError as error:
        raise RuleFileUnavailable(f"rule file is unavailable before merge: {path}") from error

    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise RuleFileUnavailable(f"rule file is not a regular file: {path}")
        with os.fdopen(descriptor, "r", encoding="utf-8") as rule_file:
            descriptor = -1
            return rule_file.read()
    except (OSError, UnicodeError) as error:
        raise RuleFileUnavailable(f"rule file is unavailable before merge: {path}") from error
    finally:
        if descriptor != -1:
            os.close(descriptor)


def _open_absolute_regular_file_without_symlinks(path: Path) -> int:
    """Open an absolute file by descriptor-walking every component without symlinks."""
    no_follow = getattr(os, "O_NOFOLLOW", None)
    directory_flag = getattr(os, "O_DIRECTORY", None)
    if no_follow is None or directory_flag is None:
        raise UnsafeRulePath("safe no-follow rule-file opening is unavailable")

    absolute_path = Path(os.path.abspath(os.fspath(path)))
    root = Path(absolute_path.anchor)
    components = absolute_path.parts[1:]
    if not root or not components:
        raise RuleFileUnavailable(f"rule file is not an absolute file path: {path}")

    directory_flags = os.O_RDONLY | directory_flag | no_follow
    try:
        directory_descriptor = os.open(root, directory_flags)
    except OSError as error:
        _raise_unsafe_symlink_error(error, root)
        raise

    try:
        current_path = root
        for component in components[:-1]:
            current_path = current_path / component
            _require_non_symlink_component(component, directory_descriptor, current_path)
            try:
                next_descriptor = os.open(
                    component,
                    directory_flags,
                    dir_fd=directory_descriptor,
                )
            except OSError as error:
                _raise_unsafe_symlink_error(error, current_path)
                raise
            os.close(directory_descriptor)
            directory_descriptor = next_descriptor

        final_component = components[-1]
        _require_non_symlink_component(
            final_component,
            directory_descriptor,
            absolute_path,
        )
        try:
            return os.open(
                final_component,
                os.O_RDONLY | no_follow,
                dir_fd=directory_descriptor,
            )
        except OSError as error:
            _raise_unsafe_symlink_error(error, absolute_path)
            raise
    finally:
        os.close(directory_descriptor)


def _require_non_symlink_component(name: str, directory_descriptor: int, path: Path) -> None:
    """Reject an existing symlink before opening the next descriptor component."""
    metadata = os.stat(name, dir_fd=directory_descriptor, follow_symlinks=False)
    if stat.S_ISLNK(metadata.st_mode):
        raise UnsafeRulePath(f"rule file symlink is not allowed: {path}")


def _raise_unsafe_symlink_error(error: OSError, path: Path) -> None:
    """Map no-follow symlink failures to the course-local unsafe-path error."""
    if error.errno == errno.ELOOP:
        raise UnsafeRulePath(f"rule file symlink is not allowed: {path}") from error
