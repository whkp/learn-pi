"""B05 · 工具注册表——加工具 = 加一行。

上一阶段：TOOLS dict + 循环里按名字分发（read_file）。
本阶段新增：ToolRegistry 类，把"声明"和"分发"收拢。
从此加一个工具 = 注册一行，循环里不再有工具专属分支。

关键设计点：工具是一个接口（name + schema + executor），
不是散落在循环里的 switch 分支。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentTool:
    """一个工具：schema（给模型看）+ executor（给 harness 执行）。"""

    name: str
    description: str
    parameters: dict[str, object]
    execute_fn: Callable[..., str]


class ToolRegistry:
    """注册表：add 一行一个工具，get 按名字分发。"""

    def __init__(self) -> None:
        self._tools: dict[str, AgentTool] = {}

    def add(self, tool: AgentTool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"duplicate tool: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> AgentTool | None:
        return self._tools.get(name)

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))


def make_read_file_tool() -> AgentTool:
    def read_file(path: str) -> str:
        del path
        return "lesson.md: 这是文件内容。"

    return AgentTool(
        name="read_file",
        description="读取文件内容",
        parameters={"path": {"type": "string"}},
        execute_fn=read_file,
    )


def make_list_files_tool() -> AgentTool:
    def list_files(directory: str) -> str:
        return f"{directory}/: lesson.md, main.py"

    return AgentTool(
        name="list_files",
        description="列出目录内容",
        parameters={"directory": {"type": "string"}},
        execute_fn=list_files,
    )


if __name__ == "__main__":
    registry = ToolRegistry()
    registry.add(make_read_file_tool())
    registry.add(make_list_files_tool())
    print("已注册工具:", registry.names())
    tool = registry.get("read_file")
    assert tool is not None
    print(tool.execute_fn("lesson.md"))
