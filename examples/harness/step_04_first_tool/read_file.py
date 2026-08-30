"""B04 · 第一个工具——agent loop 第一次完整闭环。

上一阶段：流式输出（streaming）。
本阶段新增：模型可以返回"工具调用请求"，harness 执行工具并把结果回填——
这就是 agent loop 的五步闭环：声明工具 → 模型请求 → 执行 → 回填 → 再问。

关键设计点：循环由模型输出驱动——模型说 toolUse 就执行工具，
说 stop 就结束。harness 只做两件事：喂消息、执行工具。
"""

from __future__ import annotations

from dataclasses import dataclass

# --- 消息 ---
@dataclass
class Message:
    role: str  # "user" | "assistant" | "toolResult"
    content: str


# --- 工具 ---
def read_file(path: str) -> str:
    """真正的工具：读文件。教学环境用固定内容模拟。"""
    del path
    return "lesson.md: 这是文件内容。"


TOOLS: dict[str, object] = {
    "read_file": {"description": "读取文件内容", "execute": read_file},
}


# --- 脚本化模型：先要工具，再给最终答案 ---
def scripted_model(messages: list[Message]) -> tuple[str, str | None]:
    """返回 (stop_reason, tool_name)。模拟模型的一轮输出。

    用函数属性保存轮次状态——但状态必须在每次 agent_loop 运行时重置，
    否则多次调用会共享计数器（测试里的经典坑）。
    """
    del messages
    if not hasattr(scripted_model, "_asked"):
        scripted_model._asked = 0
    scripted_model._asked += 1
    if scripted_model._asked == 1:
        return "toolUse", "read_file"  # 第一轮：请求工具
    return "stop", None               # 第二轮：结束


def agent_loop(prompt: str) -> list[Message]:
    """五步闭环：声明工具 → 模型请求 → 执行 → 回填 → 再问。"""
    scripted_model._asked = 0  # 每次运行独立状态
    messages: list[Message] = [Message("user", prompt)]

    while True:
        stop_reason, tool_name = scripted_model(messages)
        if stop_reason == "stop":
            messages.append(Message("assistant", "我已经读完文件了。"))
            return messages

        # 模型请求了工具：记录请求 → 查表执行 → 结果回填
        assert tool_name is not None
        messages.append(Message("assistant", f"[请求调用 {tool_name}]"))
        tool = TOOLS[tool_name]
        result = tool["execute"]("lesson.md")  # type: ignore[operator]
        messages.append(Message("toolResult", result))


if __name__ == "__main__":
    for message in agent_loop("读一下 lesson.md"):
        print(f"{message.role}: {message.content}")
