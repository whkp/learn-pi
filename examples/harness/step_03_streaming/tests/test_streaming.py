"""B03 测试：流式输出。"""

from __future__ import annotations

import unittest

from step_03_streaming.streaming import collect, stream_reply


class StreamingTests(unittest.TestCase):
    def test_stream_pieces_reassemble_to_full_text(self) -> None:
        text = "流式输出让等待变成可见的进度。"
        self.assertEqual(text, collect(stream_reply(text)))

    def test_stream_yields_multiple_pieces(self) -> None:
        pieces = list(stream_reply("abcdef", chunk_size=2))
        self.assertEqual(pieces, ["ab", "cd", "ef"])

    def test_empty_text_streams_nothing(self) -> None:
        self.assertEqual("", collect(stream_reply("")))


if __name__ == "__main__":
    unittest.main()
