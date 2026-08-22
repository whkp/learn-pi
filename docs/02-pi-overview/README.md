# Pi 项目概览

> Pi 是一个极致可扩展的终端编码智能体——不强制你的工作流，而是让你定制它。

---

## 一、Pi 是什么？

Pi 是一个**终端编码智能体（Terminal Coding Harness）**，由 [earendil-works](https://github.com/earendil-works) 开发。它的核心理念是：

> **"Adapt pi to your workflows, not the other way around."**
> （让 Pi 适应你的工作流，而不是反过来。）

与 Claude Code 等闭源工具不同，Pi 完全开源，允许开发者自由定制和扩展。

---

## 二、核心特性

### 2.1 极致可扩展

Pi 的一切都可以通过扩展系统定制：

| 可扩展项 | 说明 |
|----------|------|
| **工具** | 自定义工具或替换内置工具 |
| **命令** | 注册斜杠命令 |
| **快捷键** | 绑定自定义快捷键 |
| **UI** | 自定义编辑器、Footer、Header、Widget |
| **事件** | 在 Agent 各阶段注入逻辑 |
| **Provider** | 接入新的 LLM 提供商 |
| **压缩** | 自定义上下文压缩策略 |
| **渲染** | 控制工具调用和消息的显示方式 |

### 2.2 多模式运行

Pi 支持四种运行模式：

| 模式 | 用途 |
|------|------|
| **交互式** | 终端 TUI，实时对话 |
| **Print** | 一次性查询，输出结果后退出 |
| **JSON** | 结构化事件输出，便于程序解析 |
| **RPC** | 进程间通信，用于集成 |

### 2.3 多 Provider 支持

Pi 支持几乎所有主流 LLM 提供商：

| 类型 | Provider |
|------|----------|
| **订阅** | Claude Pro/Max、ChatGPT Plus/Pro、GitHub Copilot |
| **API Key** | Anthropic、OpenAI、Google、DeepSeek、Mistral、Groq 等 20+ |
| **云服务** | Azure OpenAI、AWS Bedrock、Google Vertex |
| **国产** | 小米 MiMo、Kimi、MiniMax |

### 2.4 会话管理

Pi 提供强大的会话管理能力：

- **自动保存**：会话自动保存到 `~/.pi/agent/sessions/`
- **分支系统**：支持在任意点分叉，探索不同方案
- **压缩机制**：自动压缩旧消息，释放上下文空间
- **导出分享**：导出为 HTML 或分享为 GitHub Gist

---

## 三、设计哲学

### 3.1 最小核心

Pi 刻意不内置某些功能：

| 不内置 | 原因 |
|--------|------|
| **MCP** | 构建带 README 的 CLI 工具，或用扩展实现 |
| **子 Agent** | 用 tmux 启动多个实例，或自己实现 |
| **权限弹窗** | 在容器中运行，或用扩展实现确认流程 |
| **计划模式** | 写文件，或用扩展实现 |
| **内置待办** | 用 TODO.md 文件，或用扩展实现 |
| **后台 Bash** | 用 tmux，完全可观测 |

> **为什么？** 每个工作流都不同。内置这些功能会限制灵活性。通过扩展系统，你可以按需构建。

### 3.2 渐进式披露

Pi 采用渐进式披露策略：

- **技能**：只加载描述，按需加载完整指令
- **工具**：默认 4 个核心工具，按需添加
- **扩展**：自动发现，按需启用

### 3.3 安全第一

- 扩展运行在你的系统权限下，只安装信任的来源
- 技能可以指导模型执行任何操作，审查后再使用
- 文件操作默认在当前工作目录内

---

## 四、技术栈

| 层面 | 技术 |
|------|------|
| 语言 | TypeScript (100%) |
| 包管理 | npm workspaces |
| 构建 | tsc + esbuild |
| 代码检查 | Biome |
| 测试 | Vitest |
| 许可 | MIT |

---

## 五、与竞品对比

| 特性 | Pi | Claude Code | Aider | Nanobot |
|------|-----|-------------|-------|---------|
| 开源 | ✅ | ❌ | ✅ | ✅ |
| 语言 | TypeScript | - | Python | Python |
| 扩展系统 | ✅ 完整 | 有限 | 插件 | MCP |
| 多 Provider | ✅ 20+ | Anthropic | 多 | 多 |
| 会话分支 | ✅ | ❌ | ❌ | ❌ |
| SDK 集成 | ✅ | ❌ | ❌ | ❌ |
| 桌面端 | 本课程仅有集成案例，非官方产品 | ✅ | ❌ | ❌ |
| MCP 支持 | 可扩展 | 内置 | 内置 | 内置 |

---

## 六、适用场景

| 场景 | Pi 的优势 |
|------|-----------|
| **个人开发** | 快速上手，灵活定制 |
| **团队协作** | 通过 AGENTS.md 共享规范 |
| **CI/CD 集成** | RPC/SDK 模式易于集成 |
| **教学研究** | 完全开源，可深入源码 |
| **企业定制** | 扩展系统支持深度定制 |

---

## 七、项目结构预览

```
pi/
├── packages/
│   ├── ai/              # 统一 LLM API 层（pi-ai）
│   ├── agent/           # 智能体运行时核心（pi-agent-core）
│   ├── coding-agent/    # 交互式编码智能体 CLI
│   ├── tui/             # 终端 UI 库
│   ├── client/          # 实验性：客户端
│   ├── protocol/        # 实验性：CBOR 二进制协议
│   ├── server/          # 实验性：PiServer 会话服务
│   ├── evals/           # 实验性：评测
│   ├── telemetry/       # 遥测契约
│   └── session-backends/# 会话存储后端
├── scripts/             # 构建与工具脚本
└── package.json         # npm workspaces 配置
```

核心包依赖关系：**ai ← agent ← coding-agent**（tui 被 coding-agent 使用；client、protocol、server 等实验性包 API 可能变化）。

---

## 八、小结

| 要点 | 说明 |
|------|------|
| **定位** | 极致可扩展的终端编码智能体 |
| **核心理念** | 不强制工作流，让用户定制 |
| **技术栈** | TypeScript Monorepo |
| **扩展能力** | 工具、命令、UI、事件、Provider |
| **运行模式** | 交互式、Print、JSON、RPC、SDK |

---

## 下一步

了解了 Pi 的概览后，下一章我们将深入 [架构解析](../03-architecture-deep-dive/README.md)，理解 Pi 的分层设计和核心模块。
