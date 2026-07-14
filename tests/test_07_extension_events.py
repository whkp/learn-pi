"""Behavior tests for the course-local extension-events teaching model."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import unittest

from learn_pi_lab.cli import main
from learn_pi_lab.labs.extension_events import LessonEventBus


class ExtensionEventsTests(unittest.TestCase):
    def test_handlers_run_in_registration_order(self) -> None:
        bus = LessonEventBus()
        calls: list[str] = []
        bus.on("turn", lambda payload: calls.append("first") or "first value")
        bus.on("turn", lambda payload: calls.append("second") or "second value")

        outcomes = bus.emit("turn", {"id": 1})

        self.assertEqual(["first", "second"], calls)
        self.assertEqual(("ok", "ok"), tuple(outcome.status for outcome in outcomes))
        self.assertEqual((0, 1), tuple(outcome.handler_index for outcome in outcomes))
        self.assertEqual(("first value", "second value"), tuple(outcome.value for outcome in outcomes))

    def test_handler_error_is_data_and_later_handler_runs(self) -> None:
        bus = LessonEventBus()
        calls: list[str] = []

        def failing_handler(payload: object) -> object:
            calls.append("failing")
            raise ValueError("lesson failure")

        bus.on("turn", failing_handler)
        bus.on("turn", lambda payload: calls.append("later") or "later value")

        outcomes = bus.emit("turn", {"id": 1})

        self.assertEqual(["failing", "later"], calls)
        self.assertEqual(("error", "ok"), tuple(outcome.status for outcome in outcomes))
        self.assertIn("ValueError: lesson failure", outcomes[0].error or "")
        self.assertEqual("later value", outcomes[1].value)

    def test_unsubscribe_is_idempotent_and_cannot_remove_later_handler(self) -> None:
        bus = LessonEventBus()
        calls: list[str] = []
        first = bus.on("turn", lambda payload: calls.append("first"))
        first.unsubscribe()
        first.unsubscribe()
        bus.on("turn", lambda payload: calls.append("later"))

        outcomes = bus.emit("turn", {"id": 1})

        self.assertEqual(["later"], calls)
        self.assertEqual(1, len(outcomes))
        self.assertEqual("ok", outcomes[0].status)

    def test_payload_is_deeply_frozen_for_handlers_and_original_mapping(self) -> None:
        bus = LessonEventBus()
        original = {"nested": {"items": ["safe"]}}
        observed: list[object] = []

        def mutating_handler(payload: object) -> None:
            nested = payload["nested"]  # type: ignore[index]
            try:
                nested["items"].append("changed")  # type: ignore[index,union-attr]
            except AttributeError:
                pass

        def observing_handler(payload: object) -> object:
            nested = payload["nested"]  # type: ignore[index]
            observed.append(nested["items"])  # type: ignore[index]
            return nested["items"]  # type: ignore[index]

        bus.on("turn", mutating_handler)
        bus.on("turn", observing_handler)

        outcomes = bus.emit("turn", original)

        self.assertEqual({"nested": {"items": ["safe"]}}, original)
        self.assertEqual([("safe",)], observed)
        self.assertEqual(("ok", "ok"), tuple(outcome.status for outcome in outcomes))
        self.assertEqual(("safe",), outcomes[1].value)

    def test_payload_bytearrays_are_snapshotted_without_mutating_the_original(self) -> None:
        bus = LessonEventBus()
        original = {"buffer": bytearray(b"safe")}
        observed: list[object] = []

        def mutating_handler(payload: object) -> None:
            buffer = payload["buffer"]  # type: ignore[index]
            with self.assertRaises(AttributeError):
                buffer.extend(b"!")  # type: ignore[union-attr]

        def observing_handler(payload: object) -> object:
            observed.append(payload["buffer"])  # type: ignore[index]
            return payload["buffer"]  # type: ignore[index]

        bus.on("turn", mutating_handler)
        bus.on("turn", observing_handler)
        outcomes = bus.emit("turn", original)

        self.assertEqual(bytearray(b"safe"), original["buffer"])
        self.assertEqual([b"safe"], observed)
        self.assertEqual(b"safe", outcomes[1].value)

    def test_payload_rejects_unknown_mutable_values(self) -> None:
        class MutableValue:
            pass

        with self.assertRaisesRegex(TypeError, "snapshot-safe"):
            LessonEventBus().emit("turn", {"value": MutableValue()})

    def test_invalid_event_names_and_handlers_are_rejected(self) -> None:
        bus = LessonEventBus()

        with self.assertRaisesRegex(ValueError, "event name"):
            bus.on("   ", lambda payload: None)
        with self.assertRaisesRegex(TypeError, "callable"):
            bus.on("turn", object())

    def test_events_cli_prints_deterministic_status_order(self) -> None:
        output = StringIO()

        with redirect_stdout(output):
            exit_code = main(["lab", "events"])

        self.assertEqual(0, exit_code)
        self.assertEqual(
            {
                "outcomes": [
                    {"error": None, "handler_index": 0, "status": "ok", "value": "first"},
                    {"error": None, "handler_index": 1, "status": "ok", "value": "second"},
                ]
            },
            json.loads(output.getvalue()),
        )

    def test_events_cli_rejects_irrelevant_shared_arguments(self) -> None:
        for arguments in (
            ["lab", "events", "unexpected-positional"],
            ["lab", "events", "--boundary", "."],
            ["lab", "events", "--leaf", "ignored"],
            ["lab", "events", "--name", "ignored"],
        ):
            with self.subTest(arguments=arguments):
                output = StringIO()
                error = StringIO()

                with redirect_stdout(output), redirect_stderr(error):
                    exit_code = main(arguments)

                self.assertEqual(2, exit_code)
                self.assertEqual("", output.getvalue())
                self.assertIn("events:", error.getvalue())


if __name__ == "__main__":
    unittest.main()
