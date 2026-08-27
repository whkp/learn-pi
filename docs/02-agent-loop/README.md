# Agent Loop —— 循环如何驱动模型工作

> Agent Loop 是 Pi 的心脏，但它的核心设计其实很简单：**循环由模型的输出驱动，而不是由代码写死**。模型返回工具调用就执行、回填、再问；模型返回最终文本就结束。Pi 的一切机制（工具、事件、权限、压缩）都是绕着这个循环搭的。

## 学习目标

- 理解 Agent Loop 与"直接调用 LLM""Workflow"的本质区别。
- 分清 Trace 与 Turn 两个精确概念。
- 理解 `stopReason` 是循环唯一的终止信号。

## Pi 的核心设计

### 模型决定，harness 执行

大模型的三种用法，决策权不同：

| 用法 | 决策者 | 模型调用次数 |
|------|--------|-------------|
| 直接调用 | 用户 | 1 次 |
| Workflow | 你的代码 | N 次（代码控制） |
| Agent Loop | 模型 | 不确定（模型控制） |

Agent Loop 的关键：**步骤之间的流转由模型的输出内容驱动**。harness 只做两件事——把输入和工具结果喂给模型；如果模型输出包含工具调用就执行它，否则结束。工具循环的完整闭环是五步：声明工具 → 模型请求调用 → 执行 → 结果回填 → 再问模型。

### Trace 与 Turn

- **Trace**：从 `agent_start` 到 `agent_end` 的一次完整运行，包含多个 Turn。
- **Turn**：一次模型调用 + 该调用触发的一批工具执行。模型一口气要求 3 个工具，这 3 个工具在**同一个** Turn 里执行；回填结果再调模型，就进入下一个 Turn。

区分两者的实际意义：持久化按 Trace 组织，进度与 UI 按 Turn 刷新，工具结果配对按 Turn 内的调用 ID 对齐。

### stopReason 是唯一终止信号

循环的每一步都以 `stopReason` 判断去留：`stop`（正常结束）、`toolUse`（执行工具继续）、`error`/`aborted`（异常终止）。Pi 还有一个值得注意的取舍：**token 超限（`length`）时，残留的工具调用参数可能不完整，Pi 选择全部失败而不是执行可能损坏的调用**——安全优先。

### 事件先于状态

Pi 循环的每个状态变更都先发事件（`turn_start`、`message_start`、`tool_execution_*`、`turn_end`……），前端消费事件流而不是读取内部对象——这是 [06 章](../06-events-and-extensions/README.md) "事件是契约"的源头。

## 当前 Pi 行为

- 循环由 pi-agent-core 提供，Provider 无关；终止条件：`stopReason` 为 `stop`/`error`/`aborted`，或钩子 `shouldStopAfterTurn` 提前终止。
- 工具执行默认并行，可全局或按工具配置为顺序。

## 在 Pi 里怎么操作

Agent Loop 无需手动操作——启动 `pi` 后输入提示词即进入循环；TUI 里每轮工具调用、消息更新都是循环的可见投影。

## Python 实验

[mini_agent.py](../../learn_pi_lab/labs/mini_agent.py) 的 `run_agent_loop` 是同一循环的最小实现，核心只有十几行：

```python
for turn in range(1, max_turns + 1):
    assistant = _ask_model(provider, model, system, messages, tools)
    messages.append(assistant)
    yield MessageStartEvent(message=assistant)
    yield MessageEndEvent(message=assistant)

    if assistant.stop_reason in {"stop", "error"}:
        yield TurnEndEvent(message=assistant)
        yield AgentEndEvent(messages=tuple(messages))
        return

    for call in assistant.tool_calls:
        result = _execute_call(call, tools)
        messages.append(ToolResultMessage(
            tool_call_id=call.id, tool_name=call.name,
            content=result.content, is_error=result.is_error))
        yield ToolExecutionEndEvent(tool_name=call.name, result=result)

    yield TurnEndEvent(message=assistant)
    yield TurnStartEvent()
```

对照 Pi 的真实实现（`agent-loop.ts` 的 `runLoop`）：`_ask_model` ↔ 流式请求 assistant、`_execute_call` ↔ 执行工具批、`yield 事件` ↔ 发事件。Tau 的 `tau_agent/loop.py` 是同样的循环，只是异步版并保留 steering/follow-up 钩子。

```sh
python3 -m learn_pi_lab lab agent-loop   # 脚本化 trace：终止/未知工具/异常工具
python3 -m learn_pi_lab lab mini-agent
```

## 验证方式

```sh
python3 -m unittest tests.test_01_agent_loop tests.test_13_mini_agent -v
```

## 边界与安全

- 循环本身不设防：权限、速率限制、取消都必须包在循环外面。
- `max_turns` 是防止失控的最后防线；真实产品还应支持取消令牌。
