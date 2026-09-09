# 上下文压缩 —— 有限窗口如何装下无限对话

> 上下文窗口是固定的，对话是增长的。Pi 的上下文工程核心设计是**两层防护**：输入侧截断工具输出，历史侧压缩旧对话。而压缩的设计原则只有一条——**压缩不是丢消息，是让模型总结它自己**：把撑爆预算的旧对话交给模型总结成摘要，原样保留最近的部分，摘要继续留在上下文里保留因果。

## 学习目标

- 理解两层防护：输入侧（工具输出截断）与历史侧（压缩）各解决什么问题。
- 理解压缩触发条件与"成对不拆"的切割约束。
- 理解为什么摘要必须留在上下文里（保留因果），以及 token 估算为何"不精确但够用"。

## 一、问题：窗口是固定的，对话是增长的

模型的上下文窗口是硬上限（如 128K token）。对话越聊越长，迟早撑爆窗口。不处理会怎样？两个选择：拒绝继续（用户无法接受），或者**静默截断**（更糟——模型不知道前面发生了什么，因果断裂，回答质量崩坏）。

Pi 的答案是把"窗口"当作**预算**来管理：窗口大小是上限，每次请求都在消耗预算。预算不足时腾出空间。

## 二、两层防护：各管一段

| 防护 | 时机 | 手段 |
|------|------|------|
| 输入侧 | 工具结果进入上下文之前 | 截断：行数（2000 行）+ 字节（50KB）双重限制 |
| 历史侧 | 上下文即将超限时 | 压缩：让模型总结旧消息，保留近期窗口 |

- **输入侧**解决"一条 bash 命令就占满窗口"——工具输出在进入上下文之前就截断。
- **历史侧**解决"对话本身太长"——旧对话被总结成摘要。

两者都做，窗口才能稳定。只做输入侧，对话还是会越来越长；只做历史侧，一条超长命令输出就能瞬间占满窗口。

### 截断的两个细节

1. **双重限制，先触者胜**：只限行数挡不住超长单行，只限字节挡不住海量短行。
2. **不切半行 + UTF-8 安全**：截断只发生在完整行边界；如果第一行就超字节上限，返回空内容并标记，而不是切出半个字符。**截断事实本身也是结果的一部分**——bash 工具会告知模型"输出不完整，完整输出在临时文件里"。

## 三、压缩的三个设计问题

### 什么时候触发？

Pi 的 `shouldCompact` 判断：`contextTokens > contextWindow - reserveTokens`。注意**不是等窗口满了才压缩**，而是提前预留缓冲——因为压缩本身也要消耗 token。

### 在哪切？

切割点有两个约束：

1. **切在 Turn 边界，不拆开成对的工具调用与结果**——因为 Provider 要求它们成对出现（见 [04 章](../04-messages-and-memory/README.md)）。宁可多保留一点，也不拆开一个 Turn。
2. **不越过上次的压缩点**——压缩记录本身是合法的切割点。

### 切掉的部分怎么处理？

**不是删除，是替换**：被切掉的旧消息被一条摘要消息（`compactionSummary`）替换，摘要留在上下文里。摘要不是自由文本，而是结构化记录用户目标、关键决策、进行中的工作——让模型在窗口缩小后依然知道"我们本来要干什么"。

### token 估算：不精确但够用

触发判断需要知道"现在用了多少 token"，但精确计算代价高。Pi 用字符数启发式估算（文本按字符、图片按固定估算值）——误差在可控范围，足够做"是否该压缩"的决策。

## 当前 Pi 行为

- 自动压缩默认开启；手动压缩 `/[compact 指令]`，可选指令聚焦摘要内容。
- `/tree` 切换分支时为离开的分支生成摘要（分支摘要），是导航的上下文保留行为，不是导出功能。
- 扩展在压缩前的定制边界是 `session_before_compact`。
- 压缩属于"可能很长的准备"：循环在准备结束后会再取一次 steering 消息（`agent-loop.ts` 191 行的注释明确点名 compaction），压缩期间用户输入不会丢。

### 源码证据表

| 教学结论 | Pi 路径 / 符号 | 说明 |
|---|---|---|
| 压缩期间不吞用户输入 | `packages/agent/src/agent-loop.ts`（191） | "Preparation can be long-running (for example, compaction)" |
| 压缩前扩展边界 | `session_before_compact` | extensions 文档与 `extensions/types.ts` |
| 成对完整不变量 | `packages/agent/src/agent-loop.ts` `failToolCallsFromTruncatedMessage` | 入历史前保证 toolCall/toolResult 成对 |
| 压缩的教学模型 | `learn_pi_lab/labs/compaction.py` | `compact()` 与 `COMPACTION_FIXTURE` |

## 失败与边界实验

`tests/test_05_compaction` 覆盖的三类边界，都指向同一条不变量——**压缩后历史仍然合法**：

1. **压缩点选在工具批中间。** 摘要替换掉旧消息后，某个 `toolCall` 的 `toolResult` 被丢了——下一轮请求直接被 API 拒绝。修法：压缩边界必须对齐消息边界，且成对消息要么都进摘要、要么都保留。
2. **摘要溢出预算。** 历史太大，摘要本身又接近窗口上限——压缩等于没压。修法：摘要也受预算约束；必要时对摘要再压缩，而不是允许摘要无限膨胀。
3. **敏感信息进摘要。** 压缩让模型复述历史，密钥、个人路径会被写进摘要并长期驻留。修法：`session_before_compact` 钩子在压缩前脱敏；这是扩展介入压缩的唯一合法时机。

```sh
python3 -m learn_pi_lab lab compaction
python3 -m unittest tests.test_05_compaction -v
```

## 在 Pi 里怎么操作

```sh
/compact 聚焦:这次会话改动了哪些文件   # 手动压缩，带聚焦指令
```

## Python 实验

[compaction.py](../../learn_pi_lab/labs/compaction.py) 演示切割点的核心约束——**成对不拆**：`choose_cut` 从最近后缀出发，只要切割点落在某对 `pair_id`（工具调用 + 结果）中间就向前扩展，直到不再拆开任何一对：

```python
while True:
    expanded_start = start
    for indices in pair_indices.values():
        includes_pair_unit = any(index >= start for index in indices)
        excludes_pair_unit = any(index < start for index in indices)
        if includes_pair_unit and excludes_pair_unit:
            expanded_start = min(expanded_start, min(indices))  # 拆开了一对，向前扩展
    if expanded_start == start:
        break
    start = expanded_start
```

[context_files.py](../../learn_pi_lab/labs/context_files.py)（规则文件逐级发现、拒绝符号链接）与 [resources.py](../../learn_pi_lab/labs/resources.py)（资源扫描、拒绝重复名称）对应输入侧"什么能进上下文"的边界控制。Tau 的 `tau_agent/session/memory.py` 用 `replaces_entry_ids` 记录被替换的 entry，回放时把旧消息换成摘要。

```sh
python3 -m learn_pi_lab lab compaction   # 打印保留/摘要集合
```

> 这一模块的核心代码在[核心代码导览 · 压缩切割点](../code-tour.md)有逐段解读。

## 验证方式

```sh
python3 -m unittest tests.test_05_compaction tests.test_03_context_files tests.test_06_resources -v
```

## 边界与安全

- 压缩前后都应能回答：保留了哪个用户目标、哪些文件被修改、哪些工具结果仍相关。
- 摘要中的不确定性必须标明，不能伪造验证结果。
- 本课程实验不估算 token、不调用 LLM、不写 Pi 的会话文件。

## 回顾

- **两层防护**：输入侧截断工具输出，历史侧压缩旧对话。
- **压缩不是丢消息，是让模型总结它自己**：摘要留在上下文里保留因果。
- **成对不拆**：切割点不拆开工具调用与结果；不越过上次压缩点。
- **提前预留缓冲**：`contextWindow - reserveTokens` 才触发。

窗口管理之外，Agent 还要面对"换模型、接多家 Provider"——下一章[Provider 与模型](../08-providers-and-models/README.md)。
