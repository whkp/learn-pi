# 扩展系统与工具链

> Pi 的扩展系统是其最强大的特性——通过 TypeScript 代码，你可以定制几乎一切。

---

## 一、扩展系统概览

Pi 的扩展系统允许你在不修改核心代码的情况下，添加新功能或修改现有行为：

| 能力 | 说明 |
|------|------|
| **自定义工具** | 注册 LLM 可调用的新工具 |
| **事件钩子** | 在 Agent 各阶段注入逻辑 |
| **自定义命令** | 注册斜杠命令 |
| **快捷键** | 绑定自定义快捷键 |
| **UI 组件** | 自定义编辑器、Footer、Header、Widget |
| **自定义 Provider** | 接入新的 LLM 提供商 |
| **自定义渲染** | 控制工具调用和消息的显示方式 |

---

## 二、扩展结构

### 2.1 基本结构

```typescript
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  // 1. 订阅事件
  pi.on("session_start", async (event, ctx) => {
    ctx.ui.notify("扩展已加载！", "info");
  });
  
  // 2. 注册工具
  pi.registerTool({
    name: "my-tool",
    description: "我的自定义工具",
    parameters: { /* JSON Schema */ },
    execute: async (toolCallId, params, signal, onUpdate, ctx) => {
      return {
        content: [{ type: "text", text: "执行结果" }]
      };
    }
  });
  
  // 3. 注册命令
  pi.registerCommand("my-cmd", {
    description: "我的命令",
    handler: async (args, ctx) => {
      ctx.ui.notify("命令执行", "info");
    }
  });
}
```

### 2.2 扩展位置

| 位置 | 作用域 |
|------|--------|
| `~/.pi/agent/extensions/*.ts` | 全局（所有项目） |
| `~/.pi/agent/extensions/*/index.ts` | 全局（子目录） |
| `.pi/extensions/*.ts` | 项目级 |
| `.pi/extensions/*/index.ts` | 项目级（子目录） |

---

## 三、事件系统

### 3.1 事件类型

Pi 提供 30+ 生命周期事件：

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

### 3.2 事件处理

```typescript
// 拦截危险命令
pi.on("tool_call", async (event, ctx) => {
  if (event.toolName === "bash") {
    const command = event.input.command;
    if (command.includes("rm -rf") || command.includes("sudo")) {
      const ok = await ctx.ui.confirm("危险操作", `允许执行: ${command}?`);
      if (!ok) {
        return { block: true, reason: "用户拒绝" };
      }
    }
  }
});

// 工具执行后记录日志
pi.on("tool_result", async (event, ctx) => {
  console.log(`工具 ${event.toolName} 执行完成`);
});
```

### 3.3 事件返回值

某些事件可以返回特殊值来影响行为：

```typescript
pi.on("tool_call", async (event, ctx) => {
  // 阻止工具执行
  return { block: true, reason: "不允许" };
  
  // 或者修改输入
  return { modifiedInput: { ...event.input, safe: true } };
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
    
    // 执行部署逻辑
    const result = await deploy(params.environment, params.version);
    
    return {
      content: [{ 
        type: "text", 
        text: `部署到 ${params.environment} 成功！版本: ${result.version}` 
      }],
      details: { deploymentId: result.id } // 持久化状态
    };
  }
});
```

### 4.2 工具最佳实践

1. **清晰的描述**：让 LLM 理解何时使用这个工具
2. **合理的参数**：使用 JSON Schema 定义参数
3. **进度反馈**：使用 `onUpdate` 显示执行进度
4. **错误处理**：捕获异常并返回有意义的错误信息
5. **状态持久化**：使用 `details` 保存状态，支持会话分支

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
// 在编辑器上方显示内容
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
const ok = await ctx.ui.confirm("确认删除", "确定要删除这个文件吗？");

// 输入对话框
const input = await ctx.ui.input("输入版本号", "1.0.0");
```

---

## 六、命令注册

```typescript
pi.registerCommand("deploy", {
  description: "部署应用",
  handler: async (args, ctx) => {
    // args 是用户输入的参数
    const environment = args || "staging";
    ctx.ui.notify(`开始部署到 ${environment}`, "info");
  }
});
```

使用方式：在编辑器中输入 `/deploy production`

---

## 七、快捷键

```typescript
pi.registerShortcut("ctrl+d", {
  description: "快速部署",
  handler: async (ctx) => {
    // 快捷键处理逻辑
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
    // 实现流式调用
    const response = await fetch("https://my-api.com/chat", {
      method: "POST",
      body: JSON.stringify(request)
    });
    return transformToStream(response);
  }
});
```

---

## 九、异步扩展

如果扩展需要异步初始化（如获取远程配置），使用 async 工厂函数：

```typescript
export default async function (pi: ExtensionAPI) {
  // 异步初始化
  const config = await fetchConfig();
  
  // 注册工具
  pi.registerTool({
    name: "my-tool",
    // ...
  });
}
```

Pi 会等待异步初始化完成后再继续启动。

---

## 十、小结

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

掌握了扩展系统后，下一章我们将介绍 [安装与快速上手](../06-install-and-quickstart/README.md)，开始实际使用 Pi。
