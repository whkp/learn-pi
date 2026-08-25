# 上下文压缩 —— 有限窗口如何装下无限对话

> 上下文窗口是固定的，对话是增长的。这一章拆解上下文工程与压缩"如何实现"：两层防护、压缩触发条件、切割点选择与"成对不拆"。

## 学习目标

- 理解上下文工程的两层防护：输入侧（工具输出截断）与历史侧（压缩）。
- 掌握压缩触发条件与切割点选择的设计。
- 理解为什么成对的工具调用/结果不能在被切割点拆开。

## 机制：上下文预算与两层防护

先把窗口看成**预算**：窗口大小是上限，每次请求的 token 用量都在消耗预算。预算不足时只有两条路——拒绝处理，或者腾出空间（压缩）。

| 防护 | 时机 | 手段 |
|------|------|------|
| 输入侧 | 工具结果进入上下文之前 | 截断：行数 + 字节双重限制，truncateHead / truncateTail |
| 历史侧 | 上下文即将超限时 | 压缩：让模型总结旧消息，保留近期窗口 |

输入侧解决“一条 bash 命令就能占满窗口”；历史侧解决“对话本身太长”。两者都做，窗口才能稳定。

**压缩不是丢消息，是让模型总结它自己**：把撑爆预算的旧对话交给模型总结成摘要，原样保留最近的部分，摘要继续留在上下文里以保留因果。

**压缩的三个设计问题**：什么时候触发？切在哪？切掉的部分怎么保留因果？Pi 的回答是：触发看阈值，切割点选在 Turn 边界（工具调用/结果不拆开），被切掉的内容总结成摘要消息继续保留。

### 截断的细节：双重限制与边界安全

工具输出截断（`packages/agent/src/harness/utils/truncate.ts`）有两个设计要点：

1. **双重限制，先触者胜**：行数（默认 2000 行）+ 字节数（默认 50KB）同时计数，任一超限即截断。只限行数挡不住超长单行；只限字节挡不住海量短行。
2. **不切半行 + UTF-8 安全**：截断只发生在完整行边界，绝不从多字节字符中间切开；如果第一行就超字节上限，返回空内容并标记 `firstLineExceedsLimit`，而不是返回半个字符。

截断策略分两种：`truncateHead`（保留开头，适合文件读取）与 `truncateTail`（保留结尾，适合命令输出）。bash 工具用的是 tail——命令的最终输出（错误信息、退出状态）通常在结尾。

核心实现（`truncateHead`）：

```typescript
// packages/agent/src/harness/utils/truncate.ts（Pi 0.84.2，原文节选）
export const DEFAULT_MAX_LINES = 2000;
export const DEFAULT_MAX_BYTES = 50 * 1024; // 50KB

/**
 * 从头部截断（保留前 N 行/字节），适合文件读取。
 * 绝不返回半行；如果第一行就超字节上限，返回空内容并置 firstLineExceedsLimit。
 */
export function truncateHead(content: string, options: TruncationOptions = {}): TruncationResult {
  const maxLines = options.maxLines ?? DEFAULT_MAX_LINES;
  const maxBytes = options.maxBytes ?? DEFAULT_MAX_BYTES;

  const totalBytes = utf8ByteLength(content);
  const lines = splitLinesForCounting(content);
  const totalLines = lines.length;

  // 未超限：原样返回
  if (totalLines <= maxLines && totalBytes <= maxBytes) {
    return { content, truncated: false, totalLines, totalBytes, ... };
  }

  // 第一行就超字节上限：返回空内容，绝不切半个字符
  const firstLineBytes = utf8ByteLength(lines[0]);
  if (firstLineBytes > maxBytes) {
    return { content: "", truncated: true, truncatedBy: "bytes", firstLineExceedsLimit: true, ... };
  }
  // ...否则按完整行边界逐行累加，直到行数或字节数将超限
}
```

要点：返回值 `TruncationResult` 包含 `totalLines` / `totalBytes` / `truncatedBy`——截断不是静默的，**截断事实本身也是结果的一部分**，bash 工具会把它写进描述与 details，让模型知道输出不完整。

## Pi 源码怎么实现（0.84.2）

压缩核心在 `packages/agent/src/harness/compaction/compaction.ts`：

```typescript
// packages/agent/src/harness/compaction/compaction.ts（Pi 0.84.2，节选）
export function shouldCompact(
  contextTokens: number,
  contextWindow: number,
  settings: CompactionSettings,
): boolean {
  if (!settings.enabled) return false;
  return contextTokens > contextWindow - settings.reserveTokens;
}

// 默认保留近期 token 预算：
keepRecentTokens: 20000,
```

- **触发**：`contextTokens > contextWindow - reserveTokens`——不是等窗口满了才压缩，而是提前预留缓冲。
- **切割点**：`findCutPoint` 在候选点中找能保留约 `keepRecentTokens` 的位置，优先选择 Turn 边界，避免把一个 Turn 的“工具调用 + 结果”拆到两边。
- **结果**：被切掉的部分生成 `compactionSummary` 消息（含 `tokensBefore`），摘要本身留在上下文里。

### findCutPoint：切割点怎么找

`findCutPoint`（373 行）分三步：

```typescript
// 1. 找所有合法切割点：只在 Turn 边界（user 消息前、compaction 记录前）设候选
const cutPoints = findValidCutPoints(entries, startIndex, endIndex);

// 2. 从尾部向前累加 token，直到凑够 keepRecentTokens，
//    然后把切割点推到最近的候选点（不拆开本 Turn）
let accumulatedTokens = 0;
let cutIndex = cutPoints[0];
for (let i = endIndex - 1; i >= startIndex; i--) {
  const entry = entries[i];
  if (entry.type !== "message") continue;
  accumulatedTokens += estimateTokens(entry.message);
  if (accumulatedTokens >= keepRecentTokens) { /* 取最近的候选点 */ break; }
}

// 3. 向前越过非消息记录（model_change 等），并判断是否切在 Turn 中间
while (cutIndex > startIndex) {
  const prevEntry = entries[cutIndex - 1];
  if (prevEntry.type === "compaction") break;   // 不越过上次压缩点
  if (prevEntry.type === "message") break;
  cutIndex--;                                    // 操作记录不占上下文，可越过后继续切
}
```

关键取舍：**切割点宁可多保留一点，也不拆开一个 Turn**。`isSplitTurn` 标记用于提示摘要生成时该 Turn 的因果信息；`compaction` 记录本身是合法的停止点，不会越过它。

## 当前 Pi 行为

- 自动压缩：上下文超过阈值时触发；手动：`/compact [指令]`，可选指令聚焦摘要内容。
- `/tree` 切换分支时为离开的分支生成摘要（分支摘要），是导航的上下文保留行为，不是导出功能。
- 扩展在压缩前的定制边界是 `session_before_compact`。

## 在 Pi 里怎么操作

- 自动压缩默认开启；在设置里调整阈值/开关。
- 手动压缩：`/compact [指令]`。
- 分支摘要：`/tree` 切换分支时自动生成。

## Python 对照

[compaction.py](../../learn_pi_lab/labs/compaction.py) 演示切割点的核心约束——**成对不拆**：`choose_cut` 从最近后缀出发，只要切割点落在某对 `pair_id`（工具调用 + 结果）中间就向前扩展，直到不再拆开任何一对：

```python
for indices in pair_indices.values():
    includes_pair_unit = any(index >= start for index in indices)
    excludes_pair_unit = any(index < start for index in indices)
    if includes_pair_unit and excludes_pair_unit:
        expanded_start = min(expanded_start, min(indices))
```

[context_files.py](../../learn_pi_lab/labs/context_files.py) 与 [resources.py](../../learn_pi_lab/labs/resources.py) 则对应输入侧：规则文件（`.course-rules.md`）从根到工作目录逐级发现、拒绝符号链接；资源（`LESSON.md`）递归扫描、拒绝重复名称——都是"什么能进上下文"的边界控制。

Tau 对照：`tau_agent/session/memory.py` 提供上下文压缩相关实现；`tau_coding/context_window.py` 负责窗口计算。

## 实现对照：Pi 源码与 Tau 双版本

压缩的实现两套都分成“决定何时切”与“把切掉的部分变成摘要”两步。

**触发条件**：

```typescript
// Pi 0.84.2: packages/agent/src/harness/compaction/compaction.ts（原文节选）
export function shouldCompact(contextTokens, contextWindow, settings): boolean {
  if (!settings.enabled) return false;
  return contextTokens > contextWindow - settings.reserveTokens;
}
```

```python
# Tau: tau_agent/session/memory.py（原文节选，概念改写）
# 概念对照：TS 的 contextWindow - reserveTokens → Python 的 window - reserve
# Tau 把同一逻辑组织在 SessionState 的压缩决策里
if context_tokens > window - reserve_tokens:
    apply_compaction(...)  # 生成 CompactionEntry
```

**切割后的应用**——Pi 用 `findCutPoint` 决定切在哪，Tau 用 `replaces_entry_ids` 记录替换了哪些 entry，回放时把旧消息换成摘要：

```python
# Tau: tau_agent/session/memory.py 的 _apply_compaction（原文节选）
def _apply_compaction(message_rows, entry):
    replaced_ids = set(entry.replaces_entry_ids)
    retained = []
    inserted_summary = False
    for entry_id, message in message_rows:
        if entry_id not in replaced_ids:
            retained.append((entry_id, message))
            continue
        if not inserted_summary:
            retained.append((entry.id, UserMessage(
                content=f"Previous conversation summary:\n{entry.summary}")))
            inserted_summary = True
    return retained
```

两套实现共享同一个设计原则：**压缩是“替换”不是“删除”**——旧消息不消失，而是被一条摘要消息替换，摘要继续留在上下文里保留因果。Pi 的切割点选择（[上文的 findCutPoint](#findcutpoint切割点怎么找)）解决“切在哪”；Tau 的 `replaces_entry_ids` 解决“替换哪些”。

## Python 实验

```sh
python3 -m learn_pi_lab lab compaction   # 打印保留/摘要集合
```

## 验证方式

```sh
python3 -m unittest tests.test_05_compaction tests.test_03_context_files tests.test_06_resources -v
```

## 边界与安全

- 压缩前后都应能回答：保留了哪个用户目标、哪些文件被修改、哪些工具结果仍相关、哪些事实只是旧摘要。
- 摘要中的不确定性必须标明，不能伪造验证结果。
- 本课程实验不估算 token、不调用 LLM、不写 Pi 的会话文件。
