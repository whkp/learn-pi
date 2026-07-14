"""Tests for the four offline, practical course mini-projects."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from projects.ci_review_pipeline import build_review_report
from projects.rpc_console import handle_request
from projects.safe_review_runner import ReviewPolicy, review_request
from projects.session_inspector import inspect_session_jsonl


class PracticalProjectsTests(unittest.TestCase):
    def test_session_inspector_counts_valid_jsonl_roles_without_executing_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory) / "session.jsonl"
            session.write_text(
                '{"type":"message","message":{"role":"user"}}\n'
                '{"type":"message","message":{"role":"assistant"}}\n'
                '{"type":"compaction"}\n',
                encoding="utf-8",
            )

            report = inspect_session_jsonl(session)

        self.assertEqual(3, report.entries)
        self.assertEqual({"assistant": 1, "user": 1}, dict(report.roles))
        self.assertEqual(1, report.compactions)

    def test_safe_review_runner_allows_only_read_only_tool_intents(self) -> None:
        policy = ReviewPolicy(root=Path("/workspace"))

        allowed = review_request(policy, "read", "src/app.py")
        blocked = review_request(policy, "shell", "rm -rf /")

        self.assertTrue(allowed.allowed)
        self.assertEqual("/workspace/src/app.py", allowed.normalized_target)
        self.assertFalse(blocked.allowed)
        self.assertIsNone(blocked.normalized_target)

    def test_ci_review_pipeline_reports_each_completed_check(self) -> None:
        report = build_review_report(
            markdown_links_ok=True,
            course_contract_ok=True,
            unit_tests_ok=False,
        )

        self.assertFalse(report.passed)
        self.assertEqual(("course-contract", "markdown-links"), report.passed_checks)
        self.assertEqual(("unit-tests",), report.failed_checks)

    def test_rpc_console_returns_json_safe_response_for_a_supported_method(self) -> None:
        response = handle_request('{"id":"1","method":"ping","params":{}}')

        self.assertEqual({"id": "1", "result": {"ok": True, "value": "pong"}}, json.loads(response))


if __name__ == "__main__":
    unittest.main()
