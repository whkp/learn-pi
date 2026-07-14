"""Behavior tests for the course-local compaction teaching model."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import FrozenInstanceError
from io import StringIO
import json
import unittest

from learn_pi_lab.cli import main
from learn_pi_lab.labs.compaction import (
    MalformedPair,
    TranscriptUnit,
    choose_cut,
    compact,
    make_summary,
)


class CompactionTests(unittest.TestCase):
    def test_newest_unpaired_units_fill_the_budget_in_original_order(self) -> None:
        entries = (
            TranscriptUnit("old", "Old"),
            TranscriptUnit("middle", "Middle"),
            TranscriptUnit("new", "New"),
        )

        kept = choose_cut(entries, keep_units=2)

        self.assertEqual(("middle", "new"), tuple(unit.id for unit in kept))

    def test_split_pair_expands_the_kept_range_to_include_both_units(self) -> None:
        entries = (
            TranscriptUnit("old", "Old"),
            TranscriptUnit("call", "Call", pair_id="tool-1", role="tool_call"),
            TranscriptUnit("result", "Result", pair_id="tool-1", role="tool_result"),
            TranscriptUnit("new", "New"),
        )

        kept = choose_cut(entries, keep_units=2)

        self.assertEqual(("call", "result", "new"), tuple(unit.id for unit in kept))

    def test_pair_groups_must_contain_exactly_two_units(self) -> None:
        entries = (TranscriptUnit("call", "Call", pair_id="tool-1"),)

        with self.assertRaisesRegex(MalformedPair, "exactly two"):
            choose_cut(entries, keep_units=1)

    def test_zero_budget_keeps_no_unpaired_or_paired_units(self) -> None:
        entries = (
            TranscriptUnit("old", "Old"),
            TranscriptUnit("call", "Call", pair_id="tool-1"),
            TranscriptUnit("result", "Result", pair_id="tool-1"),
        )

        self.assertEqual((), choose_cut(entries, keep_units=0))

    def test_compaction_plan_snapshots_input_and_is_immutable(self) -> None:
        old = TranscriptUnit("old", "Old")
        new = TranscriptUnit("new", "New")
        input_entries = [old, new]
        plan = compact(input_entries, keep_units=1)
        input_entries.clear()
        input_entries.append(TranscriptUnit("other", "Other"))

        self.assertEqual(("new",), tuple(unit.id for unit in plan.kept))
        self.assertEqual(("old",), tuple(unit.id for unit in plan.summarized))
        with self.assertRaises(FrozenInstanceError):
            old.text = "Changed"  # type: ignore[misc]
        with self.assertRaises(FrozenInstanceError):
            plan.kept = ()  # type: ignore[misc]

    def test_summary_is_deterministic_structured_and_bounded(self) -> None:
        entries = (
            TranscriptUnit("first", "x" * 60, role="message"),
            TranscriptUnit("second", "Result", role="tool_result"),
        )

        first_summary = make_summary(entries)
        second_summary = make_summary(entries)

        self.assertEqual(first_summary, second_summary)
        self.assertEqual(2, first_summary.count)
        self.assertEqual(("first", "second"), first_summary.unit_ids)
        self.assertEqual(("message", "tool_result"), first_summary.roles)
        self.assertEqual(("x" * 40, "Result"), first_summary.text_preview)

    def test_compaction_cli_prints_the_deterministic_fixture_plan(self) -> None:
        output = StringIO()

        with redirect_stdout(output):
            exit_code = main(["lab", "compaction"])

        self.assertEqual(0, exit_code)
        self.assertEqual(
            {
                "kept_ids": ["call", "result", "latest"],
                "summarized_ids": ["intro"],
                "summary": {
                    "count": 1,
                    "roles": ["message"],
                    "text_preview": ["Older context"],
                    "unit_ids": ["intro"],
                },
            },
            json.loads(output.getvalue()),
        )

    def test_compaction_cli_rejects_irrelevant_directory_and_boundary(self) -> None:
        for arguments in (
            ["lab", "compaction", "unexpected-positional"],
            ["lab", "compaction", "--boundary", "."],
        ):
            with self.subTest(arguments=arguments):
                output = StringIO()
                error = StringIO()

                with redirect_stdout(output), redirect_stderr(error):
                    exit_code = main(arguments)

                self.assertEqual(2, exit_code)
                self.assertEqual("", output.getvalue())
                self.assertIn("compaction:", error.getvalue())

    def test_compaction_cli_rejects_an_irrelevant_leaf(self) -> None:
        output = StringIO()
        error = StringIO()

        with redirect_stdout(output), redirect_stderr(error):
            exit_code = main(["lab", "compaction", "--leaf", "ignored"])

        self.assertEqual(2, exit_code)
        self.assertEqual("", output.getvalue())
        self.assertIn("compaction:", error.getvalue())


if __name__ == "__main__":
    unittest.main()
