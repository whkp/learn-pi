"""B06 · 工具结果与错误回填——结果是数据，错误不中断循环。

上一阶段：ToolRegistry（加工具 = 加一行）。
本阶段新增：ToolResult（结构化结果）+ 错误隔离——
工具抛异常、未知工具、执行失败都变成带 is_error 的结果回填给模型，
循环继续，而不是崩溃。

关键设计点：工具是隔离边界。模型需要知道"发生了什么"，
包括失败——但失败不能以异常的形式炸穿循环。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from step_05_registry.registry import AgentTool, ToolRegistry


@dataclass(frozen=True)
class ToolResult:
    """一次工具执行的结构化结果。"""

    content: str
    is_error: bool = False
    error_type: str | None = None


def execute_tool(registry: ToolRegistry, name: str, arguments: dict[str, object]) -> ToolResult:
    """执行一个工具，把一切失败都变成结构化结果。"""
    tool = registry.get(name)
    if tool is None:
        return ToolResult(f"unknown tool: {name}", is_error=True, error_type="UnknownTool")

    try:
        output = tool.execute_fn(**arguments)
        return ToolResult(content=str(output))
    except Exception as error:
        # 只保留异常类型，不把异常消息无界传播（对应可靠性章的脱敏原则）
        return ToolResult(
            f"tool {name} failed: {type(error).__name__}",
            is_error=True,
            error_type=type(error).__name__,
        )


def make_flaky_tool() -> AgentTool:
    def flaky(value: int) -> str:
        if value <= 0:
            raise ValueError("value must be positive")
        return f"ok: {value}"

    return AgentTool(
        name="flaky",
        description="一个可能失败的示例工具",
        parameters={"value": {"type": "integer"}},
        execute_fn=flaky,
    )


if __name__ == "__main__":
    registry = ToolRegistry()
    registry.add(make_flaky_tool())

    print(execute_tool(registry, "flaky", {"value": 1}))       # 成功
    print(execute_tool(registry, "flaky", {"value": -1}))      # 执行异常 → is_error
    print(execute_tool(registry, "missing", {}))               # 未知工具 → is_error
