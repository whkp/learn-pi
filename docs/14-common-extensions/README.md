# 常用扩展实战

> 通过实际案例，学习如何实现联网搜索、计划模式、权限控制等实用功能。

---

## 一、联网搜索

### 1.1 使用 brave-search 技能

Pi 官方提供了网页搜索技能：

```bash
pi install npm:pi-skills
```

安装后，Agent 可以自动使用搜索功能。

### 1.2 手动使用

```
/skill:brave-search 搜索关键词
```

### 1.3 自定义搜索扩展

```typescript
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "web-search",
    label: "网页搜索",
    description: "搜索网页获取信息",
    parameters: Type.Object({
      query: Type.String({ description: "搜索关键词" }),
      numResults: Type.Optional(Type.Number({ description: "结果数量" }))
    }),
    async execute(toolCallId, params, signal, onUpdate, ctx) {
      onUpdate({ status: "running", message: `搜索: ${params.query}` });
      
      // 调用搜索 API
      const results = await searchWeb(params.query, params.numResults || 5);
      
      return {
        content: [{ 
          type: "text", 
          text: results.map(r => `[${r.title}](${r.url})\n${r.snippet}`).join("\n\n")
        }]
      };
    }
  });
}
```

---

## 二、计划模式

### 2.1 什么是计划模式？

计划模式让 Agent 在只读模式下探索代码库，制定实施计划，然后再执行。

### 2.2 官方实现

Pi 提供了 `plan-mode` 扩�示例：

```bash
pi -e examples/extensions/plan-mode/
```

### 2.3 使用方式

```bash
/plan 重构认证模块
```

Agent 会：
1. 分析现有代码
2. 制定实施计划
3. 显示计划供确认
4. 确认后执行

### 2.4 自定义计划模式

```typescript
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

export default function (pi: ExtensionAPI) {
  let planMode = false;
  
  // 注册 /plan 命令
  pi.registerCommand("plan", {
    description: "进入计划模式",
    handler: async (args, ctx) => {
      planMode = true;
      ctx.ui.notify("已进入计划模式（只读）", "info");
      
      // 切换到只读工具
      // 实际实现需要更复杂的工具切换逻辑
    }
  });
  
  // 拦截写操作
  pi.on("tool_call", async (event, ctx) => {
    if (planMode && ["write", "edit", "bash"].includes(event.toolName)) {
      return { block: true, reason: "计划模式下不允许写操作" };
    }
  });
  
  // 退出计划模式
  pi.registerCommand("execute", {
    description: "执行计划",
    handler: async (args, ctx) => {
      planMode = false;
      ctx.ui.notify("已退出计划模式", "info");
    }
  });
}
```

---

## 三、权限控制

### 3.1 危险命令确认

```typescript
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  const DANGEROUS_PATTERNS = [
    /rm\s+-rf/,
    /sudo/,
    /chmod\s+777/,
    /curl.*\|\s*sh/,
    /wget.*\|\s*sh/
  ];
  
  pi.on("tool_call", async (event, ctx) => {
    if (event.toolName === "bash") {
      const command = event.input.command;
      
      for (const pattern of DANGEROUS_PATTERNS) {
        if (pattern.test(command)) {
          const ok = await ctx.ui.confirm(
            "危险操作",
            `检测到危险命令:\n${command}\n\n确定要执行吗？`
          );
          
          if (!ok) {
            return { block: true, reason: "用户拒绝危险操作" };
          }
        }
      }
    }
  });
}
```

### 3.2 路径保护

```typescript
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import * as path from "node:path";

export default function (pi: ExtensionAPI) {
  const PROTECTED_PATHS = [
    ".env",
    ".env.local",
    "node_modules",
    ".git",
    "*.key",
    "*.pem"
  ];
  
  pi.on("tool_call", async (event, ctx) => {
    if (["write", "edit"].includes(event.toolName)) {
      const filePath = event.input.path;
      const fileName = path.basename(filePath);
      
      // 检查文件名
      for (const pattern of PROTECTED_PATHS) {
        if (fileName === pattern || fileName.match(pattern.replace("*", ".*"))) {
          return { block: true, reason: `保护路径: ${fileName}` };
        }
      }
      
      // 检查路径
      if (filePath.includes("node_modules") || filePath.includes(".git")) {
        return { block: true, reason: `保护路径: ${filePath}` };
      }
    }
  });
}
```

---

## 四、Git 集成

### 4.1 Git 检查点

```typescript
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { execSync } from "node:child_process";

export default function (pi: ExtensionAPI) {
  // 每次回合结束时创建检查点
  pi.on("turn_end", async (event, ctx) => {
    try {
      // 暂存当前更改
      execSync("git stash push -m 'pi-checkpoint'", { stdio: "ignore" });
      
      // 记录检查点
      ctx.ui.setStatus("git", "已创建检查点");
    } catch (e) {
      // 忽略错误（可能没有更改）
    }
  });
  
  // 恢复检查点
  pi.registerCommand("restore", {
    description: "恢复到上一个检查点",
    handler: async (args, ctx) => {
      try {
        execSync("git stash pop", { stdio: "ignore" });
        ctx.ui.notify("已恢复检查点", "info");
      } catch (e) {
        ctx.ui.notify("恢复失败", "error");
      }
    }
  });
}
```

### 4.2 自动提交

```typescript
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { execSync } from "node:child_process";

export default function (pi: ExtensionAPI) {
  // 退出时自动提交
  pi.on("session_end", async (event, ctx) => {
    try {
      // 检查是否有更改
      const status = execSync("git status --porcelain", { encoding: "utf-8" });
      
      if (status.trim()) {
        // 获取最后一条助手消息作为提交信息
        const lastMessage = event.messages
          .filter(m => m.role === "assistant")
          .pop()?.content || "Pi 自动提交";
        
        execSync("git add -A", { stdio: "ignore" });
        execSync(`git commit -m "${lastMessage.substring(0, 50)}"`, { stdio: "ignore" });
        
        ctx.ui.notify("已自动提交", "info");
      }
    } catch (e) {
      // 忽略错误
    }
  });
}
```

---

## 五、代码质量

### 5.1 代码审查

```typescript
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "review-code",
    label: "代码审查",
    description: "审查代码质量和潜在问题",
    parameters: Type.Object({
      file: Type.String({ description: "要审查的文件" })
    }),
    async execute(toolCallId, params, signal, onUpdate, ctx) {
      onUpdate({ status: "running", message: `审查: ${params.file}` });
      
      // 读取文件
      const content = await readFile(params.file);
      
      // 分析代码
      const issues = analyzeCode(content);
      
      return {
        content: [{ 
          type: "text", 
          text: formatIssues(issues)
        }]
      };
    }
  });
}
```

---

## 六、工作流自动化

### 6.1 提交前检查

```typescript
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { execSync } from "node:child_process";

export default function (pi: ExtensionAPI) {
  // 拦截 bash 命令
  pi.on("tool_call", async (event, ctx) => {
    if (event.toolName === "bash") {
      const command = event.input.command;
      
      // 检测 git commit
      if (command.includes("git commit")) {
        // 运行检查
        const checks = [
          { name: "Lint", cmd: "npm run lint" },
          { name: "Test", cmd: "npm test" },
          { name: "Type Check", cmd: "npm run typecheck" }
        ];
        
        for (const check of checks) {
          try {
            execSync(check.cmd, { stdio: "ignore" });
          } catch (e) {
            return { 
              block: true, 
              reason: `${check.name} 失败，请先修复` 
            };
          }
        }
      }
    }
  });
}
```

---

## 七、小结

| 实战案例 | 说明 |
|----------|------|
| **联网搜索** | brave-search 技能或自定义工具 |
| **计划模式** | 只读探索 + 执行计划 |
| **权限控制** | 危险命令确认、路径保护 |
| **Git 集成** | 检查点、自动提交 |
| **代码质量** | 代码审查、提交前检查 |
| **工作流自动化** | 自动化常见任务 |

---

## 下一步

掌握了常用扩展后，下一章我们将介绍 [Pi Packages 包管理](../15-pi-packages/README.md)，学习如何安装、创建和分享扩展包。
