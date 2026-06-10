# SDK 与 RPC 编程接口

> 通过 SDK 或 RPC 模式，将 Pi 集成到你的应用中。

---

## 一、集成方式概览

| 方式 | 说明 |
|------|------|
| **SDK** | TypeScript/Node.js 库，直接 import |
| **RPC** | 进程间通信，通过 stdin/stdout |
| **JSON** | 结构化事件输出 |

---

## 二、SDK 集成

### 2.1 安装

```bash
npm install @earendil-works/pi-coding-agent
```

### 2.2 基本使用

```typescript
import { 
  AuthStorage, 
  createAgentSession, 
  ModelRegistry, 
  SessionManager 
} from "@earendil-works/pi-coding-agent";

// 创建认证存储
const authStorage = AuthStorage.create();

// 创建模型注册表
const modelRegistry = ModelRegistry.create(authStorage);

// 创建会话
const { session } = await createAgentSession({
  sessionManager: SessionManager.inMemory(),
  authStorage,
  modelRegistry,
});

// 发送消息
await session.prompt("当前目录有哪些文件？");
```

### 2.3 监听事件

```typescript
session.on("message", (message) => {
  console.log("新消息:", message);
});

session.on("tool_call", (toolCall) => {
  console.log("工具调用:", toolCall);
});

session.on("tool_result", (result) => {
  console.log("工具结果:", result);
});
```

### 2.4 工具配置

```typescript
const { session } = await createAgentSession({
  sessionManager: SessionManager.inMemory(),
  authStorage,
  modelRegistry,
  tools: createCodingTools(),  // 完整工具集
  // 或
  tools: createReadOnlyTools(),  // 只读工具集
});
```

### 2.5 会话管理

```typescript
// 继续会话
await session.continue();

// 中止
session.abort();

// 获取状态
const state = session.getState();
```

---

## 三、RPC 模式

### 3.1 启动 RPC

```bash
pi --mode rpc
```

### 3.2 通信协议

RPC 使用 LF 分隔的 JSONL 帧。客户端必须只在 `\n` 上分割记录。

**请求格式：**

```json
{"type": "prompt", "message": "当前目录有哪些文件？"}
```

**响应格式：**

```json
{"type": "message", "role": "assistant", "content": "..."}
{"type": "tool_call", "id": "...", "name": "bash", "input": {...}}
{"type": "tool_result", "toolCallId": "...", "content": [...]}
```

### 3.3 客户端示例

```typescript
import { spawn } from "node:child_process";

const pi = spawn("pi", ["--mode", "rpc"]);

// 发送请求
pi.stdin.write(JSON.stringify({
  type: "prompt",
  message: "列出所有 TypeScript 文件"
}) + "\n");

// 接收响应
pi.stdout.on("data", (data) => {
  const lines = data.toString().split("\n").filter(Boolean);
  for (const line of lines) {
    const event = JSON.parse(line);
    console.log("事件:", event);
  }
});
```

### 3.4 事件类型

| 事件 | 说明 |
|------|------|
| `message` | 助手消息 |
| `tool_call` | 工具调用 |
| `tool_result` | 工具结果 |
| `error` | 错误 |
| `done` | 完成 |

---

## 四、JSON 模式

### 4.1 启动 JSON 模式

```bash
pi --mode json "列出所有 TypeScript 文件"
```

### 4.2 输出格式

每行一个 JSON 事件：

```json
{"type": "text", "text": "当前目录有以下 TypeScript 文件："}
{"type": "tool_call", "id": "...", "name": "bash", "input": {"command": "find . -name '*.ts'"}}
{"type": "tool_result", "toolCallId": "...", "content": [{"type": "text", "text": "..."}]}
{"type": "text", "text": "找到了 10 个 TypeScript 文件。"}
```

---

## 五、高级 SDK 用法

### 5.1 多会话运行时

```typescript
import { createAgentSessionRuntime, AgentSessionRuntime } from "@earendil-works/pi-coding-agent";

// 创建运行时
const runtime = await createAgentSessionRuntime({
  authStorage,
  modelRegistry,
});

// 创建多个会话
const session1 = await runtime.createSession();
const session2 = await runtime.createSession();

// 并行执行
await Promise.all([
  session1.prompt("任务 A"),
  session2.prompt("任务 B")
]);
```

### 5.2 自定义工具

```typescript
import { defineTool } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

const myTool = defineTool({
  name: "my-tool",
  description: "我的自定义工具",
  parameters: Type.Object({
    input: Type.String()
  }),
  async execute(params) {
    return { result: `处理: ${params.input}` };
  }
});

const { session } = await createAgentSession({
  tools: [...createCodingTools(), myTool],
  // ...
});
```

### 5.3 扩展集成

```typescript
const { session } = await createAgentSession({
  extensions: [myExtension],
  // ...
});
```

---

## 六、使用场景

### 6.1 CI/CD 集成

```bash
# 在 CI 中使用 Pi 进行代码审查
pi -p @code-review-prompt.md "审查这次提交"
```

### 6.2 构建工具

```typescript
// 作为构建工具的一部分
const runtime = await createAgentSessionRuntime({ ... });
const session = await runtime.createSession();
await session.prompt("生成 API 文档");
```

### 6.3 自定义界面

```typescript
// 构建自定义 Web UI
const runtime = await createAgentSessionRuntime({ ... });
const session = await runtime.createSession();

// 将事件转发到 WebSocket
session.on("message", (msg) => {
  ws.send(JSON.stringify(msg));
});
```

---

## 七、性能考虑

### 7.1 会话复用

复用会话而不是每次创建新会话，可以利用上下文缓存。

### 7.2 并行执行

SDK 支持并行执行多个会话，但注意 LLM API 限制。

### 7.3 错误处理

```typescript
try {
  await session.prompt("...");
} catch (error) {
  if (error.name === "ContextOverflow") {
    // 处理上下文溢出
    await session.compact();
    await session.prompt("...");
  }
}
```

---

## 八、小结

| 方式 | 适用场景 |
|------|----------|
| **SDK** | TypeScript/Node.js 应用集成 |
| **RPC** | 跨语言、进程间通信 |
| **JSON** | 脚本、管道处理 |

---

## 下一步

掌握了 SDK 和 RPC 后，下一章我们将介绍 [桌面端设计方案](../18-desktop-design/README.md)，探讨如何构建 Pi 的桌面应用。
