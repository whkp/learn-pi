"""A no-subprocess JSON RPC console using the course JSONL parser."""

from __future__ import annotations

import json

from learn_pi_lab.labs.rpc_jsonl import JsonlRpcCodec, RpcProtocolError


def handle_request(request_line: str) -> str:
    """Handle the small allowlisted demo protocol and return one JSON object."""
    try:
        messages = JsonlRpcCodec().feed(request_line.rstrip("\n") + "\n")
        if len(messages) != 1:
            raise RpcProtocolError("exactly one request record is required")
        request = messages[0]
        if request.method == "ping":
            payload: dict[str, object] = {"id": request.id, "result": {"ok": True, "value": "pong"}}
        else:
            payload = {
                "id": request.id,
                "error": {"code": "method_not_found", "message": "unsupported method"},
            }
    except (RpcProtocolError, TypeError) as error:
        payload = {"id": None, "error": {"code": "invalid_request", "message": str(error)}}
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
