# 消息与记忆 —— 对话历史如何组织与传递

> 模型没有记忆——它看到的"记忆"就是每次请求时喂给它的消息数组，而这个数组由 harness 维护。消息设计的核心是 **role 判别**：每条消息用 `role` 字段标明来源（user / assistant / toolResult），解析、持久化、渲染都按 role 分发。

## 学习目标

- 理解消息为什么按 `role` 判别，以及内容块的类型与顺序。
- 理解工具调用与结果如何成对回填。
- 分清两类记忆：对话历史（harness 维护）与跨会话记忆（单独存储、按需筛选）。

## Pi 的核心设计

### role 判别：消息是判别联合

Pi 的消息是判别联合（`AgentMessage`），靠 `role` 字段区分类型：

- `user`：用户消息，内容可以是纯文本或文本/图片块。
- `assistant`：助手回复，内容块可以是文本、思考、或 `toolCall`（工具调用请求）。
- `toolResult`：工具执行结果，用 `toolCallId` 与 assistant 的调用**配对**。

关键约束：**工具调用与工具结果必须成对出现**，否则 Provider 会拒绝该上下文——这也是 [07 章](../07-context-and-compaction/README.md) 压缩时"成对不拆"的根因。Pi 在基础消息之上通过声明合并扩展产品消息（如 `bashExecution` 承载命令/输出/退出码/截断标记），不破坏统一的 role 判别。

### 两类记忆的分工

| 记忆 | 存哪 | 职责 |
|------|------|------|
| 对话历史 | 消息数组 / 会话文件 | 模型推理的完整上下文 |
| 跨会话记忆 | 单独的记忆库 | 事实、偏好、修正，按需筛选注入 |

跨会话记忆的价值在**筛选，不在积累**：不是把所有历史存下来，而是把值得复用的事实挑选出来在需要时注入。存储是次要问题，筛选策略才是记忆系统的核心。

### 摘要也是消息

Pi 的压缩摘要、分支摘要都以消息形式进入上下文（role `compactionSummary`/`branchSummary`），用 XML 包装成模型可读的指令——"摘要继续保留因果"的具体实现，见 [07 章](../07-context-and-compaction/README.md)。

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

- 消息内容可能包含敏感数据：持久化与日志输出都应脱敏。
- 不要信任历史中的工具结果：恢复会话后应审计工具调用记录。
- 消息模型是兼容性契约：新增 role 必须向后兼容，未知记录保留而不是丢弃。
