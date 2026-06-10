# 架构深入解析

> 理解 Pi 的分层架构，是掌握其扩展能力和定制能力的基础。

---

## 一、Monorepo 整体结构

Pi 采用 npm workspaces 的 Monorepo 结构，包含 5 个核心包：

```
pi/
├── packages/
│   ├── ai/              # @earendil-works/pi-ai
│   ├── agent/           # @earendil-works/pi-agent-core
│   ├── coding-agent/    # @earendil-works/pi-coding-agent
│   ├── tui/             # @earendil-works/pi-tui
│   └── web-ui/          # @earendil-works/pi-web-ui
├── scripts/
├── .pi/                 # 默认配置
└── package.json
```

---

## 二、依赖关系图

```
┌─────────────────────────────────────────────────────────────┐
│                    前端展示层                                 │
│  ┌──────────┐                    ┌──────────┐               │
│  │   tui    │                    │  web-ui  │               │
│  │ (终端UI) │                    │ (Web UI) │               │
│  └────┬─────┘                    └────┬─────┘               │
│       │                               │                     │
├───────┼───────────────────────────────┼─────────────────────┤
│       │         核心层                 │                     │
│  ┌────▼─────┐                    ┌────▼─────┐               │
│  │    ai    │◄───────────────────│  agent   │               │
│  │ (LLM API)│                   │(运行时核心)│               │
│  └──────────┘                    └────┬─────┘               │
│                                       │                     │
├───────────────────────────────────────┼─────────────────────┤
│         应用层                         │                     │
│  ┌────────────────────────────────────▼─────┐               │
│  │           coding-agent                   │               │
│  │        (交互式编码智能体)                  │               │
│  └──────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

依赖方向：**ai ← agent ← coding-agent**

---

## 三、各包职责

### 3.1 @earendil-works/pi-ai（LLM API 层）

**职责**：统一的多供应商 LLM API，屏蔽不同提供商的差异。

```typescript
// 统一的流式接口
const stream = await api.stream({
  model: "claude-sonnet-4-20250514",
  messages: [...],
  tools: [...]
});

for await (const event of stream) {
  // text, tool_call, thinking, usage, stop, error
}
```

**核心设计**：
- 每个 Provider 是独立模块（`providers/anthropic.ts`、`providers/openai-responses.ts` 等）
- 懒加载策略：Provider 在首次使用时才动态 import
- 统一事件流：`AssistantMessageEventStream`

**支持的 Provider**：

| Provider | API 类型 |
|----------|----------|
| Anthropic | `anthropic-messages` |
| OpenAI | `openai-completions`、`openai-responses` |
| Google | `google-generative-ai`、`google-vertex` |
| Mistral | `mistral-conversations` |
| AWS Bedrock | `bedrock-converse-stream` |

### 3.2 @earendil-works/pi-agent-core（运行时核心）

**职责**：定义 Agent 的基本生命周期和工具执行框架。

```
Agent
├── 状态管理（messages、tools、systemPrompt、model）
├── 生命周期事件（subscribe/emit）
├── 消息队列（steeringQueue / followUpQueue）
├── prompt() — 启动新对话
├── continue() — 继续当前对话
└── abort() — 中断运行
```

**核心机制**：
- **Agent Loop**：LLM 推理 → 工具调用 → 结果收集 → 继续推理
- **生命周期事件**：message_start、tool_execution_start/end、turn_end 等
- **消息队列**：支持 steer（植入消息）和 followUp（后续消息）
- **并行工具执行**：多个独立工具调用可并行执行

### 3.3 @earendil-works/pi-coding-agent（编码智能体）

**职责**：面向最终用户的交互式编程智能体 CLI。

**核心功能**：
- 交互式终端界面（TUI）
- RPC 模式（进程集成）
- Print 模式（批量非交互）
- 会话管理（创建、切换、分支、标签）

**核心工具集**：
```typescript
// core/tools/
read    // 读取文件
write   // 写入文件
edit    // 精确编辑
bash    // 执行命令
grep    // 搜索内容
find    // 查找文件
ls      // 列出目录
```

### 3.4 @earendil-works/pi-tui（终端 UI）

**职责**：终端 UI 库，采用差异化渲染实现高性能。

**组件**：
- 文本编辑器（语法高亮、撤销/重做、自动补全）
- 选择列表、设置列表、弹窗、对话框
- Markdown 渲染与代码高亮
- 图片渲染

### 3.5 @earendil-works/pi-web-ui（Web UI）

**职责**：AI 聊天界面的 Web 组件库。

提供 `ChatPanel` 组件，支持：
- 消息显示与输入
- 工具调用可视化
- 会话管理
- 主题定制

---

## 四、数据流

### 4.1 核心 Agent Loop

```
用户输入
  │
  ▼
Agent.prompt() / Agent.continue()
  │
  ▼
┌─────────────────────────────────────┐
│         Agent Loop                  │
│  ┌──────────────────────────────┐   │
│  │ 1. 构建消息列表               │   │
│  │ 2. 调用 LLM Provider         │   │
│  │ 3. 解析工具调用               │   │
│  │ 4. 执行工具                  │   │
│  │ 5. 收集工具结果               │   │
│  │ 6. 继续循环（传递结果给 LLM） │   │
│  └──────────────────────────────┘   │
│          直到任务完成                │
└─────────────────────────────────────┘
  │
  ▼
最终回复 → UI 渲染
```

### 4.2 交互式 CLI 数据流

```
AgentSessionRuntime
  │
  ├── AgentHarness（管理 Session、压缩、技能）
  │     │
  │     └── Agent（核心循环）
  │           │
  │           ├── LLM Provider（packages/ai）
  │           │     └── stream() 返回事件流
  │           │
  │           └── Tools（read/write/edit/bash 等）
  │
  └── 事件回调 → UI 渲染（packages/tui）
```

---

## 五、核心设计模式

### 5.1 事件驱动

Pi 大量使用事件驱动模式：

```typescript
// 生命周期事件
pi.on("session_start", async (event, ctx) => { ... });
pi.on("tool_call", async (event, ctx) => { ... });
pi.on("message_end", async (event, ctx) => { ... });

// 30+ 事件类型覆盖完整链路
```

### 5.2 插件化架构

扩展通过注册机制注入功能：

```typescript
pi.registerTool({ ... });      // 自定义工具
pi.registerCommand("name", {}); // 自定义命令
pi.registerShortcut("ctrl+x", {}); // 快捷键
pi.registerProvider("name", {}); // 自定义 Provider
```

### 5.3 渐进式加载

- **技能**：只加载描述，按需加载完整指令
- **扩展**：自动发现，按需启用
- **Provider**：懒加载，首次使用时才 import

### 5.4 树形会话结构

会话采用 JSONL + 树形结构：

```json
[
  { "id": "a", "parentId": null, "type": "user", "message": "..." },
  { "id": "b", "parentId": "a", "type": "assistant", "message": "..." },
  { "id": "c", "parentId": "b", "type": "user", "message": "..." },
  { "id": "d", "parentId": "c", "type": "assistant", "message": "..." }
]
```

支持在任意点分叉，探索不同方案。

---

## 六、关键抽象

### 6.1 ExtensionAPI

扩展的入口点，提供注册和事件订阅能力：

```typescript
interface ExtensionAPI {
  on(event: string, handler: Function): void;
  registerTool(tool: ToolDefinition): void;
  registerCommand(name: string, command: CommandDefinition): void;
  registerShortcut(key: string, handler: Function): void;
  registerProvider(name: string, provider: ProviderDefinition): void;
}
```

### 6.2 ExtensionContext

扩展执行时的上下文：

```typescript
interface ExtensionContext {
  ui: UI;                    // 用户交互
  sessionManager: Session;   // 会话管理
  signal: AbortSignal;       // 中断信号
}
```

### 6.3 ToolDefinition

工具定义：

```typescript
interface ToolDefinition {
  name: string;
  description: string;
  parameters: JSONSchema;
  execute(toolCallId, params, signal, onUpdate, ctx): Promise<ToolResult>;
}
```

---

## 七、构建与开发

```bash
npm install              # 安装所有依赖
npm run build            # 构建所有包
npm run dev              # 并行监视模式
npm run check            # 代码检查 + 类型检查
```

**构建顺序**：tui → ai → agent → coding-agent → web-ui

---

## 八、小结

| 架构要点 | 说明 |
|----------|------|
| **Monorepo** | npm workspaces，5 个核心包 |
| **分层设计** | ai → agent → coding-agent |
| **事件驱动** | 30+ 生命周期事件 |
| **插件化** | 工具、命令、UI、Provider 全可扩展 |
| **树形会话** | 支持分支和回退 |

---

## 下一步

了解了整体架构后，下一章我们将深入 [核心模块源码](../04-core-modules/README.md)，解读各模块的实现细节。
