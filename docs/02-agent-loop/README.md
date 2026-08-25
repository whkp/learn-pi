# Agent Loop —— 循环如何驱动模型工作

> 所有 Coding Agent 都围绕同一个循环构建：把消息喂给模型，执行模型要求的工具，把结果回填，再问模型，直到模型决定停下。这一章拆解这个循环"如何实现"：三种用法、Trace/Turn、双层循环结构、工具批执行，以及 Pi 0.84.2 的真实代码。

## 学习目标

- 理解 Agent Loop 与"直接调用 LLM""Workflow"的本质区别。
- 分清 Trace 与 Turn 两个精确概念。
- 理解双层循环：内层处理工具调用，外层处理 follow-up 消息。
- 读 Pi 0.84.2 的 `agent-loop.ts` 真实实现，并对照本课程的 Python 教学模型。

## 机制：一个定义与两种约束

先给一个贯穿全书的统一定义：**agent = LLM + tool use**。模型负责语言、推理，以及决定下一步调用哪个工具；除此之外的一切——消息怎么维护、工具怎么注册与执行、结果怎么回填、什么时候停——都是 harness（包住模型的那层程序）的职责。

工具循环的完整闭环是五步：

```
1. 声明工具（schema）→ 2. 模型请求调用 → 3. 你执行 → 4. 结果回填 → 5. 再问模型
```

第五步之后回到第 2 步，直到模型不再请求工具。

### 大模型的三种用法

| 维度 | 直接调用 | Workflow | Agent Loop |
|------|---------|----------|------------|
| 决策者 | 用户 | 你的代码 | 模型 |
| 模型调用次数 | 1 次 | N 次（代码控制） | 不确定（模型控制） |
| 核心工作 | 写提示词 | 设计流程 | 定义工具和循环 |

Agent Loop 的关键：**步骤之间的流转由模型的输出内容驱动**，而不是写死。你的代码只做两件事——把输入和工具结果喂给模型；如果模型输出包含工具调用就执行它，否则结束。

### Trace 与 Turn

- **Trace**：从 `agent_start` 到 `agent_end` 的一次完整运行，包含多个 Turn。
- **Turn**：一次模型调用 + 该调用触发的一批工具执行，由一对 `turn_start` / `turn_end` 包裹。模型一口气要求 3 个工具，这 3 个工具在同一个 Turn 里执行；把结果回填后再调模型，就进入下一个 Turn。

区分两者的实际意义：持久化按 Trace 组织（一个会话文件 = 一个 Trace 的历史），进度与 UI 按 Turn 刷新，工具结果配对按 Turn 内的调用 ID 对齐。

### 双层循环

实现上，循环是双层的，两层的职责不同：

```
外层（while true）      内层（while hasMoreToolCalls || pending）
  ├─ 处理 follow-up        ├─ 发 turn_start
  ├─ 检查是否该停          ├─ 流式请求 assistant 消息
  └─ 结束发 agent_end      ├─ 检查 stopReason
                          ├─ 执行本 Turn 的一批工具
                          └─ 发 turn_end
```

- **内层**处理"模型还要工具 + 用户中途插入的 steering 消息"；`hasMoreToolCalls` 由本轮是否产生工具调用决定。
- **外层**处理"Agent 本来要停，但钩子（follow-up）又塞进了新消息"的情况——比如用户等待时又输入了一句话。

## Pi 源码怎么实现（0.84.2）

循环主体在 `packages/agent/src/agent-loop.ts` 的 `runLoop`（155 行起）：

```typescript
// packages/agent/src/agent-loop.ts（Pi 0.84.2，节选）
while (true) {
  let hasMoreToolCalls = true;
  while (hasMoreToolCalls || pendingMessages.length > 0) {
    if (!firstTurn) {
      await emit({ type: "turn_start" });
    } else {
      firstTurn = false;
    }
    // 处理 steering 消息（用户等待时插入）
    const message = await streamAssistantResponse(currentContext, config, signal, emit, streamFunction);
    newMessages.push(message);

    if (message.stopReason === "error" || message.stopReason === "aborted") {
      await emit({ type: "turn_end", message, toolResults: [] });
      await emit({ type: "agent_end", messages: newMessages });
      return;
    }

    const toolCalls = message.content.filter((c) => c.type === "toolCall");
    const toolResults: ToolResultMessage[] = [];
    hasMoreToolCalls = false;
    if (toolCalls.length > 0) {
      // length 截断时工具参数可能不完整，全部失败而非执行
      const executedToolBatch =
        message.stopReason === "length"
          ? await failToolCallsFromTruncatedMessage(toolCalls, emit)
          : await executeToolCalls(currentContext, message, config, signal, emit);
      toolResults.push(...executedToolBatch.messages);
      hasMoreToolCalls = !executedToolBatch.terminate;
      // ...把 toolResults push 回 currentContext.messages 和 newMessages
    }

    await emit({ type: "turn_end", message, toolResults });

    // 钩子：prepareNextTurn 可改模型/思考级别；shouldStopAfterTurn 可提前终止
    const nextTurnSnapshot = await config.prepareNextTurn?.(nextTurnContext);
    if (await config.shouldStopAfterTurn?.(nextTurnContext)) {
      await emit({ type: "agent_end", messages: newMessages });
      return;
    }
    pendingMessages = (await config.getSteeringMessages?.()) || [];
  }

  // 内层退出，Agent 本来要停：检查 follow-up
  const followUpMessages = (await config.getFollowUpMessages?.()) || [];
  if (followUpMessages.length > 0) {
    pendingMessages = followUpMessages;
    continue;
  }
  break;
}
await emit({ type: "agent_end", messages: newMessages });
```

逐个要点：

1. **双层循环**：内层结束（`hasMoreToolCalls` 为 false 且无 steering）后，外层检查 follow-up；有则注入继续，没有则 break 发 `agent_end`。
2. **`stopReason` 是唯一终止信号**：`error`/`aborted` 立即结束；正常结束时模型不再产生 `toolCall`。
3. **`length` 特判**：token 超限截断时，消息里残留的工具调用参数可能不完整，Pi 选择全部失败（`failToolCallsFromTruncatedMessage`）而不是执行可能损坏的调用。
4. **事件先于状态**：每次状态变更都先 `emit` 事件，前端消费事件流，而不是读取内部对象。
5. **三个钩子**：`prepareNextTurn`（换模型/思考级别）、`shouldStopAfterTurn`（提前终止）、`getSteeringMessages`/`getFollowUpMessages`（注入消息）——它们让产品层可以在不修改循环的情况下定制行为。

### 工具批的执行：顺序与并行

`executeToolCalls`（411 行）根据配置选择顺序或并行执行：

```typescript
// packages/agent/src/agent-loop.ts（Pi 0.84.2，节选）
async function executeToolCalls(...) {
  const toolCalls = assistantMessage.content.filter((c) => c.type === "toolCall");
  const hasSequentialToolCall = toolCalls.some(
    (tc) => currentContext.tools?.find((t) => t.name === tc.name)?.executionMode === "sequential",
  );
  if (config.toolExecution === "sequential" || hasSequentialToolCall) {
    return executeToolCallsSequential(...);
  }
  return executeToolCallsParallel(...);
}
```

顺序路径（`executeToolCallsSequential`）对每个调用依次：发 `tool_execution_start` → 准备参数（`prepareToolCall`）→ 执行（`executePreparedToolCall`）→ 收尾（`finalizeExecutedToolCall`）→ 发 `tool_execution_end` → 生成 `ToolResultMessage` → 发消息事件。`signal.aborted` 时中断后续调用。一个 Turn 内全部工具执行完毕后，`shouldTerminateToolBatch` 决定是否提前终止整个 Trace（所有工具都请求终止时才生效）。

注意 `AgentTool` 的 `executionMode` 字段：单个工具可以声明自己是 `"sequential"`（如编辑文件），强制与其他调用串行，即使全局配置是并行。

## 当前 Pi 行为

- Agent 循环由 `pi-agent-core`（`packages/agent`）提供，Provider 无关；`coding-agent` 在其上组装产品能力。
- 终止条件：`stopReason` 为 `stop`、`error`、`aborted`，或钩子 `shouldStopAfterTurn` 返回 true。
- steering（用户等待时插入的消息）与 follow-up（Agent 本可停止后由钩子追加的消息）是两条独立注入通道。
- 工具执行默认并行，可全局或按工具配置为顺序。

## 在 Pi 里怎么操作

Agent Loop 本身无需手动操作——启动 `pi` 后输入提示词即进入循环。你可以观察事件流：TUI 里每轮工具调用、消息更新都是循环的可见投影。

## Python 对照

本课程的 [mini_agent.py](../../learn_pi_lab/labs/mini_agent.py) 是同一循环的最小实现（同步版），`run_agent_loop` 与上面 TS 代码一一对应：

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
        yield ToolExecutionStartEvent(tool_name=call.name, arguments=call.arguments)
        result, updates = _execute_call(call, tools)
        for partial in updates:
            yield ToolExecutionUpdateEvent(tool_name=call.name, partial_result=AgentToolResult(partial))
        yield ToolExecutionEndEvent(tool_name=call.name, result=result)

        result_message = ToolResultMessage(...)
        messages.append(result_message)
        yield MessageStartEvent(message=result_message)
        yield MessageEndEvent(message=result_message)

    yield TurnEndEvent(message=assistant)
    yield TurnStartEvent()
```

对应关系：`_ask_model` ≈ `streamAssistantResponse`；`_execute_call` ≈ `executeToolCallsSequential` 的单工具版本；`yield` 事件 ≈ `await emit(...)`。教学模型刻意简化了三件事：无 steering/follow-up 钩子、工具只串行、无取消信号。

Tau 的真实实现是 asyncio 版：`tau_agent/loop.py` 的 `run_agent_loop` 结构完全同型，且保留了 steering/follow-up 与 before/after_tool_call 钩子——完整的双版本对照见下一节「实现对照：Pi 源码与 Tau 双版本」。

## 实现对照：Pi 源码与 Tau 双版本

同一个循环，Pi 用 TypeScript 实现、Tau 用 Python 实现（asyncio）。逻辑完全对应，选择读哪一个版本都可以；对照读更清楚。

**循环主体**——内层循环的每一圈（一个 Turn）：

```typescript
// Pi 0.84.2: packages/agent/src/agent-loop.ts（原文节选）
while (hasMoreToolCalls || pendingMessages.length > 0) {
  if (!firstTurn) {
    await emit({ type: "turn_start" });
  } else {
    firstTurn = false;
  }
  const message = await streamAssistantResponse(currentContext, config, signal, emit, streamFunction);
  newMessages.push(message);

  if (message.stopReason === "error" || message.stopReason === "aborted") {
    await emit({ type: "turn_end", message, toolResults: [] });
    await emit({ type: "agent_end", messages: newMessages });
    return;
  }

  const toolCalls = message.content.filter((c) => c.type === "toolCall");
  // ...executeToolCalls → 结果回填
  await emit({ type: "turn_end", message, toolResults });
}
```

```python
# Tau: tau_agent/loop.py（原文节选，Python 改写）
# 概念对照：TS 的 await emit(...) → Python 的 yield ...；
# TS 的 message.content.filter(...) → Python 的 assistant.tool_calls
while has_more_tools or pending:
    if not first_turn:
        yield TurnStartEvent()
    first_turn = False

    async for event in _assistant_events(
        provider=provider, model=model, system=system,
        messages=_provider_context(messages), tools=tools,
        signal=signal, session_id=session_id,
    ):
        yield event
        if isinstance(event, MessageEndEvent) and isinstance(event.message, AssistantMessage):
            assistant = event.message

    if assistant.stop_reason in {"error", "aborted"}:
        yield TurnEndEvent(message=assistant)
        yield AgentEndEvent(messages=new_messages)
        return

    tool_results = []
    for call in assistant.tool_calls:
        async for event in _execute_tool_call(call, tool_by_name, signal,
                                              before_tool_call, after_tool_call):
            yield event
            if isinstance(event, MessageEndEvent) and isinstance(event.message, ToolResultMessage):
                tool_results.append(event.message)
                messages.append(event.message)
    yield TurnEndEvent(message=assistant, tool_results=tool_results)
```

对应关系一目了然：`streamAssistantResponse` ↔ `_assistant_events`，`executeToolCalls` ↔ `_execute_tool_call`，`await emit(...)` ↔ `yield`。

**单个工具的执行**——先发开始事件、执行、再发结束事件：

```typescript
// Pi 0.84.2: packages/agent/src/agent-loop.ts（原文节选）
await emit({ type: "tool_execution_start", toolCallId: call.id, toolName: call.name, args: call.arguments });
// ...prepareToolCall / executePreparedToolCall / finalizeExecutedToolCall
await emit({ type: "tool_execution_end", toolCallId: call.id, toolName: call.name, result, isError });
```

```python
# Tau: tau_agent/loop.py 的 _execute_tool_call（原文节选）
yield ToolExecutionStartEvent(tool_call_id=call.id, tool_name=call.name, args=call.arguments)

if before_tool_call is not None:
    blocked, block_reason = await before_tool_call(call)
if blocked:
    result = _error_result(block_reason or "Tool execution was blocked")
    is_error = True
elif signal is not None and signal.is_cancelled():
    result = _error_result("Operation aborted")
    is_error = True
else:
    tool = tools.get(call.name)
    if tool is None:
        result = _error_result(f"Tool {call.name} not found")
        is_error = True
    else:
        result, is_error, updates = await _run_tool(tool, call, signal)

if after_tool_call is not None:
    result, is_error = await after_tool_call(call, result, is_error)

yield ToolExecutionEndEvent(tool_call_id=call.id, tool_name=call.name, result=result, is_error=is_error)
```

Tau 版多展示了 Pi 版省略的细节：`before_tool_call`（执行前拦截）、`after_tool_call`（执行后改写）、取消信号检查——它们对应 Pi 的 [06 章](../06-events-and-extensions/README.md) 扩展事件与权限钩子。

## Python 实验

```sh
python3 -m learn_pi_lab lab agent-loop   # 脚本化 trace：终止/未知工具/异常工具
python3 -m learn_pi_lab lab mini-agent   # Tau 对照最小循环，含事件流与 JSONL 往返
```

## 验证方式

```sh
python3 -m unittest tests.test_01_agent_loop tests.test_13_mini_agent -v
```

## 边界与安全

- 循环本身不设防：谁提供消息、谁执行工具、谁决定终止，由 Harness 控制。权限、速率限制、取消都必须包在循环外面。
- `max_turns` 是防止失控的最后防线；真实产品还应支持取消令牌（AbortSignal）。
- `length` 截断时宁可失败工具调用，也不要执行参数可能被截断的调用——这是安全优先的取舍。
