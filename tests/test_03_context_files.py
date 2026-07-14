"""Behavior tests for the course-local context-files teaching model."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import FrozenInstanceError
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from learn_pi_lab.cli import main
from learn_pi_lab.labs.context_files import (
    InvalidBoundary,
    InvalidRuleFilename,
    RuleFileUnavailable,
    UnsafeRulePath,
    discover_rules,
    merge_rules,
)


RULE_FILENAME = ".course-rules.md"


def write_rules(directory: Path, *lines: str) -> Path:
    """Create one fixture rule file and return its path."""
    path = directory / RULE_FILENAME
    path.write_text("\n".join(lines), encoding="utf-8")
    return path.resolve()


class ContextFilesTests(unittest.TestCase):
    def test_parent_rules_merge_before_child_rules(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            course_root = Path(directory) / "course"
            parent = course_root / "parent"
            child = parent / "child"
            child.mkdir(parents=True)
            root_rule = write_rules(course_root, "root rule")
            parent_rule = write_rules(parent, "parent rule")
            child_rule = write_rules(child, "child rule")

            bundle = merge_rules(discover_rules(child, boundary=course_root))

        self.assertEqual(
            (root_rule.resolve(), parent_rule.resolve(), child_rule.resolve()),
            bundle.paths,
        )
        self.assertEqual(("root rule", "parent rule", "child rule"), bundle.lines)

    def test_boundary_excludes_a_parent_rule_outside_the_course(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            course_root = workspace / "course"
            child = course_root / "lesson"
            child.mkdir(parents=True)
            outside_rule = write_rules(workspace, "outside rule")
            root_rule = write_rules(course_root, "course rule")
            child_rule = write_rules(child, "child rule")

            bundle = merge_rules(discover_rules(child, boundary=course_root))

        self.assertEqual((root_rule.resolve(), child_rule.resolve()), bundle.paths)
        self.assertEqual(("course rule", "child rule"), bundle.lines)
        self.assertNotIn(outside_rule.resolve(), bundle.paths)
        self.assertNotIn("outside rule", bundle.lines)

    def test_start_outside_boundary_raises_a_helpful_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            boundary = workspace / "course"
            start = workspace / "other"
            boundary.mkdir()
            start.mkdir()

            with self.assertRaisesRegex(InvalidBoundary, "outside boundary"):
                discover_rules(start, boundary=boundary)

    def test_blank_rule_lines_are_omitted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rule_file = write_rules(Path(directory), "", "  first rule  ", "   ", "second rule")

            bundle = merge_rules((rule_file,))

        self.assertEqual(("first rule", "second rule"), bundle.lines)

    def test_merge_preserves_input_order_and_returns_immutable_tuples(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            first = write_rules(directory_path, "first")
            second_path = directory_path / "second.course-rules.md"
            second_path.write_text("second\n", encoding="utf-8")
            second = second_path.resolve()

            bundle = merge_rules((second, first))

        self.assertEqual((second, first), bundle.paths)
        self.assertEqual(("second", "first"), bundle.lines)
        self.assertIsInstance(bundle.paths, tuple)
        self.assertIsInstance(bundle.lines, tuple)
        with self.assertRaises(FrozenInstanceError):
            bundle.lines = ()  # type: ignore[misc]

    def test_rule_file_that_disappears_before_merge_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rule_file = write_rules(Path(directory), "transient rule")
            rule_file.unlink()

            with self.assertRaisesRegex(RuleFileUnavailable, "disappeared"):
                merge_rules((rule_file,))

    def test_rule_symlink_inside_boundary_to_outside_is_never_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            course_root = workspace / "course"
            course_root.mkdir()
            sentinel = workspace / "outside.md"
            sentinel.write_text("outside sentinel must not be read\n", encoding="utf-8")
            (course_root / RULE_FILENAME).symlink_to(sentinel)

            with self.assertRaisesRegex(UnsafeRulePath, "symlink") as caught:
                merge_rules(discover_rules(course_root, boundary=course_root))

        self.assertNotIn("outside sentinel", str(caught.exception))

    def test_absolute_and_traversal_rule_filenames_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            course_root = workspace / "course"
            course_root.mkdir()
            outside = workspace / "outside.md"
            outside.write_text("outside sentinel\n", encoding="utf-8")

            for filename in (str(outside), "../outside.md"):
                with self.subTest(filename=filename):
                    with self.assertRaisesRegex(InvalidRuleFilename, "bare filename"):
                        discover_rules(course_root, filename=filename, boundary=course_root)

    def test_regular_rule_swapped_to_symlink_before_merge_is_never_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            course_root = workspace / "course"
            course_root.mkdir()
            rule_file = write_rules(course_root, "safe rule")
            discovered = discover_rules(course_root, boundary=course_root)
            sentinel = workspace / "outside.md"
            sentinel.write_text("outside sentinel must not be read\n", encoding="utf-8")
            rule_file.unlink()
            rule_file.symlink_to(sentinel)

            with self.assertRaisesRegex(UnsafeRulePath, "symlink") as caught:
                merge_rules(discovered)

        self.assertNotIn("outside sentinel", str(caught.exception))

    def test_ancestor_directory_swapped_to_symlink_before_merge_is_never_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            course_root = workspace / "course"
            nested = course_root / "nested"
            nested.mkdir(parents=True)
            rule_file = write_rules(nested, "safe nested rule")
            discovered = discover_rules(nested, boundary=course_root)
            external = workspace / "external"
            external.mkdir()
            write_rules(external, "outside ancestor sentinel must not be read")
            rule_file.unlink()
            nested.rmdir()
            nested.symlink_to(external, target_is_directory=True)

            with self.assertRaisesRegex(UnsafeRulePath, "symlink") as caught:
                merge_rules(discovered)

        self.assertNotIn("outside ancestor sentinel", str(caught.exception))

    def test_context_files_cli_prints_paths_and_lines(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            course_root = Path(directory) / "course"
            course_root.mkdir()
            rule_file = write_rules(course_root, "course rule")
            output = StringIO()

            with redirect_stdout(output):
                exit_code = main(["lab", "context-files", str(course_root)])

        self.assertEqual(0, exit_code)
        self.assertEqual(
            {"lines": ["course rule"], "paths": [str(rule_file.resolve())]},
            json.loads(output.getvalue()),
        )

    def test_context_files_cli_reports_a_missing_directory(self) -> None:
        output = StringIO()
        error = StringIO()

        with redirect_stdout(output), redirect_stderr(error):
            exit_code = main(["lab", "context-files", "missing-course-directory"])

        self.assertEqual(2, exit_code)
        self.assertEqual("", output.getvalue())
        self.assertIn("does not exist", error.getvalue())

    def test_context_files_cli_reports_a_bad_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            start = workspace / "start"
            boundary = workspace / "boundary"
            start.mkdir()
            boundary.mkdir()
            output = StringIO()
            error = StringIO()

            with redirect_stdout(output), redirect_stderr(error):
                exit_code = main(
                    ["lab", "context-files", str(start), "--boundary", str(boundary)]
                )

        self.assertEqual(2, exit_code)
        self.assertEqual("", output.getvalue())
        self.assertIn("outside boundary", error.getvalue())

    def test_context_files_cli_reports_an_unsafe_rule_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            course_root = workspace / "course"
            course_root.mkdir()
            sentinel = workspace / "outside.md"
            sentinel.write_text("outside sentinel\n", encoding="utf-8")
            (course_root / RULE_FILENAME).symlink_to(sentinel)
            output = StringIO()
            error = StringIO()

            with redirect_stdout(output), redirect_stderr(error):
                exit_code = main(["lab", "context-files", str(course_root)])

        self.assertEqual(2, exit_code)
        self.assertEqual("", output.getvalue())
        self.assertIn("context-files:", error.getvalue())
        self.assertNotIn("Traceback", error.getvalue())


if __name__ == "__main__":
    unittest.main()
