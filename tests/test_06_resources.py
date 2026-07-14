"""Behavior tests for the course-local resource-discovery teaching model."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import FrozenInstanceError
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from learn_pi_lab.cli import main
from learn_pi_lab.labs import resources as resources_module
from learn_pi_lab.labs.resources import (
    UnknownLessonResource,
    load_resource,
    scan_lesson_resources,
)


def write_lesson(
    directory: Path,
    *,
    name: str = "sample-resource",
    description: str = "Sample description",
    body: str = "Sample body",
) -> Path:
    """Create one simplified course resource fixture."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "LESSON.md"
    path.write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n{body}",
        encoding="utf-8",
    )
    return path


class ResourceDiscoveryTests(unittest.TestCase):
    def test_valid_resource_catalogues_metadata_and_snapshot_body(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "resources"
            lesson = write_lesson(root / "sample", body="Original body")

            catalog = scan_lesson_resources((root,))
            resource = load_resource(catalog, "sample-resource")

        self.assertEqual((), catalog.diagnostics)
        self.assertEqual("sample-resource", resource.name)
        self.assertEqual("Sample description", resource.description)
        self.assertEqual("Original body", resource.body)
        self.assertEqual(lesson, resource.path)

    def test_missing_description_is_diagnostic_and_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "resources"
            root.mkdir()
            lesson = root / "LESSON.md"
            lesson.write_text("---\nname: missing-description\n---\nBody", encoding="utf-8")

            catalog = scan_lesson_resources((root,))

        self.assertEqual((), catalog.resources)
        self.assertEqual(1, len(catalog.diagnostics))
        self.assertIn(str(lesson), catalog.diagnostics[0])
        self.assertIn("missing description", catalog.diagnostics[0])

    def test_duplicate_resource_name_is_diagnostic_and_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "resources"
            first = write_lesson(root / "first", name="duplicate")
            second = write_lesson(root / "second", name="duplicate")

            catalog = scan_lesson_resources((root,))

        self.assertEqual((first,), tuple(resource.path for resource in catalog.resources))
        self.assertEqual(1, len(catalog.diagnostics))
        self.assertIn(str(second), catalog.diagnostics[0])
        self.assertIn("duplicate name", catalog.diagnostics[0])

    def test_symlinked_lesson_file_is_never_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            root = workspace / "resources"
            root.mkdir()
            sentinel = workspace / "external-LESSON.md"
            sentinel.write_text(
                "---\nname: external\ndescription: External\n---\nexternal sentinel",
                encoding="utf-8",
            )
            (root / "LESSON.md").symlink_to(sentinel)

            catalog = scan_lesson_resources((root,))

        self.assertEqual((), catalog.resources)
        self.assertTrue(any("symlink" in message for message in catalog.diagnostics))
        self.assertFalse(any("external sentinel" in resource.body for resource in catalog.resources))

    def test_symlinked_resource_directory_is_never_followed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            root = workspace / "resources"
            root.mkdir()
            external = workspace / "external"
            write_lesson(external, name="external", body="external directory sentinel")
            (root / "linked").symlink_to(external, target_is_directory=True)

            catalog = scan_lesson_resources((root,))

        self.assertEqual((), catalog.resources)
        self.assertTrue(any("symlink" in message for message in catalog.diagnostics))
        self.assertFalse(
            any("external directory sentinel" in resource.body for resource in catalog.resources)
        )

    def test_directory_swap_before_recursive_open_is_never_followed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            root = workspace / "resources"
            nested = root / "nested"
            lesson = write_lesson(nested, name="safe", body="safe body")
            external = workspace / "external"
            write_lesson(external, name="external", body="external swap sentinel")
            original_open_child = resources_module._open_child_directory

            def swap_then_open(directory_fd: int, child_name: str) -> int:
                if child_name == "nested":
                    lesson.unlink()
                    nested.rmdir()
                    nested.symlink_to(external, target_is_directory=True)
                return original_open_child(directory_fd, child_name)

            with patch.object(
                resources_module,
                "_open_child_directory",
                side_effect=swap_then_open,
            ):
                catalog = scan_lesson_resources((root,))

        self.assertEqual((), catalog.resources)
        self.assertTrue(any("symlink" in message for message in catalog.diagnostics))
        self.assertFalse(
            any("external swap sentinel" in resource.body for resource in catalog.resources)
        )

    def test_post_scan_file_mutation_does_not_change_loaded_body(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "resources"
            lesson = write_lesson(root, body="Snapshot body")
            catalog = scan_lesson_resources((root,))
            lesson.write_text(
                "---\nname: sample-resource\ndescription: Sample description\n---\nChanged body",
                encoding="utf-8",
            )

            resource = load_resource(catalog, "sample-resource")

        self.assertEqual("Snapshot body", resource.body)

    def test_unknown_resource_raises_without_loading_filesystem(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            catalog = scan_lesson_resources((Path(directory),))

            with self.assertRaises(UnknownLessonResource) as caught:
                load_resource(catalog, "missing")

        self.assertIn("unknown lesson resource", str(caught.exception))

    def test_catalog_and_resources_expose_only_immutable_tuples(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "resources"
            write_lesson(root)
            catalog = scan_lesson_resources((root,))
            resource = catalog.resources[0]

        self.assertIsInstance(catalog.resources, tuple)
        self.assertIsInstance(catalog.diagnostics, tuple)
        with self.assertRaises(FrozenInstanceError):
            catalog.resources = ()  # type: ignore[misc]
        with self.assertRaises(FrozenInstanceError):
            resource.body = "Changed"  # type: ignore[misc]
        with self.assertRaises(TypeError):
            catalog.resources[0] = resource  # type: ignore[index]

    def test_resources_cli_prints_a_selected_resource_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "resources"
            lesson = write_lesson(root, body="CLI body")
            output = StringIO()

            with redirect_stdout(output):
                exit_code = main(["lab", "resources", str(root), "--name", "sample-resource"])

        self.assertEqual(0, exit_code)
        self.assertEqual(
            {
                "name": "sample-resource",
                "description": "Sample description",
                "body": "CLI body",
                "path": str(lesson),
            },
            json.loads(output.getvalue()),
        )

    def test_resources_cli_rejects_boundary_leaf_and_missing_name(self) -> None:
        for arguments in (
            ["lab", "resources", ".", "--boundary", ".", "--name", "sample-resource"],
            ["lab", "resources", ".", "--leaf", "ignored", "--name", "sample-resource"],
            ["lab", "resources", "."],
        ):
            with self.subTest(arguments=arguments):
                output = StringIO()
                error = StringIO()

                with redirect_stdout(output), redirect_stderr(error):
                    exit_code = main(arguments)

                self.assertEqual(2, exit_code)
                self.assertEqual("", output.getvalue())
                self.assertIn("resources:", error.getvalue())


if __name__ == "__main__":
    unittest.main()
