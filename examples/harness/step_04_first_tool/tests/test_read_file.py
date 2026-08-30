"""B04 测试：第一个工具与五步闭环。"""

from __future__ import annotations

import unittest

from step_04_first_tool.read_file import TOOLS, Message, agent_loop, read_file


class FirstToolTests(unittest.TestCase):
    def test_read_file_returns_content(self) -> None:
        self.assertIn("lesson.md", read_file("lesson.md"))

    def test_loop_runs_tool_then_stops(self) -> None:
        messages = agent_loop("读一下 lesson.md")
        roles = [m.role for m in messages]
        # user → assistant(请求工具) → toolResult → assistant(结束)
        self.assertEqual(roles, ["user", "assistant", "toolResult", "assistant"])

    def test_tool_result_fed_back_to_messages(self) -> None:
        messages = agent_loop("读一下 lesson.md")
        result = messages[2]
        self.assertEqual("toolResult", result.role)
        self.assertIn("文件内容", result.content)


if __name__ == "__main__":
    unittest.main()
