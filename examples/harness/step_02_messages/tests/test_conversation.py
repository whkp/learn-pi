"""B02 测试：messages 多轮历史。"""

from __future__ import annotations

import unittest

from step_02_messages.conversation import conversation, mock_chat


class ConversationTests(unittest.TestCase):
    def test_history_alternates_roles(self) -> None:
        history = conversation()
        roles = [m["role"] for m in history]
        self.assertEqual(roles, ["user", "assistant"] * 3)

    def test_mock_uses_full_history(self) -> None:
        reply = mock_chat(
            [
                {"role": "user", "content": "第一问"},
                {"role": "assistant", "content": "第一答"},
                {"role": "user", "content": "第二问"},
            ]
        )
        self.assertIn("3 条消息", reply)
        self.assertIn("第二问", reply)


if __name__ == "__main__":
    unittest.main()
