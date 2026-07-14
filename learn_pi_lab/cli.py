"""Command-line entry point for the dependency-free course labs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from . import __version__
from .labs.agent_loop import ScriptedModel, run_scripted_loop
from .labs.context_files import (
    InvalidBoundary,
    InvalidStart,
    RuleFileUnavailable,
    UnsafeRulePath,
    discover_rules,
    merge_rules,
)
from .labs.compaction import COMPACTION_FIXTURE, compact
from .labs.extension_events import LessonEventBus
from .labs.provider_registry import ProviderRegistry
from .labs.reliability import retry
from .labs.resources import UnknownLessonResource, load_resource, scan_lesson_resources
from .labs.rpc_jsonl import JsonlRpcCodec
from .labs.session_tree import (
    SESSION_TREE_FIXTURE,
    TranscriptTree,
    UnknownTranscriptEntry,
)
from .labs.tool_permissions import CommandRequest, Policy, dispatch_if_allowed


def _run_agent_loop_lab() -> int:
    """Print a fixed, offline trace for the agent-loop teaching lab."""
    trace = run_scripted_loop(
        "List the lesson files.",
        ScriptedModel.tool_then_text("list_files", {}, "Lesson files listed."),
        {"list_files": lambda arguments: ["lesson.md"]},
    )
    print(
        json.dumps(
            {
                "errors": [
                    {
                        "code": error.code,
                        "message": error.message,
                        "tool_name": error.tool_name,
                        "turn": error.turn,
                    }
                    for error in trace.errors
                ],
                "final_text": trace.final_text,
                "tool_names": trace.tool_names,
                "turns": trace.turns,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def _run_permissions_lab() -> int:
    """Print a fixed denied request without invoking its injected executor."""
    outcome = dispatch_if_allowed(
        CommandRequest("rm -rf /"),
        Policy.read_only(Path.cwd()),
        lambda request: "unreachable",
    )
    print(
        json.dumps(
            {
                "allowed": outcome.decision.allowed,
                "executed": outcome.executed,
                "reason": outcome.decision.reason,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def _run_context_files_lab(directory: Path, boundary: Path | None) -> int:
    """Print the deterministic course-rule bundle for one directory."""
    try:
        bundle = merge_rules(discover_rules(directory, boundary=boundary))
    except (InvalidStart, InvalidBoundary, RuleFileUnavailable, UnsafeRulePath) as error:
        print(f"context-files: {error}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "paths": [str(path) for path in bundle.paths],
                "lines": list(bundle.lines),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def _run_session_tree_lab(leaf_id: str) -> int:
    """Print one deterministic root-to-leaf branch from the teaching fixture."""
    try:
        path = TranscriptTree(SESSION_TREE_FIXTURE).path_to(leaf_id)
    except UnknownTranscriptEntry as error:
        print(f"session-tree: {error}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "path_ids": [entry.id for entry in path],
                "texts": [entry.text for entry in path],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def _run_compaction_lab() -> int:
    """Print a fixed, offline compaction plan from course-local transcript units."""
    plan = compact(COMPACTION_FIXTURE, keep_units=2)
    print(
        json.dumps(
            {
                "kept_ids": [unit.id for unit in plan.kept],
                "summarized_ids": [unit.id for unit in plan.summarized],
                "summary": {
                    "count": plan.summary.count,
                    "unit_ids": list(plan.summary.unit_ids),
                    "roles": list(plan.summary.roles),
                    "text_preview": list(plan.summary.text_preview),
                },
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def _run_events_lab() -> int:
    """Print a deterministic event order without using Pi extension APIs."""
    bus = LessonEventBus()
    bus.on("turn", lambda payload: "first")
    bus.on("turn", lambda payload: "second")
    outcomes = bus.emit("turn", {"lesson": "events"})
    print(
        json.dumps(
            {
                "outcomes": [
                    {
                        "error": outcome.error,
                        "handler_index": outcome.handler_index,
                        "status": outcome.status,
                        "value": outcome.value,
                    }
                    for outcome in outcomes
                ]
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def _run_resources_lab(directory: Path, name: str) -> int:
    """Print one scanned course-resource snapshot without loading Pi Skills."""
    catalog = scan_lesson_resources((directory,))
    try:
        resource = load_resource(catalog, name)
    except UnknownLessonResource as error:
        print(f"resources: {error}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "name": resource.name,
                "description": resource.description,
                "body": resource.body,
                "path": str(resource.path),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def _run_providers_lab() -> int:
    """Print a single non-sensitive model catalog entry."""
    registry = ProviderRegistry()
    registry.register("openai-completions", "demo-1", "Demo Model", 128_000)
    print(
        json.dumps(
            {
                "models": [
                    {
                        "provider_id": model.provider_id,
                        "model_id": model.model_id,
                        "display_name": model.display_name,
                        "context_window": model.context_window,
                    }
                    for model in registry.catalog()
                ]
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def _run_reliability_lab() -> int:
    """Print a retry trace with injected no-op sleeping."""
    attempts = 0

    def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError("temporary")
        return "ready"

    result = retry(operation, attempts=2, base_delay=0.1, sleep=lambda delay: None)
    print(
        json.dumps(
            {"value": result.value, "attempts": result.attempts, "delays": list(result.delays)},
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def _run_rpc_jsonl_lab() -> int:
    """Print one validated course-local JSONL request."""
    message = JsonlRpcCodec().feed(
        '{"id":"demo","method":"ping","params":{"course":"learn-pi"}}\n'
    )[0]
    print(
        json.dumps(
            {"id": message.id, "method": message.method, "params": message.params},
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Print the available course-lab entry points."""
    parser = argparse.ArgumentParser(description="Offline Learn Pi Python labs")
    parser.add_argument("--version", action="store_true", help="print the lab package version")
    commands = parser.add_subparsers(dest="command")
    lab_parser = commands.add_parser("lab", help="run a deterministic course lab")
    lab_parser.add_argument(
        "name",
        nargs="?",
        choices=(
            "agent-loop",
            "permissions",
            "context-files",
            "session-tree",
            "compaction",
            "resources",
            "events",
            "providers",
            "reliability",
            "rpc-jsonl",
        ),
    )
    lab_parser.add_argument("directory", nargs="?", type=Path)
    lab_parser.add_argument("--boundary", type=Path)
    lab_parser.add_argument("--leaf")
    lab_parser.add_argument("--name", dest="resource_name")
    arguments = parser.parse_args(argv)

    if arguments.version:
        print(__version__)
    elif arguments.command == "lab" and arguments.name == "agent-loop":
        return _run_agent_loop_lab()
    elif arguments.command == "lab" and arguments.name == "permissions":
        return _run_permissions_lab()
    elif arguments.command == "lab" and arguments.name == "context-files":
        if arguments.directory is None:
            print("context-files: a directory argument is required", file=sys.stderr)
            return 2
        return _run_context_files_lab(arguments.directory, arguments.boundary)
    elif arguments.command == "lab" and arguments.name == "session-tree":
        if arguments.directory is not None or arguments.boundary is not None:
            print(
                "session-tree: positional directory and --boundary are not supported",
                file=sys.stderr,
            )
            return 2
        return _run_session_tree_lab(arguments.leaf or "leaf")
    elif arguments.command == "lab" and arguments.name == "compaction":
        if (
            arguments.directory is not None
            or arguments.boundary is not None
            or arguments.leaf is not None
        ):
            print(
                "compaction: positional directory, --boundary, and --leaf are not supported",
                file=sys.stderr,
            )
            return 2
        return _run_compaction_lab()
    elif arguments.command == "lab" and arguments.name == "resources":
        if arguments.directory is None:
            print("resources: a directory argument is required", file=sys.stderr)
            return 2
        if arguments.boundary is not None or arguments.leaf is not None:
            print("resources: --boundary and --leaf are not supported", file=sys.stderr)
            return 2
        if arguments.resource_name is None:
            print("resources: --name is required", file=sys.stderr)
            return 2
        return _run_resources_lab(arguments.directory, arguments.resource_name)
    elif arguments.command == "lab" and arguments.name == "events":
        if (
            arguments.directory is not None
            or arguments.boundary is not None
            or arguments.leaf is not None
            or arguments.resource_name is not None
        ):
            print(
                "events: positional directory, --boundary, --leaf, and --name are not supported",
                file=sys.stderr,
            )
            return 2
        return _run_events_lab()
    elif arguments.command == "lab" and arguments.name in {
        "providers",
        "reliability",
        "rpc-jsonl",
    }:
        if (
            arguments.directory is not None
            or arguments.boundary is not None
            or arguments.leaf is not None
            or arguments.resource_name is not None
        ):
            print(
                f"{arguments.name}: positional directory and shared options are not supported",
                file=sys.stderr,
            )
            return 2
        if arguments.name == "providers":
            return _run_providers_lab()
        if arguments.name == "reliability":
            return _run_reliability_lab()
        return _run_rpc_jsonl_lab()
    elif arguments.command == "lab":
        lab_parser.print_help()
        return 2
    else:
        parser.print_help()
    return 0
