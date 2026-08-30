# B05 · 工具注册表

> 第二个工具来的时候，你要改三个地方；第三个来的时候，你就烦了。烦，就是重构的信号。本阶段把"工具"变成一个接口（schema + executor），把分发收进注册表——**从此加工具 = 加一行**。

## 上一阶段已有 / 本阶段新增

- 已有：TOOLS dict + 循环里查表分发。
- 新增：`AgentTool`（name/description/parameters/execute_fn）、`ToolRegistry`（add/get/names）。

## 核心设计

```python
@dataclass(frozen=True)
class AgentTool:
    name: str
    description: str
    parameters: dict[str, object]   # schema，给模型看
    execute_fn: Callable[..., str]  # executor，给 harness 执行

class ToolRegistry:
    def add(self, tool: AgentTool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"duplicate tool: {tool.name}")
        self._tools[tool.name] = tool
    def get(self, name: str) -> AgentTool | None:
        return self._tools.get(name)
```

三个决策及原因：

1. **工具是接口不是分支**：B04 里加工具要改 TOOLS 表 + 循环分支；现在 `AgentTool` 一个 dataclass 承载全部信息，循环只调 `registry.get(name).execute_fn(...)`。
2. **拒绝重复注册**：同名工具重复 add 直接报错——注册表是"声明"的边界，重复意味着配置错误，应尽早暴露。
3. **schema 与 executor 分离**：`parameters` 是给模型看的（模型据此生成合法参数），`execute_fn` 是给 harness 执行的——这就是 [03 章](../../../docs/03-tools/README.md)"工具 = schema + executor"的最小形态。

## 运行

```sh
cd examples/harness/step_05_registry
python3 registry.py
```

预期输出：

```
已注册工具: ('list_files', 'read_file')
lesson.md: 这是文件内容。
```

## 失败实验：重复注册

`registry.add(make_read_file_tool())` 连续调用两次，第二次抛 `ValueError: duplicate tool: read_file`——注册表把"配置错误"变成显式异常，而不是让它在运行时静默覆盖。

## 下一步

[B06 工具结果与错误回填](../step_06_tool_results/README.md)：工具会失败——执行异常、未知工具、空结果。这些要变成结构化错误回填给模型，而不是让循环崩溃。
