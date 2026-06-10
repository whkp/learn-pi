# Extensions 扩展开发

> 通过 TypeScript 扩展，你可以定制 Pi 的一切——从工具、UI 到整个工作流。

---

## 一、扩展概览

### 1.1 扩展能力

| 能力 | 说明 |
|------|------|
| **自定义工具** | 注册 LLM 可调用的新工具 |
| **事件钩子** | 在 Agent 各阶段注入逻辑 |
| **自定义命令** | 注册斜杠命令 |
| **快捷键** | 绑定自定义快捷键 |
| **UI 组件** | 自定义编辑器、Footer、Header、Widget |
| **自定义 Provider** | 接入新的 LLM 提供商 |
| **自定义渲染** | 控制工具调用和消息的显示方式 |

### 1.2 扩展位置

| 位置 | 作用域 |
|------|--------|
| `~/.pi/agent/extensions/*.ts` | 全局 |
| `~/.pi/agent/extensions/*/index.ts` | 全局（子目录） |
| `.pi/extensions/*.ts` | 项目级 |
| `.pi/extensions/*/index.ts` | 项目级（子目录） |

### 1.3 测试扩展

```bash
pi -e ./my-extension.ts
```

---

## 二、扩展结构

### 2.1 基本模板

```typescript
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

export default function (pi: ExtensionAPI) {
  // 订阅事件
  pi.on("session_start", async (event, ctx) => {
    ctx.ui.notify("扩展已加载！", "info");
  });
  
  // 注册工具
  pi.registerTool({
    name: "my-tool",
    label: "My Tool",
    description: "我的自定义工具",
    parameters: Type.Object({
      input: Type.String({ description: "输入参数" })
    }),
    async execute(toolCallId, params, signal, onUpdate, ctx) {
      return {
        content: [{ type: "text", text: `处理: ${params.input}` }],
        details: {}  // 持久化状态
      };
    }
  });
  
  // 注册命令
  pi.registerCommand("my-cmd", {
    description: "我的命令",
    handler: async (args, ctx) => {
      ctx.ui.notify(`执行: ${args}`, "info");
    }
  });
}
```

### 2.2 异步扩展

如果需要异步初始化（如获取远程配置）：

```typescript
export default async function (pi: ExtensionAPI) {
  const config = await fetchConfig();
  
  pi.registerTool({ ... });
}
```

Pi 会等待异步初始化完成后再继续启动。

---

## 三、事件系统

### 3.1 事件类型

| 事件 | 触发时机 |
|------|----------|
| `session_start` | 会话开始 |
| `session_end` | 会话结束 |
| `tool_call` | 工具调用前 |
| `tool_result` | 工具执行后 |
| `message_start` | 消息开始 |
| `message_end` | 消息结束 |
| `turn_end` | 回合结束 |
| `model_select` | 模型切换 |
| `settings_change` | 设置变更 |

### 3.2 拦截工具调用

```typescript
pi.on("tool_call", async (event, ctx) => {
  // 阻止危险命令
  if (event.toolName === "bash") {
    const command = event.input.command;
    if (command.includes("rm -rf")) {
      const ok = await ctx.ui.confirm("危险操作", `允许执行: ${command}?`);
      if (!ok) {
        return { block: true, reason: "用户拒绝" };
      }
    }
  }
});
```

### 3.3 修改工具输入

```typescript
pi.on("tool_call", async (event, ctx) => {
  if (event.toolName === "bash") {
    // 添加安全前缀
    return {
      modifiedInput: {
        ...event.input,
        command: `set -e && ${event.input.command}`
      }
    };
  }
});
```

---

## 四、自定义工具

### 4.1 工具定义

```typescript
import { Type } from "typebox";

pi.registerTool({
  name: "deploy",
  label: "部署",
  description: "部署应用到指定环境",
  parameters: Type.Object({
    environment: Type.String({ 
      description: "目标环境 (staging/production)" 
    }),
    version: Type.Optional(Type.String({ 
      description: "版本号（可选）" 
    }))
  }),
  async execute(toolCallId, params, signal, onUpdate, ctx) {
    // 显示进度
    onUpdate({ status: "running", message: "正在部署..." });
    
    // 执行部署
    const result = await deploy(params.environment, params.version);
    
    return {
      content: [{ 
        type: "text", 
        text: `部署到 ${params.environment} 成功！版本: ${result.version}` 
      }],
      details: { deploymentId: result.id }
    };
  }
});
```

### 4.2 工具最佳实践

1. **清晰的描述**：让 LLM 理解何时使用
2. **合理的参数**：使用 JSON Schema 定义
3. **进度反馈**：使用 `onUpdate` 显示进度
4. **错误处理**：捕获异常并返回有意义的错误
5. **状态持久化**：使用 `details` 保存状态

---

## 五、UI 扩展

### 5.1 通知

```typescript
ctx.ui.notify("操作完成", "info");     // 信息
ctx.ui.notify("操作失败", "error");    // 错误
ctx.ui.notify("请检查", "warning");    // 警告
```

### 5.2 状态栏

```typescript
ctx.ui.setStatus("my-ext", "处理中...");  // 设置状态
ctx.ui.setStatus("my-ext", null);         // 清除状态
```

### 5.3 Widget

```typescript
ctx.ui.setWidget("my-ext", [
  "当前分支: main",
  "未提交更改: 3"
]);
```

### 5.4 自定义对话框

```typescript
// 选择列表
const choice = await ctx.ui.select("选择环境", [
  { label: "Staging", value: "staging" },
  { label: "Production", value: "production" }
]);

// 确认对话框
const ok = await ctx.ui.confirm("确认删除", "确定要删除吗？");

// 输入对话框
const input = await ctx.ui.input("输入版本号", "1.0.0");
```

### 5.5 自定义编辑器

```typescript
// 替换编辑器
ctx.ui.setEditorComponent(myCustomEditor);

// 设置编辑器文本
ctx.ui.setEditorText("新的内容");

// 设置 Widget 位置
ctx.ui.setWidget("my-ext", lines, "above");  // 或 "below"
```

### 5.6 Footer 和 Header

```typescript
// 自定义 Footer
ctx.ui.setFooter([
  "分支: main",
  "Token: 1234"
]);

// 自定义 Header
ctx.ui.setHeader([
  "Pi 编码智能体"
]);

// 清除
ctx.ui.setFooter(null);
ctx.ui.setHeader(null);
```

---

## 六、命令注册

```typescript
pi.registerCommand("deploy", {
  description: "部署应用",
  handler: async (args, ctx) => {
    const environment = args || "staging";
    ctx.ui.notify(`开始部署到 ${environment}`, "info");
  }
});
```

使用：在编辑器中输入 `/deploy production`

---

## 七、快捷键

```typescript
pi.registerShortcut("ctrl+d", {
  description: "快速部署",
  handler: async (ctx) => {
    // 快捷键处理
  }
});
```

---

## 八、自定义 Provider

```typescript
pi.registerProvider("my-provider", {
  name: "My Provider",
  models: [
    { id: "my-model-1", name: "My Model 1" },
    { id: "my-model-2", name: "My Model 2" }
  ],
  stream: async (request) => {
    const response = await fetch("https://my-api.com/chat", {
      method: "POST",
      body: JSON.stringify(request)
    });
    return transformToStream(response);
  }
});
```

---

## 九、可用导入

| 包 | 用途 |
|----|------|
| `@earendil-works/pi-coding-agent` | 扩展类型、事件 |
| `typebox` | 参数 Schema 定义 |
| `@earendil-works/pi-ai` | AI 工具函数 |
| `@earendil-works/pi-tui` | TUI 组件 |

Node.js 内置模块（`node:fs`、`node:path` 等）也可使用。

---

## 十、示例扩展

Pi 提供了丰富的示例扩展：

| 扩展 | 说明 |
|------|------|
| `permission-gate.ts` | 危险命令确认 |
| `protected-paths.ts` | 保护路径写入 |
| `todo.ts` | 待办列表工具 |
| `git-checkpoint.ts` | Git 检查点 |
| `plan-mode/` | 计划模式 |
| `snake.ts` | 贪吃蛇游戏 |
| `doom-overlay/` | Doom 游戏叠加层 |

详见 [examples/extensions/](https://github.com/earendil-works/pi-mono/tree/main/examples/extensions)。

---

## 十一、小结

| 扩展能力 | 说明 |
|----------|------|
| **事件系统** | 30+ 生命周期事件 |
| **自定义工具** | 注册 LLM 可调用的工具 |
| **UI 扩展** | 通知、状态栏、Widget、对话框 |
| **命令** | 注册斜杠命令 |
| **快捷键** | 绑定自定义快捷键 |
| **Provider** | 接入新的 LLM 提供商 |

---

## 下一步

掌握了扩展开发后，下一章我们将介绍 [Prompt Templates 提示词模板](../12-prompt-templates/README.md)，学习如何创建可复用的提示词。
