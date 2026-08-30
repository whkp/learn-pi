"""B01 · 裸 API 调用——一次调用 = 一次对话。

主线第一步：连"循环"都还没有，只有一次模型调用。
关键设计点：模型调用被包在一个函数后面（mock_chat），
这样后面换成真实 Provider 时，调用方代码不用改。
"""

from __future__ import annotations

# 一个极简的 mock 模型：输入 prompt，输出固定回复。
# 真实场景里这里是对 OpenAI/Anthropic 的一次 HTTP 请求。
def mock_chat(system: str, user: str) -> str:
    del system  # 教学模型忽略 system，B02 会用到
    return f"你说的是：「{user}」。这是 mock 模型的回复。"


def chat_once(prompt: str) -> str:
    """调用一次模型，返回回复文本。"""
    return mock_chat(system="", user=prompt)


if __name__ == "__main__":
    reply = chat_once("什么是 agent？")
    print(reply)
