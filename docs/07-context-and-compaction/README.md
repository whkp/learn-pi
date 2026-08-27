# 上下文压缩 —— 有限窗口如何装下无限对话

> 上下文窗口是固定的，对话是增长的。Pi 的上下文工程核心设计是**两层防护**：输入侧截断工具输出，历史侧压缩旧对话。而压缩的设计原则只有一条——**压缩不是丢消息，是让模型总结它自己**：把撑爆预算的旧对话交给模型总结成摘要，原样保留最近的部分，摘要继续留在上下文里保留因果。

## 学习目标

- 理解两层防护：输入侧（工具输出截断）与历史侧（压缩）。
- 理解压缩触发条件与"成对不拆"的切割约束。
- 理解为什么摘要必须留在上下文里（保留因果）。

## Pi 的核心设计

### 窗口即预算

把窗口看成**预算**：窗口大小是上限，每次请求都在消耗预算。预算不足时只有两条路——拒绝处理，或腾出空间（压缩）。

| 防护 | 时机 | 手段 |
|------|------|------|
| 输入侧 | 工具结果进入上下文之前 | 截断：行数（2000 行）+ 字节（50KB）双重限制 |
| 历史侧 | 上下文即将超限时 | 压缩：让模型总结旧消息，保留近期窗口 |

输入侧解决"一条 bash 命令就占满窗口"；历史侧解决"对话本身太长"。两者都做，窗口才能稳定。

### 压缩的触发与切割

- **触发**：Pi 的 `shouldCompact` 判断 `contextTokens > contextWindow - reserveTokens`——不是等窗口满了才压缩，而是提前预留缓冲。
- **切割**：切割点选在 Turn 边界，**不拆开成对的工具调用与结果**——因为 Provider 要求它们成对出现（见 [04 章](../04-messages-and-memory/README.md)）。宁可多保留一点，也不拆开一个 Turn。
- **保留**：被切掉的部分生成 `compactionSummary` 消息（含压缩前的 token 数），摘要本身留在上下文里。

### 截断的两个细节

1. **双重限制，先触者胜**：只限行数挡不住超长单行，只限字节挡不住海量短行。
2. **不切半行 + UTF-8 安全**：截断只发生在完整行边界；如果第一行就超字节上限，返回空内容并标记，而不是切出半个字符。截断事实本身也是结果的一部分（bash 工具会告知模型"输出不完整"）。

## 当前 Pi 行为

- 自动压缩默认开启；手动压缩 `/[compact 指令]`，可选指令聚焦摘要内容。
- `/tree` 切换分支时为离开的分支生成摘要（分支摘要），是导航的上下文保留行为，不是导出功能。
- 扩展在压缩前的定制边界是 `session_before_compact`。

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

## 验证方式

```sh
python3 -m unittest tests.test_05_compaction tests.test_03_context_files tests.test_06_resources -v
```

## 边界与安全

- 压缩前后都应能回答：保留了哪个用户目标、哪些文件被修改、哪些工具结果仍相关。
- 摘要中的不确定性必须标明，不能伪造验证结果。
- 本课程实验不估算 token、不调用 LLM、不写 Pi 的会话文件。
