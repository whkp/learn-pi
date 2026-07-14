"""Tests for deterministic retry and bounded-error teaching helpers."""

from __future__ import annotations

import unittest

from learn_pi_lab.labs.reliability import RetryExhausted, retry


class ReliabilityTests(unittest.TestCase):
    def test_retry_returns_the_first_success_and_records_backoff_delays(self) -> None:
        attempts: list[int] = []
        delays: list[float] = []

        def operation() -> str:
            attempts.append(1)
            if len(attempts) < 3:
                raise OSError("temporary")
            return "ready"

        result = retry(operation, attempts=3, base_delay=0.25, sleep=delays.append)

        self.assertEqual("ready", result.value)
        self.assertEqual(3, result.attempts)
        self.assertEqual((0.25, 0.5), result.delays)
        self.assertEqual([0.25, 0.5], delays)

    def test_retry_exhaustion_exposes_a_safe_summary_without_traceback(self) -> None:
        def failing_operation() -> None:
            raise ValueError("secret token must not escape")

        with self.assertRaises(RetryExhausted) as raised:
            retry(failing_operation, attempts=2, base_delay=1, sleep=lambda delay: None)

        error = raised.exception
        self.assertEqual(2, error.attempts)
        self.assertEqual("ValueError", error.error_type)
        self.assertEqual("operation failed after 2 attempts (ValueError)", str(error))

    def test_retry_rejects_invalid_configuration(self) -> None:
        for attempts, base_delay in ((0, 0), (1, -1), (True, 0)):
            with self.subTest(attempts=attempts, base_delay=base_delay):
                with self.assertRaises(ValueError):
                    retry(lambda: "unused", attempts=attempts, base_delay=base_delay)


if __name__ == "__main__":
    unittest.main()
