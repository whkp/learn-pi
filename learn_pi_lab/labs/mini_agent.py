"""A minimal agent loop modeled on Tau's Pi-compatible core.

Tau (``tau_agent``) is a real Python coding-agent core that mirrors Pi's
TypeScript design.  This module keeps only the smallest useful slice of that
design so the shape can be read top to bottom:

    tau_agent/messages.py      ->  role-discriminated Message dataclasses
    tau_agent/tools.py         ->  AgentTool + AgentToolResult (+ streaming updates)
    tau_agent/provider.py      ->  ModelProvider protocol
    tau_agent/events.py        ->  AgentEvent dataclasses (the contract)
    tau_agent/loop.py          ->  run_agent_loop event stream
    tau_agent/harness.py       ->  AgentHarness: subscribe() + reusable transcript
    tau_agent/session/jsonl.py ->  dump_messages / load_messages (append-only JSONL)

Tau's real loop is asyncio-based; this teaching slice is synchronous so the
event flow is easy to follow.  The contract is the same shape: frontends
consume a typed event stream, and tools are ordinary typed functions.

This is a course-local model.  It is not the Tau SDK, a Pi port, or a binding.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import tempfile
from typing import Protocol


# --- messages (tau_agent/messages.py) ---------------------------------------
# Messages are discriminated by ``role``: the same field that JSONL sessions
# use to rebuild a transcript, and that frontends use to render one message.


@dataclass(frozen=True)
class UserMessage:
    """A user prompt."""

    role: str = "user"
    content: str = ""


@dataclass(frozen=True)
class ToolCall:
    """One tool invocation requested by the assistant."""

    id: str
    name: str
    arguments: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class AssistantMessage:
    """An assistant reply: final text, tool calls, or a terminal error."""

    role: str = "assistant"
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    stop_reason: str = "stop"  # "stop" | "toolUse" | "error"


@dataclass(frozen=True)
class ToolResultMessage:
    """The result of one executed tool call, fed back to the provider."""

    role: str = "toolResult"
    tool_call_id: str = ""
    tool_name: str = ""
    content: str = ""
    is_error: bool = False


AgentMessage = UserMessage | AssistantMessage | ToolResultMessage


# --- tools (tau_agent/tools.py) ---------------------------------------------
# A tool is a schema plus an executor.  The optional ``on_update`` callback
# lets a tool stream progress text, which becomes ToolExecutionUpdateEvent.


@dataclass(frozen=True)
class AgentToolResult:
    """A deterministic tool outcome with an error flag.

    ``terminate`` 对应 Pi 的提前终止提示：本批工具全部返回 ``terminate=True``
    时，循环在发完 ``turn_end`` 后提前结束，而不是再问模型。
    """

    content: str
    is_error: bool = False
    terminate: bool = False


ToolUpdateCallback = Callable[[str], None]
ToolExecutor = Callable[[Mapping[str, object], ToolUpdateCallback | None], AgentToolResult]


@dataclass(frozen=True)
class AgentTool:
    """A typed tool: a schema plus an executor, never a magic string."""

    name: str
    description: str
    parameters: Mapping[str, object]  # JSON-schema-like metadata, kept as data
    execute_fn: ToolExecutor


# --- provider (tau_agent/provider.py) ---------------------------------------


class ModelProvider(Protocol):
    """Provider-neutral model interface; returns one assistant message."""

    def stream_response(
        self,
        *,
        model: str,
        system: str,
        messages: list[AgentMessage],
        tools: list[AgentTool],
    ) -> Iterator[AssistantMessage]:
        """Return the assistant messages for one model round."""
        ...


# --- events (tau_agent/events.py) -------------------------------------------
# Events are the contract: every observable step of a run is a typed event,
# and frontends (TUI, print mode, JSON, custom) consume exactly this stream.


@dataclass(frozen=True)
class AgentStartEvent:
    type: str = "agent_start"


@dataclass(frozen=True)
class AgentEndEvent:
    type: str = "agent_end"
    messages: tuple[AgentMessage, ...] = ()


@dataclass(frozen=True)
class TurnStartEvent:
    type: str = "turn_start"


@dataclass(frozen=True)
class TurnEndEvent:
    type: str = "turn_end"
    message: AssistantMessage = field(default_factory=AssistantMessage)


@dataclass(frozen=True)
class MessageStartEvent:
    type: str = "message_start"
    message: AgentMessage = field(default_factory=UserMessage)


@dataclass(frozen=True)
class MessageEndEvent:
    type: str = "message_end"
    message: AgentMessage = field(default_factory=UserMessage)


@dataclass(frozen=True)
class ToolExecutionStartEvent:
    type: str = "tool_execution_start"
    tool_name: str = ""
    arguments: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolExecutionUpdateEvent:
    type: str = "tool_execution_update"
    tool_name: str = ""
    partial_result: AgentToolResult = field(default_factory=lambda: AgentToolResult(""))


@dataclass(frozen=True)
class ToolExecutionEndEvent:
    type: str = "tool_execution_end"
    tool_name: str = ""
    result: AgentToolResult = field(default_factory=lambda: AgentToolResult(""))


AgentEvent = (
    AgentStartEvent
    | AgentEndEvent
    | TurnStartEvent
    | TurnEndEvent
    | MessageStartEvent
    | MessageEndEvent
    | ToolExecutionStartEvent
    | ToolExecutionUpdateEvent
    | ToolExecutionEndEvent
)


# --- loop (tau_agent/loop.py) -----------------------------------------------


def run_agent_loop(
    *,
    provider: ModelProvider,
    model: str,
    system: str,
    messages: list[AgentMessage],
    prompt: str,
    tools: list[AgentTool],
    max_turns: int = 8,
) -> Iterator[AgentEvent]:
    """Run one prompt through the provider/tool loop, yielding events.

    The ``messages`` list is the durable transcript: every message that must
    be persisted flows through ``MessageEndEvent``.
    """
    if max_turns < 1:
        raise ValueError("max_turns must be at least 1")

    messages.append(UserMessage(content=prompt))
    yield AgentStartEvent()
    yield TurnStartEvent()
    yield MessageStartEvent(message=messages[-1])
    yield MessageEndEvent(message=messages[-1])

    for turn in range(1, max_turns + 1):
        assistant = _ask_model(provider, model, system, messages, tools)
        messages.append(assistant)
        yield MessageStartEvent(message=assistant)
        yield MessageEndEvent(message=assistant)

        if assistant.stop_reason in {"stop", "error"}:
            yield TurnEndEvent(message=assistant)
            yield AgentEndEvent(messages=tuple(messages))
            return

        terminate = False
        for call in assistant.tool_calls:
            yield ToolExecutionStartEvent(tool_name=call.name, arguments=call.arguments)
            result, updates = _execute_call(call, tools)
            # Streaming progress is observable before the final result lands.
            for partial in updates:
                yield ToolExecutionUpdateEvent(
                    tool_name=call.name, partial_result=AgentToolResult(partial)
                )
            yield ToolExecutionEndEvent(tool_name=call.name, result=result)

            result_message = ToolResultMessage(
                tool_call_id=call.id,
                tool_name=call.name,
                content=result.content,
                is_error=result.is_error,
            )
            messages.append(result_message)
            yield MessageStartEvent(message=result_message)
            yield MessageEndEvent(message=result_message)

            # Pi 语义：单批并行工具中，只有全部结果都 terminate=True 才提前终止。
            # 教学模型简化为串行执行，任一结果请求终止即提前结束。
            terminate = result.terminate
            if terminate:
                break

        yield TurnEndEvent(message=assistant)
        if terminate:
            yield AgentEndEvent(messages=tuple(messages))
            return
        yield TurnStartEvent()

    error = AssistantMessage(content="", stop_reason="error")
    messages.append(error)
    yield MessageStartEvent(message=error)
    yield MessageEndEvent(message=error)
    yield TurnEndEvent(message=error)
    yield AgentEndEvent(messages=tuple(messages))


def _ask_model(
    provider: ModelProvider,
    model: str,
    system: str,
    messages: list[AgentMessage],
    tools: list[AgentTool],
) -> AssistantMessage:
    """Request one assistant message; provider failures become error messages."""
    try:
        stream = provider.stream_response(
            model=model,
            system=system,
            messages=list(messages),
            tools=tools,
        )
        return next(stream)
    except Exception:  # noqa: BLE001 - providers are an isolation boundary
        # ``StopIteration`` is an ``Exception`` subclass, so an exhausted
        # stream also lands here instead of escaping the loop.
        return AssistantMessage(content="", stop_reason="error")


def _execute_call(
    call: ToolCall, tools: list[AgentTool]
) -> tuple[AgentToolResult, tuple[str, ...]]:
    """Execute one tool call, collecting progress text; exceptions become errors."""
    tool = next((candidate for candidate in tools if candidate.name == call.name), None)
    if tool is None:
        return AgentToolResult(f"unknown tool: {call.name}", is_error=True), ()
    updates: list[str] = []
    try:
        result = tool.execute_fn(call.arguments, updates.append)
        return result, tuple(updates)
    except Exception as error:  # noqa: BLE001 - tools are an isolation boundary
        return AgentToolResult(f"{type(error).__name__}: {error}", is_error=True), tuple(updates)


# --- harness (tau_agent/harness.py) -----------------------------------------
# The loop is a pure generator; the harness wraps it with state (transcript)
# and a subscription point, so a frontend can consume the event stream.


EventListener = Callable[[AgentEvent], None]


class AgentHarness:
    """Reusable stateful agent core: subscribe to events, prompt repeatedly.

    Unlike the pure ``run_agent_loop``, the harness owns the transcript and
    lets several listeners observe every event as it is produced.
    """

    def __init__(
        self,
        *,
        provider: ModelProvider,
        model: str,
        system: str,
        tools: Iterable[AgentTool],
        max_turns: int = 8,
    ) -> None:
        self._provider = provider
        self._model = model
        self._system = system
        self._tools = tuple(tools)
        self._max_turns = max_turns
        self._messages: list[AgentMessage] = []
        self._listeners: list[EventListener] = []

    @property
    def messages(self) -> tuple[AgentMessage, ...]:
        """Immutable transcript snapshot, for persistence or inspection."""
        return tuple(self._messages)

    def subscribe(self, listener: EventListener) -> Callable[[], None]:
        """Register one event listener; the returned callable unsubscribes once."""
        self._listeners.append(listener)

        def unsubscribe() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return unsubscribe

    def prompt(self, content: str) -> tuple[AgentEvent, ...]:
        """Run one prompt, broadcasting each event to listeners, and return them."""
        events: list[AgentEvent] = []
        for event in run_agent_loop(
            provider=self._provider,
            model=self._model,
            system=self._system,
            messages=self._messages,
            prompt=content,
            tools=self._tools,
            max_turns=self._max_turns,
        ):
            events.append(event)
            for listener in tuple(self._listeners):
                listener(event)
        return tuple(events)


# --- session (tau_agent/session/jsonl.py) -----------------------------------
# Append-only JSONL: one message object per line, ``role`` is the discriminator.


def dump_messages(messages: Iterable[AgentMessage], path: Path) -> None:
    """Append a transcript to a JSONL file, one JSON object per line.

    Sessions are append-only; calling this again appends more lines.  The
    caller decides when a new file should start.
    """
    with open(path, "a", encoding="utf-8") as handle:
        for message in messages:
            handle.write(json.dumps(asdict(message), ensure_ascii=False) + "\n")


def load_messages(path: Path) -> tuple[AgentMessage | dict[str, object], ...]:
    """Read a JSONL transcript line by line, rebuilding known messages.

    Unknown records are preserved as plain dicts instead of being silently
    rewritten (course chapter 08: session files are durable data with
    compatibility constraints).
    """
    loaded: list[AgentMessage | dict[str, object]] = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            loaded.append(_from_record(json.loads(line)))
    return tuple(loaded)


def _from_record(record: dict[str, object]) -> AgentMessage | dict[str, object]:
    """Rebuild one JSON line into a known message, or return it unchanged."""
    role = record.get("role")
    if role == "user":
        return UserMessage(content=str(record.get("content", "")))
    if role == "assistant":
        calls = tuple(
            ToolCall(
                id=str(call["id"]),
                name=str(call["name"]),
                arguments=dict(call.get("arguments", {})),
            )
            for call in record.get("tool_calls", [])
            if isinstance(call, dict)
        )
        return AssistantMessage(
            content=str(record.get("content", "")),
            tool_calls=calls,
            stop_reason=str(record.get("stop_reason", "stop")),
        )
    if role == "toolResult":
        return ToolResultMessage(
            tool_call_id=str(record.get("tool_call_id", "")),
            tool_name=str(record.get("tool_name", "")),
            content=str(record.get("content", "")),
            is_error=bool(record.get("is_error", False)),
        )
    return record


# --- demo (mirrors tau_ai/fake.py) ------------------------------------------


def scripted_provider(script: list[AssistantMessage]) -> ModelProvider:
    """Build a deterministic provider that replays fixed assistant messages."""

    queue = list(script)

    class _Scripted:
        def stream_response(
            self,
            *,
            model: str,
            system: str,
            messages: list[AgentMessage],
            tools: list[AgentTool],
        ) -> Iterator[AssistantMessage]:
            del model, system, messages, tools

            def generate() -> Iterator[AssistantMessage]:
                if queue:
                    yield queue.pop(0)

            return generate()

    return _Scripted()


def _demo_list_files(
    arguments: Mapping[str, object],
    on_update: ToolUpdateCallback | None = None,
) -> AgentToolResult:
    """A tool that streams progress text, then returns its final result."""
    del arguments
    if on_update is not None:
        on_update("scanning lesson files...")
    return AgentToolResult("lesson.md, mini_agent.py")


def demo_trace() -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """Return ``(event_types, final_texts, loaded_roles)`` for the demo run.

    ``loaded_roles`` proves the JSONL round trip: dump the transcript, read it
    back, and compare the role sequence against the original messages.
    """
    tools = [
        AgentTool(
            name="list_files",
            description="List files in the lesson directory",
            parameters={"directory": {"type": "string"}},
            execute_fn=_demo_list_files,
        )
    ]
    provider = scripted_provider(
        [
            AssistantMessage(
                content="",
                tool_calls=(ToolCall("call-1", "list_files", {"directory": "."}),),
                stop_reason="toolUse",
            ),
            AssistantMessage(content="Lesson files listed.", stop_reason="stop"),
        ]
    )
    harness = AgentHarness(
        provider=provider,
        model="demo-1",
        system="You are a helpful assistant.",
        tools=tools,
    )
    event_types: list[str] = []
    harness.subscribe(lambda event: event_types.append(event.type))
    harness.prompt("List the lesson files.")

    handle, raw_path = tempfile.mkstemp(suffix=".jsonl")
    os.close(handle)
    path = Path(raw_path)
    try:
        dump_messages(harness.messages, path)
        loaded_roles = tuple(message.role for message in load_messages(path))
    finally:
        path.unlink(missing_ok=True)

    final_texts = tuple(
        message.content
        for message in harness.messages
        if isinstance(message, AssistantMessage) and message.content
    )
    return tuple(event_types), final_texts, loaded_roles
