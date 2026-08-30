# B06 · 工具结果与错误回填

> 工具会失败：参数非法、文件不存在、网络超时。本阶段把工具执行包进"结果"——**成功和失败都返回结构化 `ToolResult`，失败不炸穿循环**。这是工具系统作为"隔离边界"（[03 章](../../../docs/03-tools/README.md)）的第一个落地。

## 上一阶段已有 / 本阶段新增

- 已有：`ToolRegistry`、`AgentTool`。
- 新增：`ToolResult`（content + is_error + error_type）、`execute_tool`（错误隔离封装）。

## 核心设计

```python
@dataclass(frozen=True)
class ToolResult:
    content: str
    is_error: bool = False
    error_type: str | None = None

def execute_tool(registry, name, arguments) -> ToolResult:
    tool = registry.get(name)
    if tool is None:
        return ToolResult(f"unknown tool: {name}", is_error=True, error_type="UnknownTool")
    try:
        return ToolResult(content=str(tool.execute_fn(**arguments)))
    except Exception as error:
        return ToolResult(f"tool {name} failed: {type(error).__name__}",
                          is_error=True, error_type=type(error).__name__)
```

三个决策及原因：

1. **失败也是结果**：模型需要知道"工具失败了、为什么"——`ToolResult` 带着 `error_type` 回填给模型，模型可以调整策略重试。异常是给程序的信号，结果才是给模型的信号。
2. **只保留异常类型**：`error_type = "ValueError"` 而不带 `str(error)`——对应 [09 可靠性](../../../docs/09-reliability/README.md) 的脱敏原则，敏感异常消息不传播。
3. **`frozen=True`**：结果是不可变数据，避免被意外修改——工具结果是 transcript 的一部分，必须是稳定的。

## 运行

```sh
cd examples/harness/step_06_tool_results
python3 tool_results.py
```

预期输出：

```
ToolResult(content='ok: 1', is_error=False, error_type=None)
ToolResult(content='tool flaky failed: ValueError', is_error=True, error_type='ValueError')
ToolResult(content='unknown tool: missing', is_error=True, error_type='UnknownTool')
```

## 失败实验：错误不被隔离

把 `execute_tool` 的 try/except 删掉，`flaky` 抛的 `ValueError` 直接冒泡——循环崩溃，之前积累的对话状态丢失。这演示了为什么错误隔离是 harness 的硬需求：**一次工具失败不能毁掉整个会话**。

## 下一步

B07 权限与工作目录（下一步，待续）：工具能跑任意命令、读任意文件——要有"不问模型意见"的硬闸门。
