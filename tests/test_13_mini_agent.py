"""Behavior tests for the minimal Tau-inspired agent loop."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from learn_pi_lab.labs.mini_agent import (
    AgentEndEvent,
    AgentHarness,
    AgentTool,
    AgentToolResult,
    AssistantMessage,
    MessageEndEvent,
    ToolCall,
    ToolExecutionUpdateEvent,
    ToolResultMessage,
    UserMessage,
    demo_trace,
    dump_messages,
    load_messages,
    run_agent_loop,
    scripted_provider,
)


def _demo_tools() -> list[AgentTool]:
    return [
        AgentTool(
            name="list_files",
            description="List files",
            parameters={"directory": {"type": "string"}},
            execute_fn=lambda arguments, on_update=None: AgentToolResult(
                "lesson.md" if arguments.get("directory") else "lesson.md"
            ),
        )
    ]


class MiniAgentLoopTests(unittest.TestCase):
    def test_demo_trace_runs_tool_then_stops_with_expected_events(self) -> None:
        event_types, final_texts, loaded_roles = demo_trace()

        self.assertEqual(("Lesson files listed.",), final_texts)
        # JSONL round trip preserves the full transcript role sequence.
        self.assertEqual(("user", "assistant", "toolResult", "assistant"), loaded_roles)
        self.assertEqual("agent_start", event_types[0])
        self.assertEqual("agent_end", event_types[-1])
        self.assertIn("tool_execution_start", event_types)
        self.assertIn("tool_execution_update", event_types)
        self.assertIn("tool_execution_end", event_types)
        self.assertIn("turn_end", event_types)

    def test_loop_persists_prompt_tool_result_and_final_text(self) -> None:
        tools = _demo_tools()
        provider = scripted_provider(
            [
                AssistantMessage(
                    content="",
                    tool_calls=(ToolCall("call-1", "list_files", {"directory": "."}),),
                    stop_reason="toolUse",
                ),
                AssistantMessage(content="done", stop_reason="stop"),
            ]
        )
        messages: list[object] = []

        events = list(
            run_agent_loop(
                provider=provider,
                model="demo",
                system="system",
                messages=messages,  # type: ignore[arg-type]
                prompt="list files",
                tools=tools,
            )
        )

        self.assertIsInstance(events[-1], AgentEndEvent)
        roles = [message.role for message in events[-1].messages]
        self.assertEqual(["user", "assistant", "toolResult", "assistant"], roles)
        self.assertIsInstance(events[-1].messages[2], ToolResultMessage)
        self.assertEqual("list_files", events[-1].messages[2].tool_name)

    def test_unknown_tool_becomes_an_error_result(self) -> None:
        provider = scripted_provider(
            [
                AssistantMessage(
                    content="",
                    tool_calls=(ToolCall("call-1", "missing_tool", {}),),
                    stop_reason="toolUse",
                ),
                AssistantMessage(content="done", stop_reason="stop"),
            ]
        )
        messages: list[object] = []

        list(
            run_agent_loop(
                provider=provider,
                model="demo",
                system="system",
                messages=messages,  # type: ignore[arg-type]
                prompt="use a missing tool",
                tools=_demo_tools(),
            )
        )

        result = messages[2]
        self.assertIsInstance(result, ToolResultMessage)
        self.assertTrue(result.is_error)
        self.assertIn("unknown tool", result.content)

    def test_tool_exception_is_isolated_into_an_error_result(self) -> None:
        def explode(
            arguments: dict[str, object], on_update: object = None
        ) -> AgentToolResult:
            del arguments, on_update
            raise RuntimeError("boom")

        tools = [
            AgentTool(
                name="explode",
                description="Always fails",
                parameters={},
                execute_fn=explode,
            )
        ]
        provider = scripted_provider(
            [
                AssistantMessage(
                    content="",
                    tool_calls=(ToolCall("call-1", "explode", {}),),
                    stop_reason="toolUse",
                ),
                AssistantMessage(content="done", stop_reason="stop"),
            ]
        )
        messages: list[object] = []

        list(
            run_agent_loop(
                provider=provider,
                model="demo",
                system="system",
                messages=messages,  # type: ignore[arg-type]
                prompt="run the failing tool",
                tools=tools,
            )
        )

        result = messages[2]
        self.assertIsInstance(result, ToolResultMessage)
        self.assertTrue(result.is_error)
        self.assertIn("RuntimeError: boom", result.content)

    def test_tool_updates_emit_streaming_events(self) -> None:
        def streaming(
            arguments: dict[str, object], on_update: object = None
        ) -> AgentToolResult:
            del arguments
            on_update("progress...")  # type: ignore[operator]
            return AgentToolResult("done")

        tools = [
            AgentTool(
                name="streaming",
                description="Streams progress",
                parameters={},
                execute_fn=streaming,
            )
        ]
        provider = scripted_provider(
            [
                AssistantMessage(
                    content="",
                    tool_calls=(ToolCall("call-1", "streaming", {}),),
                    stop_reason="toolUse",
                ),
                AssistantMessage(content="done", stop_reason="stop"),
            ]
        )

        updates = [
            event
            for event in run_agent_loop(
                provider=provider,
                model="demo",
                system="system",
                messages=[],  # type: ignore[arg-type]
                prompt="stream",
                tools=tools,
            )
            if isinstance(event, ToolExecutionUpdateEvent)
        ]

        self.assertEqual(1, len(updates))
        self.assertEqual("streaming", updates[0].tool_name)
        self.assertEqual("progress...", updates[0].partial_result.content)

    def test_max_turns_exceeded_ends_with_an_error_message(self) -> None:
        provider = scripted_provider(
            [
                AssistantMessage(
                    content="",
                    tool_calls=(ToolCall("call-1", "list_files", {}),),
                    stop_reason="toolUse",
                )
            ]
        )
        messages: list[object] = []

        events = list(
            run_agent_loop(
                provider=provider,
                model="demo",
                system="system",
                messages=messages,  # type: ignore[arg-type]
                prompt="loop forever",
                tools=_demo_tools(),
                max_turns=1,
            )
        )

        final = events[-1]
        self.assertIsInstance(final, AgentEndEvent)
        self.assertEqual("error", final.messages[-1].stop_reason)

    def test_exhausted_provider_becomes_an_error_message(self) -> None:
        # The script has no assistant message; ``next()`` raises StopIteration.
        provider = scripted_provider([])
        messages: list[object] = []

        events = list(
            run_agent_loop(
                provider=provider,
                model="demo",
                system="system",
                messages=messages,  # type: ignore[arg-type]
                prompt="hello",
                tools=[],
            )
        )

        final = events[-1]
        self.assertIsInstance(final, AgentEndEvent)
        self.assertEqual("error", final.messages[-1].stop_reason)

    def test_loop_emits_message_events_for_every_persisted_message(self) -> None:
        provider = scripted_provider(
            [
                AssistantMessage(content="hi", stop_reason="stop"),
            ]
        )
        messages: list[object] = []

        ended = [
            event.message
            for event in run_agent_loop(
                provider=provider,
                model="demo",
                system="system",
                messages=messages,  # type: ignore[arg-type]
                prompt="hello",
                tools=[],
            )
            if isinstance(event, MessageEndEvent)
        ]

        self.assertEqual(2, len(ended))  # user prompt + assistant reply
        self.assertIsInstance(ended[0], UserMessage)
        self.assertIsInstance(ended[1], AssistantMessage)


class MiniAgentHarnessTests(unittest.TestCase):
    def test_subscribe_broadcasts_events_and_unsubscribe_stops_them(self) -> None:
        provider = scripted_provider(
            [
                AssistantMessage(content="hi", stop_reason="stop"),
                AssistantMessage(content="again", stop_reason="stop"),
            ]
        )
        harness = AgentHarness(provider=provider, model="demo", system="system", tools=[])
        seen: list[str] = []

        unsubscribe = harness.subscribe(lambda event: seen.append(event.type))
        harness.prompt("hello")
        self.assertEqual("agent_start", seen[0])
        self.assertEqual("agent_end", seen[-1])

        unsubscribe()
        seen.clear()
        harness.prompt("hello again")
        self.assertEqual([], seen)

    def test_harness_accumulates_messages_across_prompts(self) -> None:
        provider = scripted_provider(
            [
                AssistantMessage(content="one", stop_reason="stop"),
                AssistantMessage(content="two", stop_reason="stop"),
            ]
        )
        harness = AgentHarness(provider=provider, model="demo", system="system", tools=[])

        harness.prompt("first")
        harness.prompt("second")

        roles = [message.role for message in harness.messages]
        self.assertEqual(["user", "assistant", "user", "assistant"], roles)


class MiniAgentSessionTests(unittest.TestCase):
    def test_jsonl_round_trip_preserves_messages_and_append_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "session.jsonl"
            dump_messages([UserMessage(content="hi")], path)
            dump_messages([AssistantMessage(content="yo", stop_reason="stop")], path)

            loaded = load_messages(path)

        self.assertEqual(("user", "assistant"), tuple(message.role for message in loaded))
        self.assertEqual("hi", loaded[0].content)
        self.assertEqual("yo", loaded[1].content)

    def test_jsonl_round_trip_preserves_tool_calls(self) -> None:
        assistant = AssistantMessage(
            content="",
            tool_calls=(ToolCall("call-1", "list_files", {"directory": "."}),),
            stop_reason="toolUse",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "session.jsonl"
            dump_messages([assistant], path)
            loaded = load_messages(path)

        self.assertEqual(1, len(loaded))
        restored = loaded[0]
        self.assertIsInstance(restored, AssistantMessage)
        self.assertEqual("toolUse", restored.stop_reason)
        self.assertEqual("call-1", restored.tool_calls[0].id)
        self.assertEqual({"directory": "."}, dict(restored.tool_calls[0].arguments))

    def test_jsonl_preserves_unknown_records_verbatim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "session.jsonl"
            path.write_text('{"role":"futureRole","x":1}\n', encoding="utf-8")
            loaded = load_messages(path)

        # Unknown records are kept as dicts, never silently rewritten.
        self.assertEqual(1, len(loaded))
        self.assertEqual({"role": "futureRole", "x": 1}, loaded[0])


if __name__ == "__main__":
    unittest.main()
