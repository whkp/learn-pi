"""Smoke tests for the newer deterministic Python lab commands."""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
import unittest

from learn_pi_lab.cli import main


class ExtendedCliTests(unittest.TestCase):
    def test_provider_registry_lab_prints_a_deterministic_catalog(self) -> None:
        output = StringIO()

        with redirect_stdout(output):
            exit_code = main(["lab", "providers"])

        self.assertEqual(0, exit_code)
        self.assertEqual(
            {
                "models": [
                    {
                        "context_window": 128000,
                        "display_name": "Demo Model",
                        "model_id": "demo-1",
                        "provider_id": "openai-completions",
                    }
                ]
            },
            json.loads(output.getvalue()),
        )

    def test_reliability_lab_prints_retry_metadata_without_sleeping(self) -> None:
        output = StringIO()

        with redirect_stdout(output):
            exit_code = main(["lab", "reliability"])

        self.assertEqual(0, exit_code)
        self.assertEqual(
            {"attempts": 2, "delays": [0.1], "value": "ready"},
            json.loads(output.getvalue()),
        )

    def test_rpc_lab_prints_one_validated_request(self) -> None:
        output = StringIO()

        with redirect_stdout(output):
            exit_code = main(["lab", "rpc-jsonl"])

        self.assertEqual(0, exit_code)
        self.assertEqual(
            {"id": "demo", "method": "ping", "params": {"course": "learn-pi"}},
            json.loads(output.getvalue()),
        )


if __name__ == "__main__":
    unittest.main()
