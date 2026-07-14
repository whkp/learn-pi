"""A course-local resource-discovery teaching model, not Pi Skills discovery or loading."""

from __future__ import annotations

from dataclasses import dataclass
import errno
import os
from pathlib import Path
import re
import stat
from typing import Iterator, Sequence


LESSON_FILENAME = "LESSON.md"
_RESOURCE_NAME = re.compile(r"[a-z]+(?:-[a-z]+)*\Z")


@dataclass(frozen=True)
class LessonResource:
    """One immutable, content-snapshotted course resource."""

    name: str
    description: str
    body: str
    path: Path


@dataclass(frozen=True)
class ResourceCatalog:
    """Immutable accepted resources plus diagnostics for excluded candidates."""

    resources: tuple[LessonResource, ...]
    diagnostics: tuple[str, ...]


class UnknownLessonResource(KeyError):
    """Raised when a name is absent from an already scanned catalog."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(name)

    def __str__(self) -> str:
        return f"unknown lesson resource: {self.name!r}"


def scan_lesson_resources(paths: Sequence[Path]) -> ResourceCatalog:
    """Scan physical ``LESSON.md`` files beneath existing supplied roots.

    Symlink files and directories are skipped with diagnostics, never followed.
    Accepted content is read once into the immutable catalog so later filesystem
    changes cannot affect :func:`load_resource`.
    """
    resources: list[LessonResource] = []
    diagnostics: list[str] = []
    names: set[str] = set()

    for supplied_path in paths:
        root = Path(supplied_path)
        for lesson_path, contents in _lesson_snapshots_beneath(root, diagnostics):
            resource, diagnostic = _parse_lesson(lesson_path, contents)
            if diagnostic is not None:
                diagnostics.append(diagnostic)
                continue
            assert resource is not None
            if resource.name in names:
                diagnostics.append(f"{lesson_path}: duplicate name {resource.name!r}")
                continue

            names.add(resource.name)
            resources.append(resource)

    return ResourceCatalog(resources=tuple(resources), diagnostics=tuple(diagnostics))


def load_resource(catalog: ResourceCatalog, name: str) -> LessonResource:
    """Return a catalog snapshot by name without consulting the filesystem."""
    for resource in catalog.resources:
        if resource.name == name:
            return resource
    raise UnknownLessonResource(name)


def _lesson_snapshots_beneath(
    root: Path,
    diagnostics: list[str],
) -> Iterator[tuple[Path, str]]:
    """Yield physical ``LESSON.md`` snapshots from one supplied root only."""
    try:
        root_metadata = root.lstat()
    except OSError as error:
        diagnostics.append(f"{root}: cannot inspect input path ({error})")
        return

    if stat.S_ISLNK(root_metadata.st_mode):
        diagnostics.append(f"{root}: skipped symlink root")
        return
    if stat.S_ISREG(root_metadata.st_mode):
        if root.name == LESSON_FILENAME:
            contents = _snapshot_lesson_path(root, diagnostics)
            if contents is not None:
                yield root, contents
        return
    if not stat.S_ISDIR(root_metadata.st_mode):
        diagnostics.append(f"{root}: input path does not exist or is not a directory/file")
        return

    try:
        directory_fd = _open_root_directory(root)
    except OSError as error:
        _record_directory_open_error(root, error, diagnostics, root=True)
        return

    try:
        if not stat.S_ISDIR(os.fstat(directory_fd).st_mode):
            diagnostics.append(f"{root}: input path is not a directory")
            return
        yield from _walk_directory_fd(directory_fd, root, diagnostics)
    finally:
        os.close(directory_fd)


def _walk_directory_fd(
    directory_fd: int,
    logical_directory: Path,
    diagnostics: list[str],
) -> Iterator[tuple[Path, str]]:
    """Walk one already-open physical directory using only fd-relative operations."""
    try:
        child_names = sorted(os.listdir(directory_fd))
    except OSError as error:
        diagnostics.append(f"{logical_directory}: cannot inspect directory ({error})")
        return

    for child_name in child_names:
        logical_path = logical_directory / child_name
        try:
            metadata = os.stat(child_name, dir_fd=directory_fd, follow_symlinks=False)
        except OSError as error:
            diagnostics.append(f"{logical_path}: cannot inspect path ({error})")
            continue

        if stat.S_ISLNK(metadata.st_mode):
            diagnostics.append(f"{logical_path}: skipped symlink path")
            continue
        if stat.S_ISDIR(metadata.st_mode):
            try:
                child_fd = _open_child_directory(directory_fd, child_name)
            except OSError as error:
                _record_directory_open_error(logical_path, error, diagnostics)
                continue
            try:
                if not stat.S_ISDIR(os.fstat(child_fd).st_mode):
                    diagnostics.append(f"{logical_path}: path is not a directory")
                    continue
                yield from _walk_directory_fd(child_fd, logical_path, diagnostics)
            finally:
                os.close(child_fd)
        elif child_name == LESSON_FILENAME and stat.S_ISREG(metadata.st_mode):
            contents = _snapshot_lesson_from_directory(
                directory_fd,
                child_name,
                logical_path,
                diagnostics,
            )
            if contents is not None:
                yield logical_path, contents


def _open_root_directory(root: Path) -> int:
    """Open a supplied root directory without following a final symlink."""
    return os.open(root, _directory_open_flags())


def _open_child_directory(directory_fd: int, child_name: str) -> int:
    """Open one child directory from its already trusted parent descriptor."""
    return os.open(child_name, _directory_open_flags(), dir_fd=directory_fd)


def _directory_open_flags() -> int:
    no_follow = getattr(os, "O_NOFOLLOW", None)
    directory_flag = getattr(os, "O_DIRECTORY", None)
    if no_follow is None or directory_flag is None:
        raise OSError(errno.ENOTSUP, "safe no-follow directory opening is unavailable")
    return os.O_RDONLY | directory_flag | no_follow


def _record_directory_open_error(
    path: Path,
    error: OSError,
    diagnostics: list[str],
    *,
    root: bool = False,
) -> None:
    """Turn fd-open failures into deterministic directory/symlink diagnostics."""
    if error.errno in {errno.ELOOP, errno.ENOTDIR}:
        label = "root" if root else "path"
        diagnostics.append(f"{path}: skipped symlink {label}")
    else:
        diagnostics.append(f"{path}: cannot open directory ({error})")


def _snapshot_lesson_path(path: Path, diagnostics: list[str]) -> str | None:
    """Read a standalone supplied LESSON.md through a final-component no-follow fd."""
    no_follow = getattr(os, "O_NOFOLLOW", None)
    if no_follow is None:
        diagnostics.append(f"{path}: safe no-follow opening is unavailable")
        return None
    try:
        descriptor = os.open(path, os.O_RDONLY | no_follow)
    except OSError as error:
        _record_lesson_open_error(path, error, diagnostics)
        return None
    return _read_lesson_descriptor(descriptor, path, diagnostics)


def _snapshot_lesson_from_directory(
    directory_fd: int,
    name: str,
    logical_path: Path,
    diagnostics: list[str],
) -> str | None:
    """Read LESSON.md from its current directory descriptor without path traversal."""
    no_follow = getattr(os, "O_NOFOLLOW", None)
    if no_follow is None:
        diagnostics.append(f"{logical_path}: safe no-follow opening is unavailable")
        return None
    try:
        descriptor = os.open(name, os.O_RDONLY | no_follow, dir_fd=directory_fd)
    except OSError as error:
        _record_lesson_open_error(logical_path, error, diagnostics)
        return None
    return _read_lesson_descriptor(descriptor, logical_path, diagnostics)


def _read_lesson_descriptor(descriptor: int, path: Path, diagnostics: list[str]) -> str | None:
    """Read a regular LESSON.md descriptor and close it in every outcome."""
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            diagnostics.append(f"{path}: resource path is not a regular file")
            return None
        with os.fdopen(descriptor, "r", encoding="utf-8") as resource_file:
            descriptor = -1
            return resource_file.read()
    except (OSError, UnicodeError) as error:
        diagnostics.append(f"{path}: cannot read resource file ({error})")
        return None
    finally:
        if descriptor != -1:
            os.close(descriptor)


def _record_lesson_open_error(path: Path, error: OSError, diagnostics: list[str]) -> None:
    """Turn a no-follow LESSON.md open failure into a snapshot diagnostic."""
    if error.errno == errno.ELOOP:
        diagnostics.append(f"{path}: skipped symlink resource file")
    else:
        diagnostics.append(f"{path}: cannot read resource file ({error})")


def _parse_lesson(path: Path, contents: str) -> tuple[LessonResource | None, str | None]:
    """Parse the lesson-only frontmatter contract and preserve its body snapshot."""
    lines = contents.split("\n", maxsplit=4)
    if len(lines) < 3 or lines[0] != "---":
        return None, f"{path}: invalid frontmatter"
    if not lines[1].startswith("name: "):
        return None, f"{path}: invalid name"

    name = lines[1][len("name: ") :]
    if _RESOURCE_NAME.fullmatch(name) is None:
        return None, f"{path}: invalid name {name!r}"
    if not lines[2].startswith("description: "):
        return None, f"{path}: missing description"

    description = lines[2][len("description: ") :].strip()
    if not description:
        return None, f"{path}: missing description"
    if len(lines) < 4 or lines[3] != "---":
        return None, f"{path}: invalid frontmatter"

    body = lines[4] if len(lines) == 5 else ""
    return LessonResource(name=name, description=description, body=body, path=path), None
