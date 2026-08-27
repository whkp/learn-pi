# 消息与记忆 —— 对话历史如何组织与传递

> 模型没有记忆——它看到的"记忆"就是每次请求时喂给它的消息数组，而这个数组由 harness 维护。消息设计的第一原则是 **role 判别**：每条消息用 `role` 字段标明来源，解析、持久化、渲染都按 role 分发。这一章还回答：跨会话的"长期记忆"和对话历史是什么关系。

## 学习目标

- 理解消息为什么按 `role` 判别，以及内容块的类型与顺序。
- 理解工具调用与结果如何成对回填（`toolCallId` 配对）。
- 分清两类记忆：对话历史（harness 维护）与跨会话记忆（单独存储、按需筛选）。

## 一、问题：模型的记忆从哪来

模型每次推理都是一次独立的函数调用，它不记得上次说了什么。所谓"记忆"，是 harness 在每次请求时把**整个消息数组**重新喂给模型。因此：

1. **谁说的**——`role` 字段（判别字段）让 Provider 知道每条消息的来源。
2. **说了什么**——内容块（文本、思考、图片、工具调用）按顺序排列。

消息是判别联合（`AgentMessage`），靠 `role` 区分类型：

| role | 来源 | 内容 |
|------|------|------|
| `user` | 用户 | 纯文本，或文本/图片块 |
| `assistant` | 模型 | 文本、思考块、或 `toolCall`（工具调用请求） |
| `toolResult` | 工具执行 | 结果文本/图片，带 `toolCallId` 与调用配对 |

## 二、工具调用与结果必须成对

`assistant` 发出 `toolCall`（带唯一 `id`），工具执行后产生 `toolResult`（带同一个 `toolCallId`）。**Provider 要求它们成对出现**——如果上下文里有一个没有结果的工具调用，Provider 会拒绝请求。

这个约束的影响贯穿全书：压缩时"成对不拆"（[07 章](../07-context-and-compaction/README.md)）、恢复会话时审计工具记录（[05 章](../05-sessions/README.md)）——根子都在这里。

## 三、消息之上：产品消息与摘要消息

基础的三类消息之上，Pi 通过声明合并扩展产品消息，不破坏统一的 role 判别：

- `bashExecution`：承载命令、输出、退出码、截断标记——bash 工具的专属消息。
- `compactionSummary` / `branchSummary`：压缩与分支摘要，用 XML 包装成模型可读的指令，留在上下文里保留因果。

这些特殊消息依然走同一个消息管线：解析、持久化、渲染都按 role 分发。

## 四、两类记忆的分工

| 记忆 | 存哪 | 生命周期 | 职责 |
|------|------|----------|------|
| 对话历史 | 消息数组 / 会话文件 | 会话内 | 模型推理的完整上下文 |
| 跨会话记忆 | 单独的记忆库 | 跨会话 | 事实、偏好、修正，按需筛选注入 |

跨会话记忆的价值在**筛选，不在积累**：不是把所有历史都存下来，而是把值得复用的事实（用户偏好、项目约定、失败教训）挑选出来，在需要时注入。存储是次要问题，**筛选策略才是记忆系统的核心**——这也是社区记忆类扩展（如 pi-hermes-memory）的着力点。

## 当前 Pi 行为

- 消息是 append-only 的：循环只追加，不修改历史（异常修复除外）。
- 工具结果通过 `toolCallId` 配对；持久化时消息序列化进 JSONL（见 [05 章](../05-sessions/README.md)）。

## 在 Pi 里怎么操作

- 会话文件（`~/.pi/agent/sessions/*.jsonl`）就是消息序列化的产物，可用 [11 章](../11-projects-and-evaluation/README.md) 的 session_inspector 只读统计。
- 跨会话记忆需要安装记忆类扩展（如 pi-hermes-memory，见 [06 章](../06-events-and-extensions/README.md) 的社区扩展表）。

## Python 实验

[mini_agent.py](../../learn_pi_lab/labs/mini_agent.py) 用 dataclass 实现同一个判别联合，`role` 是默认字段值：

```python
@dataclass(frozen=True)
class ToolResultMessage:
    role: str = "toolResult"
    tool_call_id: str = ""   # 与 assistant 的 toolCall 配对
    tool_name: str = ""
    content: str = ""
    is_error: bool = False
```

JSONL 持久化（`dump_messages` / `load_messages`）按 `role` 重建消息，未知 role 的记录**原样保留为 dict**——与 Pi"解析工具应保留未知记录而非静默重写"的约定一致。Tau 的 `tau_agent/messages.py` 用 Pydantic 的 `Field(discriminator="role")` 实现同一模型。

```sh
python3 -m learn_pi_lab lab mini-agent   # 输出含 loaded_roles：JSONL 往返后的角色序列
```

## 验证方式

```sh
python3 -m unittest tests.test_13_mini_agent -v
```

## 边界与安全

- 消息内容可能包含敏感数据（密钥、日志）：持久化与日志输出都应脱敏。
- 不要信任历史中的工具结果：恢复会话后应审计工具调用记录。
- 消息模型是兼容性契约：新增 role 必须向后兼容，未知记录保留而不是丢弃。

## 回顾

- **role 判别**：谁说的、说了什么，按 role 分发处理。
- **成对回填**：工具调用与结果靠 `toolCallId` 配对，Provider 要求成对。
- **两类记忆**：对话历史由 harness 维护；跨会话记忆价值在筛选不在积累。

消息数组会越积越长——窗口装不下时怎么办？下一章讲[会话管理](../05-sessions/README.md)，之后是[上下文压缩](../07-context-and-compaction/README.md)。
