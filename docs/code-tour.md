# 核心代码导览 —— 精选片段与逐段解读

> 各章的「Python 实验」只告诉你要运行什么；这一页把九个核心机制的**关键片段**摘出来，逐段讲清设计意图，并标注对应的 Pi 源码符号。读完它，你就有了打开任何 Agent 框架源码时的"路标"。
>
> 全部片段取自 `learn_pi_lab/labs/`（共约 2,300 行，只依赖标准库、完全离线）。它们是教学模型，不是 Pi 的生产实现；Pi 侧符号以基线 0.85.1 为准。

## 01 · Agent Loop：循环骨架

[agent_loop.py](../learn_pi_lab/labs/agent_loop.py) 的 `run_scripted_loop` 把循环压缩成"问 → 判 → 执行 → 回填"四步：

```python
for turn in range(1, max_turns + 1):
    step = model.next_step(prompt)
    if step is None:
        errors.append(RunError(code="script_exhausted", ...))
        return _trace(prompt, None, tool_names, turn - 1, errors)

    if isinstance(step, str) or isinstance(step, FinalText):
        return _trace(prompt, step文本, tool_names, turn, errors)   # 终止

    # ToolRequest：执行并把结果回填，进入下一轮
```

三个设计点：

1. **`max_turns` 先于一切校验**——防失控是循环的第一道参数检查（`invalid_max_turns` 直接返回 trace，而不是抛异常）。循环的产物是 `RunTrace`（数据），不是副作用（打印/网络），这让后续断言成为可能。
2. **"脚本耗尽"也是错误**：模型停在没有 final text 的地方，循环不能装作正常结束——`script_exhausted` 让这个状态显式可见。
3. **字符串和 `FinalText` 都算终止**：`isinstance` 分支模拟了 `stopReason` 判别，工具请求之外的任何一步都走向终止。

对应 Pi：`packages/agent/src/agent-loop.ts` 的 `runLoop`（`stopReason` 判别在 215/231 行，`hasMoreToolCalls` 在 235 行）。机制详解见 [02 章](02-agent-loop/README.md)。

## 02 · 工具权限：先闸门，后执行

[tool_permissions.py](../learn_pi_lab/labs/tool_permissions.py) 是"软约束 vs 硬闸门"的完整实现，只有 134 行：

```python
def dispatch_if_allowed(request, policy, executor):
    decision = evaluate_request(request, policy)
    if not decision.allowed:
        return DispatchResult(decision=decision, result=None, executed=False)
    return DispatchResult(decision=decision, result=executor(decision.request), executed=True)
```

`evaluate_request` 内部是三道依次的检查：

```python
token, problem = _command_token(request.command)        # ① 裸命令令牌
if token not in policy.allowed_commands:                # ② 白名单
    return Decision(False, "command_not_allowed", ...)
for requested_path in request.paths:                    # ③ 路径归一化 + 包含检查
    normalized_path, path_problem = _normalized_path(requested_path, policy.root)
    if path_problem is not None:
        return Decision(False, path_problem, request)
```

关键取舍藏在细节里：

- **`_command_token` 拒绝一切 shell 语法**：`isspace()` 或字符属于 `;|&><$\`` 即拒绝。命令必须是单个裸 token——不做字符串解析，就没有注入面。
- **路径检查先拒绝 `..` 分量，再 `resolve()` 后验证 `relative_to(root)`**：前者拦住明显的穿越，后者兜底符号链接与绝对路径。两步缺一不可。
- **`executed=False` 是结构化事实**：被拒绝的请求零副作用，executor 从未被调用。调用方不必"事后撤销"任何东西。

对应 Pi：`packages/coding-agent/src/core/tools/index.ts`（工具与 cwd 绑定）。机制详解见 [03 章](03-tools/README.md)。

## 03 · 会话树：认父不认子

[session_tree.py](../learn_pi_lab/labs/session_tree.py) 用 90 行实现"append-only + 父指针"的会话树。`validate` 做三件事：

```python
for entry in self._entries:
    if entry.id in entries_by_id:                  # ① ID 幂等
        raise MalformedTranscript(f"duplicate id: {entry.id!r}")
for entry in self._entries:
    if entry.parent_id == entry.id:                # ② 禁止自父
        raise MalformedTranscript(...)
    if entry.parent_id is not None and entry.parent_id not in entries_by_id:
        raise MalformedTranscript(f"dangling parent ...")   # ③ 禁止悬空父
```

而"认父不认子"的重建逻辑只有一层循环：

```python
def path_to(self, leaf_id):
    current = self._entries_by_id[leaf_id]
    branch = []
    while True:
        branch.append(current)
        if current.parent_id is None:
            break
        current = self._entries_by_id[current.parent_id]
    return tuple(reversed(branch))
```

设计点：**分支不是数据结构，是查询结果**——从任意叶子沿父指针走到底，就是一条分支。没有"分支列表"这种需要维护的状态，自然也就没有分支不一致的 bug。第三步的环检测（沿父指针走并记录 visited）在构造时就排除掉损坏的快照，而不是等查询时才炸。

对应 Pi：`packages/coding-agent/docs/sessions.md`、`session-format.md`。机制详解见 [05 章](05-sessions/README.md)。

## 04 · 压缩：切割点永不拆对

[compaction.py](../learn_pi_lab/labs/compaction.py) 的 `choose_cut` 回答了一个具体问题：保留最新 N 条时，如果第 N 条正好切在一对 `toolCall/toolResult` 中间怎么办？

```python
start = max(0, len(units) - keep_units)
while True:
    expanded_start = start
    for indices in pair_indices.values():
        includes_pair_unit = any(index >= start for index in indices)
        excludes_pair_unit = any(index < start for index in indices)
        if includes_pair_unit and excludes_pair_unit:      # 这一对被切开了
            expanded_start = min(expanded_start, min(indices))
    if expanded_start == start:
        break
    start = expanded_start
```

**边界向更旧的方向扩张，直到不再切开任何一对**。注意扩张的是"保留区"（多留几条），而不是把半个对丢进摘要——保留区变大的代价是多占一点预算，拆对的代价是下一轮请求直接非法。`_pair_indices` 还在入口处断言每个 `pair_id` 恰好两个单元，把"配对完整性"从约定升级为构造时校验。

零预算的语义也值得看：`keep_units=0` 时什么都不保留，包括完整的对——摘要替换全部历史，是合法的极端情况。

对应 Pi：`packages/agent/src/agent-loop.ts` 的 `failToolCallsFromTruncatedMessage`（入历史前保证成对的另一道防线）。机制详解见 [07 章](07-context-and-compaction/README.md)。

## 05 · 事件总线：异常变成数据

[extension_events.py](../learn_pi_lab/labs/extension_events.py) 的 `emit` 只有 25 行，却包含了事件系统的全部纪律：

```python
snapshot = _freeze_value(payload)              # ① 不可变快照
handlers = tuple(self._handlers.get(event, ()))
for handler_index, (_rid, callback) in enumerate(handlers):
    try:
        outcomes.append(EventOutcome(status="ok", ..., value=callback(snapshot)))
    except Exception as error:                 # ② 异常隔离
        outcomes.append(EventOutcome(status="error", ...,
                                     error=f"{type(error).__name__}: {error}"))
```

- **先冻结再广播**：handler 拿到的是不可变快照，谁也无法通过修改 payload 影响后续 handler。
- **`except Exception` 而不是 `BaseException`**：`KeyboardInterrupt` / `SystemExit` 有意放行——用户按 Ctrl+C 必须能立刻停下，事件系统无权吞掉它。
- **异常是结果，不是中断**：一个 handler 崩溃，后续 handler 照常运行，调用方拿到完整的 `EventOutcome` 列表自行决定如何呈现。

对应 Pi：`session.subscribe`（消费侧）与 `pi.on`（扩展侧）的分水岭见 [06 章](06-events-and-extensions/README.md)。

## 06 · RPC 分帧：按行，不按块

[rpc_jsonl.py](../learn_pi_lab/labs/rpc_jsonl.py) 的 `feed` 展示粘包与半包的标准解法：

```python
candidate = self._buffer + chunk
records = candidate.split("\n")
self._buffer = records.pop()          # 最后一段（可能不完整）留回缓冲
for record in records:
    if not record.strip():
        continue                       # 空行跳过
    decoded = json.loads(record)       # 逐行解析，坏行报错且不连累后续
    messages.append(_validate_record(decoded))
```

三行核心，三个决定：

1. **缓冲以行为单位**——`split("\n")` 后把最后一段放回 `_buffer`，半包自动等待下一次 `feed`，粘包自动拆开。不数长度、不猜对齐。
2. **坏帧是协议错误，不是流终止**——`RpcProtocolError` 报给调用方，缓冲区状态由调用方决定是否重置。
3. **无界缓冲有上限**——`max_buffer_bytes` 检查保证一行恶意超长输入不会吃光内存；超限即清空缓冲并报错。

对应 Pi：`packages/coding-agent/docs/rpc.md`（帧契约）。机制详解见 [10 章](10-protocol-and-integration/README.md)。

## 07 · 重试：退避可注入，才可测试

[reliability.py](../learn_pi_lab/labs/reliability.py) 的 `retry` 全文不到 30 行，真正暴露重试的两个本质：

```python
for current_attempt in range(1, attempts + 1):
    try:
        return RetryResult(operation(), current_attempt, tuple(delays))
    except Exception as error:
        if current_attempt == attempts:
            raise RetryExhausted(current_attempt, type(error).__name__) from error
        delay = float(base_delay) * (2 ** (current_attempt - 1))   # 指数：1, 2, 4, ...
        delays.append(delay)
        if sleep is not None:
            sleep(delay)               # ① sleep 是参数，不是 import
```

- **`sleep` 由调用方注入**：测试传 `delays.append`，生产传 `time.sleep`。同一个函数，测试里零等待、确定性、可断言——"离线可验证"就是靠这种依赖注入实现的。
- **`RetryExhausted` 刻意只带 `type(error).__name__`**：最后一次失败的异常文本不进入新异常。错误详情是调试信息，泄漏到上层日志可能带出敏感内容（见 [09 章](09-reliability/README.md) 边界与安全）。
- **先分类的入口不在 retry 里**：这个函数对一切异常一视同仁地退避。调用方应先按 [09 章](09-reliability/README.md) 的矩阵分类——401 之类根本不该进来。

对应 Pi：Provider 层统一重试 + `ProviderRetryEvent`（重试对用户可见）。

## 08 · 系统提示词：两条路径的分歧点

[system_prompt.py](../learn_pi_lab/labs/system_prompt.py) 的 `build_system_prompt` 复现 Pi 的五段拼装，分歧点只有一行：

```python
if options.custom_prompt:
    prompt = options.custom_prompt          # ① 跳过工具清单、指南、文档指针
    prompt += append_section
    prompt += _project_context_section(options.context_files)
    ...
    return prompt

# 默认路径：persona + Available tools + Guidelines + Pi documentation
guidelines = _guidelines_block(tools, options.prompt_guidelines)
```

`_guidelines_block` 里最有意思的是指南的**动态生成与去重**：

```python
if (has_bash or has_powershell) and not has_grep and not has_find and not has_ls:
    add("Use bash for file operations like ls, rg, find")   # 或 PowerShell 变体
for guideline in extra:
    add(guideline)
for guideline in ALWAYS_GUIDELINES:                          # 无条件两条
    add(guideline)
```

指南不是写死的文本，是**根据工具集算出来的**：有专职搜索工具就不教"用 bash 找文件"，有 PowerShell 就换措辞。`add` 内部的去重让调用方重复传入也不产生重复行。技能段的注入条件同理——`skill_read_tool = next((name for name in SKILL_READ_TOOLS if name in tools), None)`，读不了技能文件就不注入。

对应 Pi：`packages/coding-agent/src/core/system-prompt.ts` 的 `buildSystemPrompt` 与 `skillFileReadTool`。完整机制（三级回退链、项目信任、cwd 无开关）见 [04b 章](04b-system-prompt/README.md)。

## 09 · Provider 注册表：元数据与执行的分离

[provider_registry.py](../learn_pi_lab/labs/provider_registry.py) 用 80 行演示"换模型不换代码"：注册表持有**元数据**（名字、窗口、上下文限制），执行经由统一的 `Provider` 接口注入。查看 `lab providers` 的输出即可看到同一套调用代码驱动两个不同的注册模型。

对应 Pi：`pi.registerProvider()` 配 `createProvider` 与 `api`（如 `openAICompletionsApi()`）——协议翻译层与循环彻底解耦。机制详解见 [08 章](08-providers-and-models/README.md)。

## 怎么把这套路标用到别的框架

九个片段分别给出了九个"检查点"。打开任何一个 Agent 框架的源码，都可以按同样的问题去定位：

| 检查点 | 问的问题 |
| --- | --- |
| 循环 | 终止由哪几个信号合流决定？`max_turns` 之外还有取消吗？ |
| 工具权限 | 检查发生在 executor 之前还是之后？拒绝时有无副作用？ |
| 会话存储 | 崩溃在任意一行会损坏多少历史？ |
| 压缩 | 切割点如何保证消息配对完整？ |
| 事件 | 一个订阅者崩溃会影响其他订阅者吗？ |
| 分帧 | 解析按块还是按帧？无界输入有上限吗？ |
| 重试 | sleep 可注入吗？错误文本会不会泄漏到上层？ |
| 系统提示词 | 换人设会不会连带丢掉工具说明？哪些段关不掉？ |
| Provider | 协议差异写在循环里，还是收敛在翻译层？ |

返回 [课程地图](00-course-map.md)。
