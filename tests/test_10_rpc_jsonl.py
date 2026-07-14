"""Tests for a strict, stream-safe JSONL RPC teaching protocol."""

from __future__ import annotations

import unittest

from learn_pi_lab.labs.rpc_jsonl import JsonlRpcCodec, RpcProtocolError


class RpcJsonlTests(unittest.TestCase):
    def test_feed_handles_fragmented_records_and_preserves_order(self) -> None:
        codec = JsonlRpcCodec()

        self.assertEqual((), codec.feed('{"id":"1","method":"ping"'))
        messages = codec.feed(',"params":{}}\n{"id":"2","method":"status","params":{}}\n')

        self.assertEqual(("1", "2"), tuple(message.id for message in messages))
        self.assertEqual(("ping", "status"), tuple(message.method for message in messages))

    def test_encode_round_trips_json_safe_params_with_exactly_one_newline(self) -> None:
        encoded = JsonlRpcCodec.encode_request("a", "inspect", {"path": "src/app.py"})
        messages = JsonlRpcCodec().feed(encoded)

        self.assertTrue(encoded.endswith("\n"))
        self.assertFalse(encoded.endswith("\n\n"))
        self.assertEqual({"path": "src/app.py"}, messages[0].params)

    def test_invalid_json_or_schema_does_not_leak_into_later_records(self) -> None:
        codec = JsonlRpcCodec()

        with self.assertRaisesRegex(RpcProtocolError, "invalid JSON"):
            codec.feed("not json\n")

        messages = codec.feed('{"id":"ok","method":"ping","params":{}}\n')
        self.assertEqual(("ok",), tuple(message.id for message in messages))

        with self.assertRaisesRegex(RpcProtocolError, "method"):
            JsonlRpcCodec().feed('{"id":"bad","method":"","params":{}}\n')

    def test_buffer_limit_rejects_unterminated_input(self) -> None:
        codec = JsonlRpcCodec(max_buffer_bytes=8)

        with self.assertRaisesRegex(RpcProtocolError, "buffer"):
            codec.feed("123456789")


if __name__ == "__main__":
    unittest.main()
