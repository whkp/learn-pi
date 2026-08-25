# 事件驱动与扩展 —— 事件如何对外暴露，扩展如何介入

> Agent 每走一步都发出事件；扩展通过事件观察甚至改写行为。这一章拆解事件系统“如何实现”：事件即契约、两种监听机制的差异、扩展生命周期。

## 学习目标

- 理解“事件是契约”：前端（TUI / JSON / RPC / 自定义）都消费同一个类型化事件流。
- 分清两条监听通道：`session.subscribe`（只读观察，Agent 不等你）与 `pi.on`（可拦截改写，Agent 会等你）。
- 理解扩展能力的本质：子代理、MCP 等高级能力都是“一个工具”。

## 机制：两条监听通道与“能力即工具”

### 两条监听通道的根本差异

Pi 有两套并行的监听机制，共享同一批事件源，但**“Agent 等不等你的 listener”是分水岭**：

| 维度 | `session.subscribe` | 扩展的 `pi.on` |
|------|--------------------|----------------|
| 用途 | 只读观察：日志、UI、统计 | 拦截与改写：权限、输入改写 |
| Agent 是否等待 | 不等（fire-and-forget） | 等（await 处理完再继续） |
| 适用方 | SDK 宿主程序 | TypeScript 扩展 |

只学一套一定会遇到“代码写了却静默不生效”的情况：在 `subscribe` 里想拦截工具调用是做不到的，必须用 `pi.on`。

### 能力即工具：subagent 与 MCP 的同一本质

一个统一视角：**Pi 核心不内置的高级能力，本质上都是一个工具**。

- **subagent**：`pi-subagents` 通过一个 `subagent` 工具，让主循环把工作委托给子代理——子代理本身又是一个独立的 Agent Loop，但对外表现为一个工具调用。
- **MCP**：MCP 适配器把外部服务器的工具“接入”当前工具池，对外同样是工具。

这个视角解释了 Pi 的设计取舍：为什么核心不内置子代理、计划模式、MCP——因为这些都可以用工具实现，按需扩展，而不是塞进核心。

### 事件全集与分层

Agent 核心层的事件（`packages/agent/src/types.ts`）是运行时自身的生命周期：

```typescript
export type AgentEvent =
  // Agent 生命周期
  | { type: "agent_start" }
  | { type: "agent_end"; messages: AgentMessage[] }
  // Turn 生命周期：一次 assistant 回复 + 其触发的工具
  | { type: "turn_start" }
  | { type: "turn_end"; message: AgentMessage; toolResults: ToolResultMessage[] }
  // 消息生命周期
  | { type: "message_start"; message: AgentMessage }
  | { type: "message_update"; message: AgentMessage; assistantMessageEvent: AssistantMessageEvent }
  | { type: "message_end"; message: AgentMessage }
  // 工具执行生命周期
  | { type: "tool_execution_start"; toolCallId: string; toolName: string; args: any }
  | { type: "tool_execution_update"; toolCallId: string; toolName: string; args: any; partialResult: any }
  | { type: "tool_execution_end"; toolCallId: string; toolName: string; result: any; isError: boolean };
```

产品层（`packages/coding-agent/src/core/extensions/types.ts`）在其上叠加扩展事件，覆盖会话生命周期、Provider 请求改写、工具执行前后等时点：

| 分组 | 事件（节选） | 用途 |
|------|-------------|------|
| 会话生命周期 | `session_start` / `session_before_switch` / `session_before_fork` / `session_before_compact` / `session_shutdown` | 初始化资源、拦截会话操作、清理 |
| 上下文 | `context` | 注入/改写上下文 |
| Provider | `before_provider_request` / `before_provider_headers` / `after_provider_response` | 改写请求头、观察响应 |
| Agent 循环 | `agent_start` / `turn_start` / `tool_execution_*` / `message_*` | 观察与拦截循环 |
| 用户操作 | `model_select` / `thinking_level_select` / `user_bash` | 观察用户切换模型、执行 bash |

`session_shutdown` 是会话关闭事件的正确名称；没有 `settings_change` 事件；工具输入改写是在事件对象上原地进行（不存在返回 `modifiedInput` 的协议）。

## Pi 源码怎么实现（0.84.2）

事件发射在 `packages/coding-agent/src/core/agent-session-runtime.ts`：

```typescript
// packages/coding-agent/src/core/agent-session-runtime.ts（Pi 0.84.2，节选）
private async emitBeforeSwitch(reason: "new" | "resume", sessionPath?: string) {
  const result = await runner.emit({ ... });   // 扩展监听器，Agent 会等
  // ...
}
private async emitBeforeFork(entryId: string, options: ...) {
  const result = await runner.emit({ ... });
}
// 会话关闭：
await emitSessionShutdownEvent(this.session.extensionRunner, {
  type: "session_shutdown", ...
});
```

要点：`runner.emit(...)` 是**可拦截**的扩展通道（await 其结果），而 `session.subscribe` 是 SDK 的只读通道。`session_shutdown` 是会话关闭事件的正确名称。

## 当前 Pi 行为

- 扩展可注册：工具（`registerTool`）、命令（`registerCommand`）、Provider（`registerProvider`）、主题、提示词模板、快捷键、编辑器组件，以及生命周期事件监听（`on(...)`）。
- 事件名与 payload 类型以固定基线的 `extensions.md` 与 `src/core/extensions/types.ts` 为准，不要从旧示例复制。
- 容易混淆的修正：关闭事件是 `session_shutdown`（不是 `session_end`）；没有 `settings_change`；工具输入改写原地进行（没有 `modifiedInput` 返回值）；压缩前定制用 `session_before_compact`。

### 一个真实扩展长什么样

Pi 官方示例 `packages/coding-agent/examples/extensions/hello.ts`（原文）——一个扩展就是一个默认导出函数，接收 `ExtensionAPI`：

```typescript
// packages/coding-agent/examples/extensions/hello.ts（Pi 0.84.2，原文）
import { Type } from "@earendil-works/pi-ai";
import { defineTool, type ExtensionAPI } from "@earendil-works/pi-coding-agent";

const helloTool = defineTool({
  name: "hello",
  label: "Hello",
  description: "A simple greeting tool",
  parameters: Type.Object({
    name: Type.String({ description: "Name to greet" }),
  }),
  async execute(_toolCallId, params, _signal, _onUpdate, _ctx) {
    return {
      content: [{ type: "text", text: `Hello, ${params.name}!` }],
      details: { greeted: params.name },
    };
  },
});

export default function (pi: ExtensionAPI) {
  pi.registerTool(helloTool);
}
```

生命周期事件示例——`session_shutdown` 用于清理扩展持有的资源（官方示例 `auto-commit-on-exit.ts` 的用法）：

```typescript
// packages/coding-agent/examples/extensions/auto-commit-on-exit.ts（Pi 0.84.2，节选）
export default function (pi: ExtensionAPI) {
  pi.on("session_shutdown", async () => {
    // 会话关闭时执行：提交 git、关闭连接、清理临时文件……
  });
}
```

要点：`hello.ts` 里工具的 `execute` 签名与 [03 章](../03-tools/README.md) 的实现对照完全一致（`toolCallId, params, signal, onUpdate`）；扩展代码可以放在 `~/.pi/agent/extensions/` 或用 `pi -e 路径` 单次运行。

## 在 Pi 里怎么操作

- 安装：`pi install npm:包名` 或 `pi install git:github.com/user/repo`。
- 查看：`pi list` 列出已安装包；移除：`pi remove npm:包名`；单次运行：`pi -e npm:包名`。

### 社区扩展参考

Pi 生态已有 5500+ 个扩展/技能/主题/模板包，生态地图见 [awesome-pi](https://github.com/BubblePtr/awesome-pi)。按教学价值挑选的高 star 项目：

**建议精读的四个代表**

1. **pi-llama**（HuggingFace 官方，93★）——单文件 `index.ts` 演示 `pi.registerProvider("llama-cpp", {...})` + `pi.registerCommand(...)`，与 [07 章](../08-providers-and-models/README.md) 的 Provider 入口一致。
2. **pi-subagents**（3255★，当前最高）——一个 `subagent` 工具撑起子代理能力：Pi 核心不内置子代理，由扩展按需提供。
3. **narumiruna/pi-extensions**（390★）——27 包 monorepo，`docs/` 沉淀扩展工程约定（extension-conventions、extension-settings、readme-conventions、ADR）。
4. **pi-context-prune**（214★）——工具调用批次总结/修剪，呼应 [06 章](../07-context-and-compaction/README.md)。

**按功能分类速查**

| 分类 | 代表 | Star | 安装 |
| --- | --- | --- | --- |
| 子代理 | [pi-subagents](https://github.com/nicobailon/pi-subagents) / [@tintinweb/pi-subagents](https://github.com/tintinweb/pi-subagents) | 3255 / 943 | `pi install npm:pi-subagents` 等 |
| 记忆系统 | [pi-hermes-memory](https://github.com/chandra447/pi-hermes-memory) / [pi-memory](https://github.com/jayzeng/pi-memory) | 366 / 125 | `pi install npm:pi-hermes-memory` 等 |
| 手机连接 | [pi-telegram](https://github.com/badlogic/pi-telegram) / [pi-web](https://github.com/jmfederico/pi-web)（手机浏览器）/ [pi-ntfy](https://github.com/yevmel/pi-ntfy)（推送示例） | 281 / 593 / — | `pi install git:github.com/badlogic/pi-telegram` 等 |
| Web 访问 | [pi-web-access](https://github.com/nicobailon/pi-web-access) | 1190 | `pi install npm:pi-web-access` |
| UI 与工具 | [pi-interactive-shell](https://github.com/nicobailon/pi-interactive-shell) | 561 | `pi install npm:pi-interactive-shell` |
| 集合 | [pi-extensions](https://github.com/narumiruna/pi-extensions) / [monopi](https://github.com/ifiokjr/monopi) | 390 / 145 | `pi install npm:@narumitw/pi-extensions` 等 |
| Provider | [pi-claude-cli](https://github.com/rchern/pi-claude-cli) / [pi-model-switch](https://github.com/nicobailon/pi-model-switch) / [pi-llama](https://github.com/huggingface/pi-llama) | 98 / 93 / 93 | 见各仓库 |
| 生态入口 | [awesome-pi](https://github.com/BubblePtr/awesome-pi) | 92 | — |

> 注：国内渠道——飞书有 pi-feishu 系列（5★，官方 Bot API + WebSocket 长连接，无需公网 IP）；微信没有（无官方 Bot API，个人号自动化有封号风险）；钉钉仅雏形。star 不代表质量，安装前先读源码确认权限与网络行为。

## Python 对照

[extension_events.py](../../learn_pi_lab/labs/extension_events.py) 是课程自己的事件总线，演示按注册顺序派发、异常隔离（普通 `Exception` 变成数据，`KeyboardInterrupt`/`SystemExit` 不拦截）、幂等退订与深度快照：

```python
bus = LessonEventBus()
bus.on("turn", lambda payload: "first")       # 返回 Subscription
outcomes = bus.emit("turn", {"lesson": "events"})  # 每个 handler 一个 EventOutcome
```

它不是 Pi ExtensionAPI 的 Python 绑定——Pi 扩展是 TypeScript 代码。Tau 对照：`tau_agent/harness.py` 的 `subscribe(listener)` 返回退订函数，语义与本课程一致。

## 实现对照：Pi 源码与 Tau 双版本

事件类型两套实现完全同构——Tau 的 `events.py` 就是 Pi 事件联合的 Python 版本。

**事件定义**：

```typescript
// Pi 0.84.2: packages/agent/src/types.ts（原文节选）
export type AgentEvent =
  | { type: "agent_start" }
  | { type: "agent_end"; messages: AgentMessage[] }
  | { type: "turn_start" }
  | { type: "turn_end"; message: AgentMessage; toolResults: ToolResultMessage[] }
  | { type: "message_start"; message: AgentMessage }
  | { type: "message_update"; message: AgentMessage; assistantMessageEvent: AssistantMessageEvent }
  | { type: "message_end"; message: AgentMessage }
  | { type: "tool_execution_start"; toolCallId: string; toolName: string; args: any }
  | { type: "tool_execution_update"; toolCallId: string; toolName: string; args: any; partialResult: any }
  | { type: "tool_execution_end"; toolCallId: string; toolName: string; result: any; isError: boolean };
```

```python
# Tau: tau_agent/events.py（原文节选）
class AgentStartEvent(WireModel):
    type: Literal["agent_start"] = "agent_start"

class AgentEndEvent(WireModel):
    type: Literal["agent_end"] = "agent_end"
    messages: list[AgentMessage] = Field(default_factory=list)

class ToolExecutionEndEvent(WireModel):
    type: Literal["tool_execution_end"] = "tool_execution_end"
    tool_call_id: str
    tool_name: str
    result: AgentToolResult
    is_error: bool

type AgentEvent = Annotated[
    AgentStartEvent | AgentEndEvent | TurnStartEvent | TurnEndEvent
    | MessageStartEvent | MessageUpdateEvent | MessageEndEvent
    | ToolExecutionStartEvent | ToolExecutionUpdateEvent | ToolExecutionEndEvent,
    Field(discriminator="type"),
]
```

概念对照：TS 的对象字面量联合 → Python 的按 `type` 判别的 WireModel 联合。事件名、字段名（`toolCallId`/`tool_call_id`）完全对应。

**订阅（只读通道）**——Pi 的 `session.subscribe` 与 Tau 的 `AgentHarness.subscribe`：

```typescript
// Pi 0.84.2: packages/coding-agent/src/core/sdk.ts（概念）
session.subscribe((event) => { ... });  // 返回退订函数
```

```python
# Tau: tau_agent/harness.py（原文节选）
def subscribe(self, listener: EventListener) -> Callable[[], None]:
    """注册事件监听器；返回的 callable 退订一次。"""
    self._listeners.append(listener)

    def unsubscribe() -> None:
        with suppress(ValueError):
            self._listeners.remove(listener)

    return unsubscribe
```

设计一致：订阅返回退订函数、幂等移除。区别在语义——Pi 的 `subscribe` 是只读观察（Agent 不等），扩展的 `pi.on` 可拦截（Agent 会等），见上文“两条监听通道”。

## Python 实验

```sh
python3 -m learn_pi_lab lab events
```

## 验证方式

```sh
python3 -m unittest tests.test_07_extension_events -v
```

## 边界与安全

- 事件名、payload、返回约定以固定基线（0.84.2）的 `extensions.md` 与 ExtensionAPI 类型定义为准，不要从旧 README 复制。
- 扩展应验证所有外部输入、限制可执行操作，把异常变成明确的用户反馈或日志。
- 社区项目随 Pi 版本演进；本课程的 Python 实验不绑定、不依赖任何 Pi 扩展。
