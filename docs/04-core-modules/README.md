# 核心模块源码解读

> 深入 Pi 的源码，理解各模块的实现细节。

---

## 一、源码入口

Pi 的源码托管在 [earendil-works/pi-mono](https://github.com/earendil-works/pi-mono)。核心代码位于 `packages/` 目录下。

---

## 二、@earendil-works/pi-ai（LLM API 层）

### 2.1 Provider 注册机制

```typescript
// packages/ai/src/providers/anthropic.ts
export function createAnthropicProvider(config: AnthropicConfig): Provider {
  return {
    type: "anthropic-messages",
    stream: async (request) => {
      // 调用 Anthropic Messages API
      const response = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {
          "x-api-key": config.apiKey,
          "anthropic-version": "2023-06-01",
          "content-type": "application/json"
        },
        body: JSON.stringify({
          model: request.model,
          messages: request.messages,
          tools: request.tools,
          stream: true
        })
      });
      
      // 返回统一事件流
      return transformToAssistantMessageStream(response);
    }
  };
}
```

### 2.2 统一事件流

```typescript
// packages/ai/src/stream.ts
type AssistantMessageEvent = 
  | { type: "text"; text: string }
  | { type: "tool_call"; id: string; name: string; parameters: any }
  | { type: "thinking"; thinking: string }
  | { type: "usage"; inputTokens: number; outputTokens: number }
  | { type: "stop"; stopReason: string }
  | { type: "error"; error: Error };
```

所有 Provider 的输出都被转换为这个统一格式。

### 2.3 懒加载策略

```typescript
// packages/ai/src/registry.ts
const providerModules = new Map<string, () => Promise<Provider>>();

export function registerProvider(name: string, loader: () => Promise<Provider>) {
  providerModules.set(name, loader);
}

export async function getProvider(name: string): Promise<Provider> {
  if (!providerModules.has(name)) {
    throw new Error(`Unknown provider: ${name}`);
  }
  const loader = providerModules.get(name)!;
  return loader(); // 首次使用时才加载
}
```

---

## 三、@earendil-works/pi-agent-core（运行时核心）

### 3.1 Agent 类

```typescript
// packages/agent/src/agent.ts
export class Agent {
  private messages: Message[] = [];
  private tools: Tool[] = [];
  private model: Model;
  private provider: Provider;
  
  // 启动新对话
  async prompt(userMessage: string): Promise<void> {
    this.messages.push({ role: "user", content: userMessage });
    await this.runLoop();
  }
  
  // 继续当前对话
  async continue(): Promise<void> {
    await this.runLoop();
  }
  
  // 核心循环
  private async runLoop(): Promise<void> {
    while (true) {
      // 1. 调用 LLM
      const stream = await this.provider.stream({
        model: this.model,
        messages: this.messages,
        tools: this.tools
      });
      
      // 2. 收集响应
      const response = await collectStream(stream);
      
      // 3. 如果没有工具调用，结束循环
      if (!response.toolCalls.length) {
        this.emit("turn_end", { response });
        break;
      }
      
      // 4. 执行工具
      const toolResults = await this.executeTools(response.toolCalls);
      
      // 5. 添加工具结果到消息
      this.messages.push(...toolResults);
    }
  }
}
```

### 3.2 工具执行

```typescript
// packages/agent/src/tools.ts
export interface Tool {
  name: string;
  description: string;
  parameters: JSONSchema;
  execute(toolCallId: string, params: any, signal: AbortSignal): Promise<ToolResult>;
}

export interface ToolResult {
  content: Array<{ type: "text"; text: string }>;
  details?: Record<string, any>;
}
```

### 3.3 生命周期事件

```typescript
// packages/agent/src/events.ts
type AgentEvent =
  | "message_start"      // 消息开始
  | "message_update"     // 消息更新
  | "message_end"        // 消息结束
  | "tool_execution_start" // 工具执行开始
  | "tool_execution_end"   // 工具执行结束
  | "turn_end"           // 回合结束
  | "agent_end";         // Agent 结束
```

---

## 四、@earendil-works/pi-coding-agent（编码智能体）

### 4.1 CLI 入口

```typescript
// packages/coding-agent/src/cli/cli.ts
export async function main() {
  const args = parseArgs(process.argv);
  
  // 1. 加载设置
  const settings = await loadSettings(args);
  
  // 2. 加载扩展
  const extensions = await loadExtensions(settings);
  
  // 3. 创建 Agent 会话
  const session = await createAgentSession({
    model: settings.model,
    provider: settings.provider,
    tools: createCodingTools(),
    extensions
  });
  
  // 4. 根据模式运行
  if (args.print) {
    await runPrintMode(session, args);
  } else if (args.mode === "rpc") {
    await runRpcMode(session);
  } else {
    await runInteractiveMode(session);
  }
}
```

### 4.2 工具集创建

```typescript
// packages/coding-agent/src/core/tools/index.ts
export function createCodingTools(): Tool[] {
  return [
    createReadTool(),
    createWriteTool(),
    createEditTool(),
    createBashTool(),
    createGrepTool(),
    createFindTool(),
    createLsTool()
  ];
}

export function createReadOnlyTools(): Tool[] {
  return [
    createReadTool(),
    createGrepTool(),
    createFindTool(),
    createLsTool()
  ];
}
```

### 4.3 Session 管理

```typescript
// packages/coding-agent/src/core/session-manager.ts
export class SessionManager {
  private entries: SessionEntry[] = [];
  private activePath: string[] = []; // 当前活跃路径
  
  // 添加条目
  appendEntry(entry: SessionEntry): void {
    this.entries.push(entry);
    this.activePath.push(entry.id);
    this.persist();
  }
  
  // 切换分支
  switchToBranch(entryId: string): void {
    const path = this.findPathToEntry(entryId);
    this.activePath = path;
  }
  
  // 获取当前分支
  getBranch(): SessionEntry[] {
    return this.activePath
      .map(id => this.entries.find(e => e.id === id))
      .filter(Boolean) as SessionEntry[];
  }
}
```

---

## 五、@earendil-works/pi-tui（终端 UI）

### 5.1 差异化渲染

```typescript
// packages/tui/src/renderer.ts
export class Renderer {
  private previousState: ScreenBuffer | null = null;
  
  render(state: ScreenBuffer): void {
    if (!this.previousState) {
      // 首次渲染：全量输出
      this.fullRender(state);
    } else {
      // 后续渲染：只更新变化部分
      this.differentialRender(this.previousState, state);
    }
    this.previousState = state;
  }
  
  private differentialRender(old: ScreenBuffer, new_: ScreenBuffer): void {
    // 比较两个状态，只输出差异
    for (let y = 0; y < new_.height; y++) {
      for (let x = 0; x < new_.width; x++) {
        if (old.get(x, y) !== new_.get(x, y)) {
          this.moveCursor(x, y);
          this.write(new_.get(x, y));
        }
      }
    }
  }
}
```

### 5.2 编辑器组件

```typescript
// packages/tui/src/editor.ts
export class Editor {
  private buffer: string[] = [];
  private cursor: Position = { x: 0, y: 0 };
  private history: string[][] = [];
  
  // 插入文本
  insert(text: string): void {
    // 处理换行、特殊字符
    // 更新光标位置
    // 保存历史
  }
  
  // 撤销
  undo(): void {
    if (this.history.length > 0) {
      this.buffer = this.history.pop()!;
    }
  }
  
  // 自动补全
  autocomplete(pattern: string): string[] {
    // 模糊搜索文件、命令等
  }
}
```

---

## 六、扩展系统实现

### 6.1 扩展加载

```typescript
// packages/coding-agent/src/core/extensions/loader.ts
export async function loadExtensions(settings: Settings): Promise<Extension[]> {
  const extensions: Extension[] = [];
  
  // 1. 全局扩展
  const globalDir = path.join(os.homedir(), ".pi/agent/extensions");
  if (fs.existsSync(globalDir)) {
    extensions.push(...await loadFromDir(globalDir));
  }
  
  // 2. 项目扩展
  const projectDir = ".pi/extensions";
  if (fs.existsSync(projectDir)) {
    extensions.push(...await loadFromDir(projectDir));
  }
  
  // 3. 通过 -e 参数加载
  for (const source of settings.cliExtensions) {
    extensions.push(await loadFromSource(source));
  }
  
  return extensions;
}

async function loadFromDir(dir: string): Promise<Extension[]> {
  const files = fs.readdirSync(dir).filter(f => f.endsWith(".ts"));
  const extensions: Extension[] = [];
  
  for (const file of files) {
    // 使用 jiti 动态加载 TypeScript
    const module = await jiti(path.join(dir, file));
    if (module.default) {
      extensions.push(module.default);
    }
  }
  
  return extensions;
}
```

### 6.2 扩展 API 注入

```typescript
// packages/coding-agent/src/core/extensions/api.ts
export function createExtensionAPI(agent: Agent, ctx: ExtensionContext): ExtensionAPI {
  return {
    on(event, handler) {
      agent.on(event, handler);
    },
    
    registerTool(tool) {
      agent.addTool(tool);
    },
    
    registerCommand(name, command) {
      ctx.registerCommand(name, command);
    },
    
    registerShortcut(key, handler) {
      ctx.registerShortcut(key, handler);
    },
    
    registerProvider(name, provider) {
      ctx.registerProvider(name, provider);
    }
  };
}
```

---

## 七、关键数据结构

### 7.1 消息格式

```typescript
interface Message {
  role: "user" | "assistant" | "tool";
  content: string | ContentBlock[];
  toolCallId?: string;
  toolName?: string;
}

interface ContentBlock {
  type: "text" | "tool_use" | "tool_result" | "thinking";
  text?: string;
  id?: string;
  name?: string;
  input?: any;
  content?: string;
}
```

### 7.2 工具调用格式

```typescript
interface ToolCall {
  id: string;
  name: string;
  input: Record<string, any>;
}

interface ToolResult {
  toolCallId: string;
  content: Array<{ type: "text"; text: string }>;
  details?: Record<string, any>;
}
```

---

## 八、小结

| 模块 | 核心实现 |
|------|----------|
| **pi-ai** | Provider 注册、统一事件流、懒加载 |
| **pi-agent-core** | Agent 类、Agent Loop、工具执行、事件系统 |
| **pi-coding-agent** | CLI 入口、会话管理、扩展加载 |
| **pi-tui** | 差异化渲染、编辑器组件 |

---

## 下一步

了解了核心模块后，下一章我们将深入 [扩展系统](../05-extension-system/README.md)，学习如何定制 Pi 的行为。
