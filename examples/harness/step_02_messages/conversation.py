"""B02 · messages 多轮历史——模型无状态，历史由 harness 维护。

上一阶段：一次调用 = 一次对话（chat_once）。
本阶段新增：messages 数组（role + content），把历史喂回模型，
让"对话"真正连续。

关键设计点：模型每次调用只看传入的 messages——它不记得上次。
记住"我们聊到哪了"是 harness 的职责。
"""

from __future__ import annotations

from dataclasses import dataclass

Message = dict[str, str]  # {"role": "user"|"assistant", "content": "..."}


def mock_chat(messages: list[Message]) -> str:
    """极简 mock：根据最后一条 user 消息生成回复。"""
    last_user = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
    )
    return f"（已收到 {len(messages)} 条消息）关于「{last_user}」的回答。"


def conversation() -> list[Message]:
    """维护一轮完整对话：harness 负责追加消息，模型只看数组。"""
    messages: list[Message] = []
    for user_turn in ("你好", "什么是 harness？", "谢谢"):
        messages.append({"role": "user", "content": user_turn})
        reply = mock_chat(messages)
        messages.append({"role": "assistant", "content": reply})
    return messages


if __name__ == "__main__":
    history = conversation()
    for message in history:
        print(f"{message['role']}: {message['content']}")
