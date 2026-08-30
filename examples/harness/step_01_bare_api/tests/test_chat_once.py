"""B01 测试：裸 API 调用。"""

from __future__ import annotations

import unittest

from step_01_bare_api.chat_once import chat_once


class ChatOnceTests(unittest.TestCase):
    def test_returns_model_reply(self) -> None:
        reply = chat_once("hello")
        self.assertIn("hello", reply)

    def test_reply_is_plain_text(self) -> None:
        reply = chat_once("什么是 agent？")
        self.assertIsInstance(reply, str)
        self.assertTrue(reply)


if __name__ == "__main__":
    unittest.main()
