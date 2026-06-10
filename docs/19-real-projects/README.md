# 实战项目

> 通过实际项目，巩固所学知识，构建实用的 Pi 扩展和工作流。

---

## 一、项目一：运维助手

### 1.1 项目目标

构建一个运维助手扩展，帮助监控服务器状态、执行运维任务。

### 1.2 功能设计

| 功能 | 说明 |
|------|------|
| **服务器状态** | CPU、内存、磁盘使用率 |
| **服务监控** | 检查服务运行状态 |
| **日志分析** | 分析错误日志 |
| **部署脚本** | 执行部署任务 |

### 1.3 实现

```typescript
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { execSync } from "node:child_process";

export default function (pi: ExtensionAPI) {
  // 服务器状态工具
  pi.registerTool({
    name: "server-status",
    label: "服务器状态",
    description: "获取服务器 CPU、内存、磁盘使用率",
    parameters: Type.Object({}),
    async execute() {
      const cpu = execSync("top -bn1 | grep 'Cpu(s)' | awk '{print $2}'").toString().trim();
      const mem = execSync("free -m | awk 'NR==2{printf \"%.2f%%\", $3*100/$2}'").toString().trim();
      const disk = execSync("df -h / | awk 'NR==2{print $5}'").toString().trim();
      
      return {
        content: [{
          type: "text",
          text: `CPU: ${cpu}%\n内存: ${mem}\n磁盘: ${disk}`
        }]
      };
    }
  });
  
  // 服务检查工具
  pi.registerTool({
    name: "check-service",
    label: "检查服务",
    description: "检查指定服务的运行状态",
    parameters: Type.Object({
      service: Type.String({ description: "服务名称" })
    }),
    async execute(toolCallId, params) {
      try {
        const status = execSync(`systemctl is-active ${params.service}`).toString().trim();
        return {
          content: [{ type: "text", text: `服务 ${params.service}: ${status}` }]
        };
      } catch (e) {
        return {
          content: [{ type: "text", text: `服务 ${params.service}: 未运行` }]
        };
      }
    }
  });
}
```

---

## 二、项目二：代码审查工作流

### 2.1 项目目标

构建一个完整的代码审查工作流，包括静态分析、测试执行、安全检查。

### 2.2 技能定义

```
code-review-workflow/
├── SKILL.md
└── scripts/
    ├── lint.sh
    ├── test.sh
    └── security-scan.sh
```

**SKILL.md：**

````markdown
---
name: code-review-workflow
description: 完整的代码审查工作流，包括 lint、测试、安全检查。
---

# 代码审查工作流

## 步骤

1. **静态分析**
```bash
./scripts/lint.sh
```

2. **单元测试**
```bash
./scripts/test.sh
```

3. **安全扫描**
```bash
./scripts/security-scan.sh
```

## 输出

生成审查报告，包含：
- 代码质量问题
- 测试覆盖率
- 安全漏洞
````

### 2.3 使用

```
/skill:code-review-workflow
```

---

## 三、项目三：文档生成器

### 3.1 项目目标

自动为代码生成 API 文档、使用说明、变更日志。

### 3.2 提示词模板

**templates/api-doc.md：**

```markdown
---
description: 为代码生成 API 文档
argument-hint: "<file>"
---
为 $1 生成详细的 API 文档，包括：

1. **功能描述**
2. **参数说明**
3. **返回值**
4. **使用示例**
5. **注意事项**

使用 Markdown 格式输出。
```

**templates/changelog.md：**

```markdown
---
description: 生成变更日志
---
根据 `git log --oneline -20` 生成变更日志。

格式：
- **新增**：新功能
- **修复**：Bug 修复
- **优化**：性能优化
- **变更**：其他变更
```

### 3.3 使用

```
/api-doc src/api/users.ts
/changelog
```

---

## 四、项目四：自动化测试

### 4.1 项目目标

构建自动化测试工作流，包括单元测试、集成测试、E2E 测试。

### 4.2 扩展实现

```typescript
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { execSync } from "node:child_process";

export default function (pi: ExtensionAPI) {
  // 运行测试
  pi.registerTool({
    name: "run-tests",
    label: "运行测试",
    description: "运行指定类型的测试",
    parameters: Type.Object({
      type: Type.Union([
        Type.Literal("unit"),
        Type.Literal("integration"),
        Type.Literal("e2e")
      ], { description: "测试类型" })
    }),
    async execute(toolCallId, params, signal, onUpdate) {
      onUpdate({ status: "running", message: `运行 ${params.type} 测试...` });
      
      const commands = {
        unit: "npm run test:unit",
        integration: "npm run test:integration",
        e2e: "npm run test:e2e"
      };
      
      try {
        const output = execSync(commands[params.type], { 
          encoding: "utf-8",
          signal 
        });
        return {
          content: [{ type: "text", text: `测试通过:\n${output}` }]
        };
      } catch (e) {
        return {
          content: [{ type: "text", text: `测试失败:\n${e.message}` }]
        };
      }
    }
  });
  
  // 测试覆盖率
  pi.registerTool({
    name: "test-coverage",
    label: "测试覆盖率",
    description: "获取测试覆盖率报告",
    parameters: Type.Object({}),
    async execute() {
      const output = execSync("npm run test:coverage", { encoding: "utf-8" });
      return {
        content: [{ type: "text", text: output }]
      };
    }
  });
}
```

---

## 五、项目五：Git 工作流助手

### 5.1 项目目标

简化 Git 操作，包括分支管理、提交规范、代码合并。

### 5.2 功能设计

| 功能 | 命令 |
|------|------|
| **创建分支** | `/branch feature/xxx` |
| **提交** | `/commit feat: xxx` |
| **合并** | `/merge main` |
| **推送** | `/push` |

### 5.3 实现

```typescript
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { execSync } from "node:child_process";

export default function (pi: ExtensionAPI) {
  // 创建分支
  pi.registerCommand("branch", {
    description: "创建并切换到新分支",
    handler: async (args, ctx) => {
      if (!args) {
        ctx.ui.notify("请提供分支名称", "error");
        return;
      }
      
      try {
        execSync(`git checkout -b ${args}`, { stdio: "ignore" });
        ctx.ui.notify(`已创建分支: ${args}`, "info");
      } catch (e) {
        ctx.ui.notify("创建分支失败", "error");
      }
    }
  });
  
  // 提交
  pi.registerCommand("commit", {
    description: "提交更改",
    handler: async (args, ctx) => {
      const message = args || "手动提交";
      
      try {
        execSync("git add -A", { stdio: "ignore" });
        execSync(`git commit -m "${message}"`, { stdio: "ignore" });
        ctx.ui.notify(`已提交: ${message}`, "info");
      } catch (e) {
        ctx.ui.notify("提交失败", "error");
      }
    }
  });
  
  // 推送
  pi.registerCommand("push", {
    description: "推送到远程",
    handler: async (args, ctx) => {
      try {
        execSync("git push", { stdio: "ignore" });
        ctx.ui.notify("已推送", "info");
      } catch (e) {
        ctx.ui.notify("推送失败", "error");
      }
    }
  });
}
```

---

## 六、项目最佳实践

### 6.1 项目结构

```
my-pi-project/
├── extensions/          # 扩展
├── skills/              # 技能
├── prompts/             # 提示词模板
├── themes/              # 主题
├── scripts/             # 辅助脚本
├── package.json         # 包配置
└── README.md            # 项目说明
```

### 6.2 开发流程

1. **明确需求**：确定要解决的问题
2. **设计接口**：定义工具、命令、技能
3. **实现功能**：编写扩展代码
4. **测试验证**：使用 `pi -e` 测试
5. **文档完善**：编写使用说明
6. **打包分享**：发布为 pi 包

### 6.3 调试技巧

```bash
# 测试扩展
pi -e ./my-extension.ts

# 查看日志
pi --verbose

# 禁用其他扩展
pi --no-extensions -e ./my-extension.ts
```

---

## 七、小结

| 项目 | 技术点 |
|------|--------|
| **运维助手** | 自定义工具、系统命令 |
| **代码审查** | 技能系统、脚本集成 |
| **文档生成** | 提示词模板 |
| **自动化测试** | 扩展、命令注册 |
| **Git 工作流** | 命令、Git 集成 |

---

## 总结

通过本指南，你已经掌握了：

1. **基础概念**：AI Coding Agent、Pi 架构、核心模块
2. **动手实践**：安装配置、交互模式、会话管理、Provider 配置
3. **进阶使用**：Skills、Extensions、Prompt Templates、Themes
4. **深入实战**：上下文管理、SDK/RPC、桌面端设计、实战项目

现在你可以：
- 高效使用 Pi 进行日常开发
- 创建自定义扩展定制工作流
- 构建技能和提示词模板
- 将 Pi 集成到其他应用中

继续探索，构建属于你的 AI 编码助手！
