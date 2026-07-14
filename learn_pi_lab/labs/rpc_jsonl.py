"""Strict newline-delimited JSON request parsing for the RPC lesson.

The production Pi RPC protocol has its own documented schema. This is a
deliberately smaller parser that illustrates framing, validation, and recovery
without launching a subprocess or interpreting user supplied commands.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any


class RpcProtocolError(ValueError):
    """Raised for invalid JSONL framing or request records."""


@dataclass(frozen=True)
class RpcRequest:
    """A validated request record."""

    id: str
    method: str
    params: dict[str, Any]


class JsonlRpcCodec:
    """Incrementally decode newline-delimited JSON request records."""

    def __init__(self, *, max_buffer_bytes: int = 65_536) -> None:
        if isinstance(max_buffer_bytes, bool) or not isinstance(max_buffer_bytes, int) or max_buffer_bytes < 1:
            raise ValueError("max buffer bytes must be a positive integer")
        self._max_buffer_bytes = max_buffer_bytes
        self._buffer = ""

    @staticmethod
    def encode_request(request_id: str, method: str, params: dict[str, Any]) -> str:
        request = _validate_record({"id": request_id, "method": method, "params": params})
        return json.dumps(
            {"id": request.id, "method": request.method, "params": request.params},
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ) + "\n"

    def feed(self, chunk: str) -> tuple[RpcRequest, ...]:
        if not isinstance(chunk, str):
            raise TypeError("chunk must be text")
        candidate = self._buffer + chunk
        if len(candidate.encode("utf-8")) > self._max_buffer_bytes and "\n" not in candidate:
            self._buffer = ""
            raise RpcProtocolError("unterminated record exceeds buffer limit")

        records = candidate.split("\n")
        self._buffer = records.pop()
        messages: list[RpcRequest] = []
        for record in records:
            if not record.strip():
                continue
            try:
                decoded = json.loads(record)
            except json.JSONDecodeError as error:
                raise RpcProtocolError("invalid JSON record") from error
            messages.append(_validate_record(decoded))

        if len(self._buffer.encode("utf-8")) > self._max_buffer_bytes:
            self._buffer = ""
            raise RpcProtocolError("unterminated record exceeds buffer limit")
        return tuple(messages)


def _validate_record(record: object) -> RpcRequest:
    if not isinstance(record, dict):
        raise RpcProtocolError("request must be a JSON object")
    request_id = record.get("id")
    method = record.get("method")
    params = record.get("params")
    if not isinstance(request_id, str) or not request_id:
        raise RpcProtocolError("request id must be a non-empty string")
    if not isinstance(method, str) or not method.strip():
        raise RpcProtocolError("request method must be a non-empty string")
    if not isinstance(params, dict):
        raise RpcProtocolError("request params must be an object")
    return RpcRequest(request_id, method, _json_safe_object(params))


def _json_safe_object(value: dict[str, Any]) -> dict[str, Any]:
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
        decoded = json.loads(encoded)
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise RpcProtocolError("request params must be JSON-safe") from error
    if not isinstance(decoded, dict):
        raise AssertionError("JSON object validation changed its type")
    return decoded
