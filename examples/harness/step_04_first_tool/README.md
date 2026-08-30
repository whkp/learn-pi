# B04 · 第一个工具——agent loop 第一次完整闭环

> 模型第一次"伸手"：它返回的不是最终文本，而是"我要调用 read_file"。harness 执行工具、把结果回填、再问模型——**五步闭环第一次完整跑通**。这是全书的心脏，也是 [02 Agent Loop](../../../docs/02-agent-loop/README.md) 的最小实现。

## 上一阶段已有 / 本阶段新增

- 已有：messages 多轮历史、流式输出。
- 新增：工具声明（`TOOLS` 表）、`scripted_model` 返回 stop_reason + 工具名、五步闭环 `agent_loop`。

## 核心设计

```python
def agent_loop(prompt: str) -> list[Message]:
    messages = [Message("user", prompt)]
    while True:
        stop_reason, tool_name = scripted_model(messages)
        if stop_reason == "stop":
            messages.append(Message("assistant", "我已经读完文件了。"))
            return messages
        tool = TOOLS[tool_name]                    # 查表分发
        result = tool["execute"]("lesson.md")      # 执行
        messages.append(Message("toolResult", result))  # 回填
        messages.append(Message("assistant", f"[请求调用 {tool_name}]"))
```

三个决策及原因：

1. **模型输出驱动循环**：`stop_reason` 决定去留（`toolUse` 继续、`stop` 结束）——对应 [02 章](../../../docs/02-agent-loop/README.md) 的"决策权在模型"。
2. **TOOLS 是 dict 查表**：此时加工具 = 在表里加一行 + 在 `scripted_model` 里加一个分支。B05 会解决"分支越来越多"的问题。
3. **toolResult 是普通消息**：结果回填进 messages，下一轮模型能看到——对应 [04 章](../../../docs/04-messages-and-memory/README.md) 的工具成对回填。

## 运行

```sh
cd examples/harness/step_04_first_tool
python3 read_file.py
```

预期输出：

```
user: 读一下 lesson.md
assistant: [请求调用 read_file]
toolResult: lesson.md: 这是文件内容。
assistant: 我已经读完文件了。
```

## 失败实验：模型请求了不存在的工具

把 `scripted_model` 第一轮返回 `"read_file2"`，`TOOLS[tool_name]` 抛 `KeyError`，循环崩溃。这提示 B05/B06 的需求：**未知工具要变成结构化错误回填给模型，而不是崩溃**。

## 下一步

[B05 工具注册表](../step_05_registry/README.md)：工具多了，switch/查表开始烦人——注册表出场。
