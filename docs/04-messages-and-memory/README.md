# 消息与记忆 —— 对话历史如何组织与传递

> 对模型而言，对话历史就是它能看到的全部上下文。这一章拆解消息系统"如何实现"：role 判别、内容块、工具结果配对、消息如何序列化，以及跨会话记忆与对话历史的区别。

## 学习目标

- 理解消息为什么按 `role` 判别（user / assistant / toolResult / ...）。
- 理解内容块的类型与顺序，以及工具调用如何与结果配对。
- 分清两类"记忆"：对话历史（harness 维护）与跨会话记忆（单独存储）。
- 读 Pi 0.84.2 的消息类型实现，并对照本课程的 Python 教学模型与 JSONL 持久化。

## 机制：消息数组由 harness 维护，不是模型记住的

模型没有记忆。它看到的"记忆"就是每次请求时喂给它的消息数组——而这个数组由 harness 维护：追加用户消息、追加 assistant 回复、追加工具结果，再整体发给模型。模型每次推理都是一次独立的函数调用，看到的只是传入的消息。

消息设计决定两件事：

1. **谁说的**——`role` 字段（判别字段）让 Provider 知道每条消息的来源。
2. **说了什么**——内容块（文本、思考、图片、工具调用）按顺序排列。

关键约束：**工具调用（assistant 发出）与工具结果（toolResult）必须成对出现**，否则 Provider 会拒绝该上下文——这也是 [07 章](../07-context-and-compaction/README.md) 压缩时"成对不拆"的根因。

### 两类记忆的分工

| 记忆 | 存哪 | 生命周期 | 职责 |
|------|------|----------|------|
| 对话历史 | 消息数组 / 会话文件 | 会话内 | 模型推理的完整上下文 |
| 跨会话记忆 | 单独的记忆库 | 跨会话 | 事实、偏好、修正，按需筛选注入 |

跨会话记忆的价值在**筛选，不在积累**：不是把所有历史都存下来，而是把值得跨会话复用的事实（用户偏好、项目约定、失败教训）挑选出来，在需要时注入。存储是次要问题，筛选策略才是记忆系统的核心。

## Pi 源码怎么实现（0.84.2）

### 基础消息类型：pi-ai 包

用户/助手/工具结果三类基础消息定义在 `packages/ai/src/types.ts`：

```typescript
// packages/ai/src/types.ts（Pi 0.84.2，节选）
export interface TextContent {
  type: "text";
  text: string;
  textSignature?: string; // 如 OpenAI responses 的元数据
}

export interface ImageContent {
  type: "image";
  data: string;      // base64 编码
  mimeType: string;  // "image/jpeg" 等
}

export interface ToolCall {
  type: "toolCall";
  id: string;
  name: string;
  arguments: Record<string, any>;
}

export interface UserMessage {
  role: "user";
  content: string | (TextContent | ImageContent)[];
  timestamp: number; // Unix 毫秒
}

export interface AssistantMessage {
  role: "assistant";
  content: (TextContent | ThinkingContent | ToolCall)[];
  // ...api / model / stopReason / errorMessage / usage 等字段
}
```

要点：

- **内容块是判别联合**：`TextContent` / `ImageContent` / `ThinkingContent` / `ToolCall` 都带 `type` 字段，解析时按 `type` 分发。
- **ToolCall 嵌在 assistant 的 content 里**：一次 assistant 回复可以包含文本 + 多个工具调用，顺序即模型输出的顺序。
- **ToolResultMessage 用 `toolCallId` 与调用配对**（`AgentMessage` 联合定义在 `packages/agent/src/types.ts`，`ToolResultMessage` 在 `packages/ai/src/types.ts`），Provider 依赖这个配对关系。

### 产品层消息：harness/messages.ts

Agent 核心之上，产品层还有扩展消息类型，例如 `BashExecutionMessage`（role `"bashExecution"`）专门承载命令、输出、退出码、截断标记：

```typescript
// packages/agent/src/harness/messages.ts（Pi 0.84.2，节选）
export interface BashExecutionMessage {
  role: "bashExecution";
  command: string;
  output: string;
  exitCode: number | undefined;
  cancelled: boolean;
  truncated: boolean;
  fullOutputPath?: string;
  timestamp: number;
  excludeFromContext?: boolean;
}
```

`AgentMessage` 是判别联合 `Message | CustomAgentMessages[...]`，产品消息通过 TypeScript 声明合并（`CustomAgentMessages`）扩展——**新增角色不破坏统一的消息处理**：解析、持久化、渲染都按 `role` 分发。

### 摘要消息：压缩与分支的载体

压缩与分支摘要也以消息形式存在（`harness/messages.ts`）：

```typescript
export const COMPACTION_SUMMARY_PREFIX = `The conversation history before this point was compacted into the following summary:

<summary>
`;
export const COMPACTION_SUMMARY_SUFFIX = `\n</summary>`;
```

压缩摘要用 XML 包装后作为一条普通消息留在上下文里——它既有自己的 `role`（`compactionSummary`），渲染成文本时又是模型可读的指令。这是"摘要继续保留因果"的具体实现（见 [07 章](../07-context-and-compaction/README.md)）。

## 当前 Pi 行为

- 消息是 append-only 的：循环只追加，不修改历史（异常修复除外）。
- 工具结果通过 `toolCallId` 与 assistant 的 `toolCall` 块配对；Provider 需要这种配对关系。
- 持久化时消息序列化进 JSONL（见 [05 章](../05-sessions/README.md)）。
- 压缩摘要、分支摘要都以消息形式进入上下文，不破坏角色判别。

## 在 Pi 里怎么操作

- 会话文件（`~/.pi/agent/sessions/*.jsonl`）就是消息序列化的产物，可以用 [11 章](../11-projects-and-evaluation/README.md) 的 session_inspector 只读统计。
- `/export [file]` 把消息历史导出为 HTML。
- 跨会话记忆需要安装记忆类扩展（如 pi-hermes-memory，见 [06 章](../06-events-and-extensions/README.md) 的社区扩展表）。

## Python 对照

[mini_agent.py](../../learn_pi_lab/labs/mini_agent.py) 用三个 dataclass 实现同一个判别联合，`role` 是默认字段值：

```python
@dataclass(frozen=True)
class ToolResultMessage:
    role: str = "toolResult"
    tool_call_id: str = ""
    tool_name: str = ""
    content: str = ""
    is_error: bool = False
```

JSONL 持久化（`dump_messages` / `load_messages`）按 `role` 重建消息，未知 role 的记录原样保留为 dict——与 Pi"解析工具应保留未知记录而非静默重写"的约定一致：

```python
def _from_record(record):
    role = record.get("role")
    if role == "user":        return UserMessage(content=str(record.get("content", "")))
    if role == "assistant":   return AssistantMessage(content=..., tool_calls=..., stop_reason=...)
    if role == "toolResult":  return ToolResultMessage(tool_call_id=..., tool_name=..., ...)
    return record  # 未知角色原样保留
```

Tau 对照：`tau_agent/messages.py` 用 Pydantic 实现同一套角色模型，`AgentMessage` 同样是按 `role` 判别的联合类型（`Annotated[...Field(discriminator="role")]`）。

## 实现对照：Pi 源码与 Tau 双版本

消息类型是两套实现里最“同构”的部分——同样的 role 判别，Pi 用 TypeScript 接口、Tau 用 Pydantic 模型。

**消息的判别联合**：

```typescript
// Pi 0.84.2: packages/agent/src/types.ts（原文节选）
export type AgentMessage = Message | CustomAgentMessages[keyof CustomAgentMessages];
// Message（pi-ai 包）按 role 判别：
//   role: "user" | "assistant" | "toolResult"
```

```python
# Tau: tau_agent/messages.py（原文节选）
type AgentMessage = Annotated[
    UserMessage | AssistantMessage | ToolResultMessage
    | BashExecutionMessage | CustomMessage
    | BranchSummaryMessage | CompactionSummaryMessage,
    Field(discriminator="role"),
]
```

概念对照：TS 的判别联合 → Python 的 `Annotated[...Field(discriminator="role")]`，两者都靠 `role` 字段区分消息类型。

**单条消息**（工具结果为例）：

```typescript
// Pi 0.84.2: packages/ai/src/types.ts（原文节选）
export interface ToolResultMessage<TDetails = any> {
  role: "toolResult";
  toolCallId: string;
  toolName: string;
  content: (TextContent | ImageContent)[]; // 支持文本与图片
  details?: TDetails;
  usage?: Usage;      // 工具自身的 token 用量，不计入主上下文
  addedToolNames?: string[];  // 本结果之后新可用的工具名
  isError: boolean;
}
```

```python
# Tau: tau_agent/messages.py（原文节选）
class ToolResultMessage(WireModel):
    role: Literal["toolResult"] = "toolResult"
    tool_call_id: str
    tool_name: str
    content: list[ToolResultContent] = Field(default_factory=list)
    details: JSONValue = None
    added_tool_names: list[str] | None = None
    is_error: bool = False
    timestamp: int = Field(default_factory=current_timestamp_ms)
```

对应关系：TS 的 `toolCallId` / `isError` ↔ Python 的 `tool_call_id` / `is_error`（WireModel 序列化时自动转回驼峰，保持 Pi 兼容的线格式）。`toolCallId` 是配对键——Provider 靠它把结果接到 assistant 的 `toolCall` 块上。

**持久化**：Tau 用同一个判别模型做 JSONL 编解码（`tau_agent/session/jsonl.py`），未知 role 会在校验时报错而不是静默改写——与本课程 [05 章](../05-sessions/README.md) 的“保留未知记录”约定一致。

## Python 实验

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
- 跨会话记忆只注入经过筛选的事实；未经验证的记忆内容不应被当作可信指令。
