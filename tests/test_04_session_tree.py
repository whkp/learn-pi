"""Behavior tests for the course-local session-tree teaching model."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import FrozenInstanceError
from io import StringIO
import json
import unittest

from learn_pi_lab.cli import main
from learn_pi_lab.labs.session_tree import (
    MalformedTranscript,
    TranscriptEntry,
    TranscriptTree,
    UnknownTranscriptEntry,
)


class SessionTreeTests(unittest.TestCase):
    def test_selected_branch_runs_from_root_to_leaf_without_siblings(self) -> None:
        entries = (
            TranscriptEntry("root", None, "Root"),
            TranscriptEntry("child", "root", "Child"),
            TranscriptEntry("leaf", "child", "Leaf"),
            TranscriptEntry("sibling", "root", "Sibling"),
        )

        path = TranscriptTree(entries).path_to("leaf")

        self.assertEqual(("root", "child", "leaf"), tuple(entry.id for entry in path))
        self.assertNotIn("sibling", tuple(entry.id for entry in path))

    def test_empty_duplicate_dangling_and_self_parent_entries_are_rejected(self) -> None:
        cases = {
            "empty id": (TranscriptEntry("", None, "empty"),),
            "duplicate id": (
                TranscriptEntry("root", None, "one"),
                TranscriptEntry("root", None, "two"),
            ),
            "dangling parent": (TranscriptEntry("child", "missing", "child"),),
            "self parent": (TranscriptEntry("self", "self", "self"),),
        }

        for expected_message, entries in cases.items():
            with self.subTest(expected_message=expected_message):
                with self.assertRaisesRegex(MalformedTranscript, expected_message):
                    TranscriptTree(entries)

    def test_cycles_are_rejected(self) -> None:
        entries = (
            TranscriptEntry("first", "second", "First"),
            TranscriptEntry("second", "first", "Second"),
        )

        with self.assertRaisesRegex(MalformedTranscript, "cycle"):
            TranscriptTree(entries)

    def test_unknown_leaf_raises_a_structured_error(self) -> None:
        tree = TranscriptTree((TranscriptEntry("root", None, "Root"),))

        with self.assertRaises(UnknownTranscriptEntry) as caught:
            tree.path_to("missing")

        self.assertEqual("missing", caught.exception.entry_id)
        self.assertIn("unknown transcript entry", str(caught.exception))

    def test_tree_snapshots_input_and_exposes_only_immutable_tuples(self) -> None:
        root = TranscriptEntry("root", None, "Root")
        child = TranscriptEntry("child", "root", "Child")
        input_entries = [root, child]
        tree = TranscriptTree(input_entries)
        input_entries.clear()
        input_entries.append(TranscriptEntry("other", None, "Other"))

        path = tree.path_to("child")
        branch_ids = tree.branch_ids()

        self.assertEqual(("root", "child"), tuple(entry.id for entry in path))
        self.assertEqual(("root", "child"), branch_ids)
        self.assertIsInstance(path, tuple)
        self.assertIsInstance(branch_ids, tuple)
        with self.assertRaises(FrozenInstanceError):
            child.text = "Changed"  # type: ignore[misc]
        with self.assertRaises(TypeError):
            path[0] = TranscriptEntry("other", None, "Other")  # type: ignore[index]
        with self.assertRaises(TypeError):
            branch_ids[0] = "other"  # type: ignore[index]

    def test_session_tree_cli_prints_the_deterministic_fixture_branch(self) -> None:
        output = StringIO()

        with redirect_stdout(output):
            exit_code = main(["lab", "session-tree"])

        self.assertEqual(0, exit_code)
        self.assertEqual(
            {
                "path_ids": ["root", "child", "leaf"],
                "texts": ["Root", "Child", "Leaf"],
            },
            json.loads(output.getvalue()),
        )

    def test_session_tree_cli_reports_an_unknown_leaf(self) -> None:
        output = StringIO()
        error = StringIO()

        with redirect_stdout(output), redirect_stderr(error):
            exit_code = main(["lab", "session-tree", "--leaf", "missing"])

        self.assertEqual(2, exit_code)
        self.assertEqual("", output.getvalue())
        self.assertIn("session-tree:", error.getvalue())
        self.assertIn("unknown transcript entry", error.getvalue())

    def test_session_tree_cli_rejects_an_irrelevant_positional_directory(self) -> None:
        output = StringIO()
        error = StringIO()

        with redirect_stdout(output), redirect_stderr(error):
            exit_code = main(["lab", "session-tree", "unexpected-positional"])

        self.assertEqual(2, exit_code)
        self.assertEqual("", output.getvalue())
        self.assertIn("session-tree:", error.getvalue())

    def test_session_tree_cli_rejects_an_irrelevant_boundary(self) -> None:
        output = StringIO()
        error = StringIO()

        with redirect_stdout(output), redirect_stderr(error):
            exit_code = main(["lab", "session-tree", "--boundary", "."])

        self.assertEqual(2, exit_code)
        self.assertEqual("", output.getvalue())
        self.assertIn("session-tree:", error.getvalue())


if __name__ == "__main__":
    unittest.main()
