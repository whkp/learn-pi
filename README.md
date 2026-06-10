# Learn Pi

<p align="center">
  <strong>面向开发者的 Pi 编码智能体完全指南</strong>
</p>

<p align="center">
  <a href="https://pi.dev"><img src="https://img.shields.io/badge/pi.dev-pi.dev-blue.svg" alt="pi.dev"></a>
  <a href="https://github.com/earendil-works/pi-mono"><img src="https://img.shields.io/badge/GitHub-earendil--works/pi--mono-orange.svg" alt="GitHub"></a>
  <a href="https://discord.com/invite/3cU7Bz4UPx"><img src="https://img.shields.io/badge/Discord-Community-5865F2.svg" alt="Discord"></a>
</p>

---

## 项目简介

本项目是一份**面向开发者的 Pi 编码智能体完全学习指南**，以 [earendil-works/pi-mono](https://github.com/earendil-works/pi-mono) 为核心，帮助你：

- **深入理解** AI Coding Agent 的核心概念与设计思想
- **全面掌握** Pi 的架构设计与源码实现
- **熟练运用** Pi 的交互模式、会话管理、扩展系统等核心功能
- **灵活定制** 通过 Skills、Extensions、Prompt Templates 打造个性化工作流
- **实战落地** 构建自己的扩展、技能和项目

> **为什么选择 Pi？** 它是一个极致可扩展的终端编码智能体，核心简洁但功能强大。通过 TypeScript 扩展系统，你可以定制几乎一切——从工具、UI 到整个工作流。这是学习现代 AI Agent 设计的最佳实践。

---

## 学习路线图

```
┌─────────────────────────────────────────────────────────────────┐
│                        学习路线图                                │
│                                                                 │
│   Phase 1              Phase 2            Phase 3    Phase 4    │
│  ┌──────────┐      ┌──────────┐      ┌─────────┐  ┌─────────┐ │
│  │ 基础概念  │ ──→  │ 动手实践  │ ──→  │ 进阶使用 │→ │ 深入实战 │ │
│  └──────────┘      └──────────┘      └─────────┘  └─────────┘ │
│  ·AI Agent概念      ·安装配置          ·扩展开发     ·压缩管理  │
│  ·Pi项目概览        ·交互模式          ·提示词模板   ·SDK/RPC   │
│  ·架构深入          ·会话管理          ·主题定制     ·桌面端    │
│  ·核心模块          ·Provider配置      ·常用扩展     ·实战项目  │
│  ·扩展系统          ·Skills技能        ·包管理                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 目录

### Phase 1：基础概念（必读）

| 章节 | 内容 | 预计时间 |
|------|------|----------|
| [01 - 什么是 AI Coding Agent](docs/01-what-is-coding-agent/README.md) | Agent 定义、核心能力、与传统工具的区别、主流框架对比 | 2 小时 |
| [02 - Pi 项目概览](docs/02-pi-overview/README.md) | 项目背景、核心特性、设计哲学、为什么选 Pi | 1.5 小时 |
| [03 - 架构深入解析](docs/03-architecture-deep-dive/README.md) | Monorepo 结构、五层架构、数据流、设计模式 | 3 小时 |
| [04 - 核心模块源码解读](docs/04-core-modules/README.md) | pi-ai、pi-agent-core、pi-coding-agent 核心代码 | 4 小时 |
| [05 - 扩展系统与工具链](docs/05-extension-system/README.md) | 扩展系统架构、工具注册、事件系统、UI 扩展 | 2 小时 |

### Phase 2：动手实践

| 章节 | 内容 | 预计时间 |
|------|------|----------|
| [06 - 安装与快速上手](docs/06-install-and-quickstart/README.md) | 环境搭建、认证配置、第一个会话、常见问题 | 2 小时 |
| [07 - 交互模式详解](docs/07-interactive-mode/README.md) | 编辑器功能、斜杠命令、快捷键、消息队列 | 2 小时 |
| [08 - 会话管理](docs/08-session-management/README.md) | 会话创建、恢复、分支、克隆、导出 | 2 小时 |
| [09 - Provider 与模型配置](docs/09-providers-and-models/README.md) | 认证方式、模型切换、自定义 Provider、多模型策略 | 2 小时 |
| [10 - Skills 技能系统](docs/10-skills-system/README.md) | 技能发现、使用、创建、从 Claude Code 迁移 | 2 小时 |

### Phase 3：进阶使用

| 章节 | 内容 | 预计时间 |
|------|------|----------|
| [11 - Extensions 扩展开发](docs/11-extensions-development/README.md) | 扩展结构、自定义工具、事件钩子、UI 组件 | 3 小时 |
| [12 - Prompt Templates 提示词模板](docs/12-prompt-templates/README.md) | 模板语法、参数传递、工作流集成 | 1.5 小时 |
| [13 - 主题与 UI 定制](docs/13-themes-and-ui/README.md) | 主题系统、自定义渲染、Footer/Header、Widget | 2 小时 |
| [14 - 常用扩展实战](docs/14-common-extensions/README.md) | 联网搜索、计划模式、权限控制、Git 集成等 | 3 小时 |
| [15 - Pi Packages 包管理](docs/15-pi-packages/README.md) | 安装、更新、创建、分享你的扩展包 | 2 小时 |

### Phase 4：深入与实战

| 章节 | 内容 | 预计时间 |
|------|------|----------|
| [16 - 会话压缩与上下文管理](docs/16-compaction/README.md) | 压缩原理、配置调优、分支摘要、自定义压缩 | 2 小时 |
| [17 - SDK 与 RPC 编程接口](docs/17-sdk-and-rpc/README.md) | SDK 集成、RPC 模式、JSON 模式、进程集成 | 3 小时 |
| [18 - 桌面端设计方案](docs/18-desktop-design/README.md) | Electron/Tauri 方案、架构设计、权限策略 | 2 小时 |
| [19 - 实战项目](docs/19-real-projects/README.md) | 运维助手、代码审查、自定义工作流 | 4 小时 |

---

## 快速开始

### 1. 安装 Pi

```bash
npm install -g --ignore-scripts @earendil-works/pi-coding-agent
```

### 2. 认证

```bash
# 方式一：OAuth 登录
pi
/login

# 方式二：API Key
export ANTHROPIC_API_KEY=sk-ant-...
pi
```

### 3. 开始使用

```bash
cd /path/to/your/project
pi "帮我分析这个项目的结构"
```

### 4. 按顺序阅读文档

建议从 [01 - 什么是 AI Coding Agent](docs/01-what-is-coding-agent/README.md) 开始，按顺序阅读。

---

## 目录结构

```
learn-pi/
├── README.md                              # 本文件
├── LICENSE                                # MIT 许可证
├── docs/                                  # 文档目录
│   ├── 01-what-is-coding-agent/           # 什么是 AI Coding Agent
│   ├── 02-pi-overview/                    # Pi 项目概览
│   ├── 03-architecture-deep-dive/         # 架构深入解析
│   ├── 04-core-modules/                   # 核心模块源码解读
│   ├── 05-extension-system/               # 扩展系统与工具链
│   ├── 06-install-and-quickstart/         # 安装与快速上手
│   ├── 07-interactive-mode/               # 交互模式详解
│   ├── 08-session-management/             # 会话管理
│   ├── 09-providers-and-models/           # Provider 与模型配置
│   ├── 10-skills-system/                  # Skills 技能系统
│   ├── 11-extensions-development/         # Extensions 扩展开发
│   ├── 12-prompt-templates/               # Prompt Templates 提示词模板
│   ├── 13-themes-and-ui/                  # 主题与 UI 定制
│   ├── 14-common-extensions/              # 常用扩展实战
│   ├── 15-pi-packages/                    # Pi Packages 包管理
│   ├── 16-compaction/                     # 会话压缩与上下文管理
│   ├── 17-sdk-and-rpc/                    # SDK 与 RPC 编程接口
│   ├── 18-desktop-design/                 # 桌面端设计方案
│   └── 19-real-projects/                  # 实战项目
├── pi-architecture-intro.md               # 架构介绍（已有）
└── pi-desktop-design.md                   # 桌面端设计（已有）
```

---

## Star History

如果这个项目对你有帮助，请给一个 Star ⭐

你的 Star 是我持续更新的动力！

---

## 参考项目

- [earendil-works/pi-mono](https://github.com/earendil-works/pi-mono) - Pi 编码智能体源码
- [pi.dev](https://pi.dev) - Pi 官方网站
- [Agent Skills 标准](https://agentskills.io) - 技能系统规范

---

## License

本项目采用 [MIT License](LICENSE) 开源。

Pi 的源码版权归 earendil-works 所有。
