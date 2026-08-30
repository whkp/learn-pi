"""B06 测试：工具结果与错误回填。"""

from __future__ import annotations

import unittest

from step_05_registry.registry import ToolRegistry
from step_06_tool_results.tool_results import execute_tool, make_flaky_tool


class ToolResultTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = ToolRegistry()
        self.registry.add(make_flaky_tool())

    def test_success_result(self) -> None:
        result = execute_tool(self.registry, "flaky", {"value": 1})
        self.assertFalse(result.is_error)
        self.assertEqual("ok: 1", result.content)

    def test_exception_becomes_is_error(self) -> None:
        result = execute_tool(self.registry, "flaky", {"value": -1})
        self.assertTrue(result.is_error)
        self.assertEqual("ValueError", result.error_type)

    def test_unknown_tool_becomes_is_error(self) -> None:
        result = execute_tool(self.registry, "missing", {})
        self.assertTrue(result.is_error)
        self.assertEqual("UnknownTool", result.error_type)

    def test_error_does_not_crash(self) -> None:
        # 错误被隔离：即使连续失败，调用方也拿到结果而不是异常
        results = [
            execute_tool(self.registry, "flaky", {"value": -1}),
            execute_tool(self.registry, "flaky", {"value": 2}),
        ]
        self.assertTrue(results[0].is_error)
        self.assertFalse(results[1].is_error)


if __name__ == "__main__":
    unittest.main()
