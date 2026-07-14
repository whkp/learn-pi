"""Behavior tests for the deterministic tool-permissions teaching model."""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from learn_pi_lab.cli import main
from learn_pi_lab.labs.tool_permissions import (
    CommandRequest,
    Policy,
    dispatch_if_allowed,
    evaluate_request,
)


class ToolPermissionsTests(unittest.TestCase):
    def test_allowed_read_request_invokes_the_injected_executor_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "workspace"
            root.mkdir()
            allowed_path = Path("notes.txt")
            request = CommandRequest("cat", (allowed_path,))
            calls: list[CommandRequest] = []

            outcome = dispatch_if_allowed(
                request,
                Policy.read_only(root),
                lambda value: calls.append(value) or "lesson notes",
            )

        self.assertTrue(outcome.decision.allowed)
        self.assertTrue(outcome.executed)
        self.assertEqual("lesson notes", outcome.result)
        self.assertEqual([CommandRequest("cat", ((root / allowed_path).resolve(),))], calls)

    def test_denied_rm_request_never_invokes_the_executor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "workspace"
            root.mkdir()
            calls: list[CommandRequest] = []

            outcome = dispatch_if_allowed(
                CommandRequest("rm -rf /"),
                Policy.read_only(root),
                lambda value: calls.append(value),
            )

        self.assertFalse(outcome.decision.allowed)
        self.assertFalse(outcome.executed)
        self.assertIsNone(outcome.result)
        self.assertEqual([], calls)
        self.assertEqual("command_must_be_a_single_allowlisted_token", outcome.decision.reason)

    def test_multi_token_command_never_invokes_the_executor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "workspace"
            root.mkdir()
            calls: list[CommandRequest] = []

            outcome = dispatch_if_allowed(
                CommandRequest("touch report.txt"),
                Policy.read_only(root),
                lambda value: calls.append(value),
            )

        self.assertFalse(outcome.decision.allowed)
        self.assertFalse(outcome.executed)
        self.assertEqual([], calls)
        self.assertEqual("command_must_be_a_single_allowlisted_token", outcome.decision.reason)

    def test_embedded_etc_passwd_command_never_invokes_the_executor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "workspace"
            root.mkdir()
            calls: list[CommandRequest] = []

            outcome = dispatch_if_allowed(
                CommandRequest("cat /etc/passwd"),
                Policy.read_only(root),
                lambda value: calls.append(value),
            )

        self.assertFalse(outcome.decision.allowed)
        self.assertFalse(outcome.executed)
        self.assertIsNone(outcome.result)
        self.assertEqual([], calls)
        self.assertEqual("command_must_be_a_single_allowlisted_token", outcome.decision.reason)

    def test_semicolon_command_never_invokes_the_executor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "workspace"
            root.mkdir()
            calls: list[CommandRequest] = []

            outcome = dispatch_if_allowed(
                CommandRequest("cat allowed.txt ; rm -rf /"),
                Policy.read_only(root),
                lambda value: calls.append(value),
            )

        self.assertFalse(outcome.decision.allowed)
        self.assertFalse(outcome.executed)
        self.assertIsNone(outcome.result)
        self.assertEqual([], calls)
        self.assertEqual("command_must_be_a_single_allowlisted_token", outcome.decision.reason)

    def test_outside_root_path_never_invokes_the_executor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "workspace"
            root.mkdir()
            calls: list[CommandRequest] = []

            outcome = dispatch_if_allowed(
                CommandRequest("cat", ("../outside.txt",)),
                Policy.read_only(root),
                lambda value: calls.append(value),
            )

        self.assertFalse(outcome.decision.allowed)
        self.assertFalse(outcome.executed)
        self.assertEqual([], calls)
        self.assertTrue(outcome.decision.reason.startswith("path_outside_root:"))

    def test_empty_command_is_denied_without_raising(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "workspace"
            root.mkdir()

            decision = evaluate_request(CommandRequest("   "), Policy.read_only(root))

        self.assertFalse(decision.allowed)
        self.assertEqual("command_must_be_a_single_allowlisted_token", decision.reason)

    def test_permissions_lab_prints_a_denied_request_as_json(self) -> None:
        output = StringIO()

        with redirect_stdout(output):
            exit_code = main(["lab", "permissions"])

        payload = json.loads(output.getvalue())
        self.assertEqual(0, exit_code)
        self.assertFalse(payload["allowed"])
        self.assertFalse(payload["executed"])
        self.assertEqual("command_must_be_a_single_allowlisted_token", payload["reason"])


if __name__ == "__main__":
    unittest.main()
