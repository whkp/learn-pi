"""Behavior tests for the deterministic agent-loop teaching model."""

from __future__ import annotations

import unittest

from learn_pi_lab.labs.agent_loop import (
    FinalText,
    ScriptedModel,
    ToolRequest,
    run_scripted_loop,
)


class AgentLoopTests(unittest.TestCase):
    def test_scripted_agent_loop_runs_a_tool_then_returns_final_text(self) -> None:
        received: list[dict[str, object]] = []

        def list_files(arguments: dict[str, object]) -> list[str]:
            received.append(arguments)
            return ["a.py"]

        trace = run_scripted_loop(
            "list the files",
            ScriptedModel.tool_then_text("list_files", {"directory": "."}, "done"),
            {"list_files": list_files},
        )

        self.assertEqual("done", trace.final_text)
        self.assertEqual(("list_files",), trace.tool_names)
        self.assertEqual(2, trace.turns)
        self.assertEqual((), trace.errors)
        self.assertEqual([{"directory": "."}], received)

    def test_unknown_tool_records_a_structured_error_without_running_an_executor(self) -> None:
        calls: list[dict[str, object]] = []
        trace = run_scripted_loop(
            "try a missing tool",
            ScriptedModel([ToolRequest("missing_tool", {"value": 1})]),
            {"known_tool": lambda arguments: calls.append(arguments)},
        )

        self.assertIsNone(trace.final_text)
        self.assertEqual(("missing_tool",), trace.tool_names)
        self.assertEqual(1, trace.turns)
        self.assertEqual([], calls)
        self.assertEqual("unknown_tool", trace.errors[0].code)
        self.assertEqual("missing_tool", trace.errors[0].tool_name)

    def test_loop_stops_with_a_structured_error_after_max_turns(self) -> None:
        calls: list[int] = []
        model = ScriptedModel(
            [
                ToolRequest("count", {"value": 1}),
                ToolRequest("count", {"value": 2}),
                FinalText("this turn must not be read"),
            ]
        )

        trace = run_scripted_loop(
            "count twice",
            model,
            {"count": lambda arguments: calls.append(int(arguments["value"]))},
            max_turns=2,
        )

        self.assertIsNone(trace.final_text)
        self.assertEqual(("count", "count"), trace.tool_names)
        self.assertEqual(2, trace.turns)
        self.assertEqual([1, 2], calls)
        self.assertEqual("max_turns_exceeded", trace.errors[0].code)

    def test_malformed_tool_request_records_an_error_before_tool_lookup(self) -> None:
        calls: list[dict[str, object]] = []

        trace = run_scripted_loop(
            "use a malformed request",
            ScriptedModel([ToolRequest([], {})]),
            {"known_tool": lambda arguments: calls.append(arguments)},
        )

        self.assertIsNone(trace.final_text)
        self.assertEqual((), trace.tool_names)
        self.assertEqual([], calls)
        self.assertEqual("invalid_scripted_step", trace.errors[0].code)

    def test_model_snapshots_arguments_and_trace_collections_are_immutable(self) -> None:
        arguments: dict[str, object] = {"directory": "."}
        model = ScriptedModel([ToolRequest("list_files", arguments), FinalText("done")])
        arguments["directory"] = "changed-after-construction"
        received: list[dict[str, object]] = []

        trace = run_scripted_loop(
            "list files",
            model,
            {"list_files": lambda values: received.append(dict(values))},
        )

        self.assertEqual([{"directory": "."}], received)
        self.assertIsInstance(trace.tool_names, tuple)
        self.assertIsInstance(trace.errors, tuple)
        with self.assertRaises(AttributeError):
            trace.tool_names.append("another_tool")  # type: ignore[attr-defined]


if __name__ == "__main__":
    unittest.main()
