"""B03 · 流式输出——回复增量吐出，UI 才能边等边显示。

上一阶段：messages 多轮历史（conversation）。
本阶段新增：模型回复从"一次性返回"变成"生成器逐个 yield"。

关键设计点：流式让"等待模型"变成"边收边显示"；
教学上它也是后面事件流（B10）的雏形——消费者按片段消费。
"""

from __future__ import annotations

from collections.abc import Iterator


def stream_reply(text: str, chunk_size: int = 2) -> Iterator[str]:
    """模拟模型逐块吐出回复。真实场景是网络流，这里是切分字符串。"""
    for index in range(0, len(text), chunk_size):
        yield text[index : index + chunk_size]


def collect(stream: Iterator[str]) -> str:
    """消费者：把流式片段拼回完整文本。"""
    return "".join(stream)


if __name__ == "__main__":
    for piece in stream_reply("流式输出让等待变成可见的进度。"):
        print(piece, end="|")
    print()
