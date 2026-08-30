# Learn Pi

[![在线阅读](https://img.shields.io/badge/在线阅读-whkp.github.io/learn--pi-blue)](https://whkp.github.io/learn-pi/)

**面向开发者的 Pi 编码智能体学习仓库：准确资料、可运行的 Python 实验、自动化测试与离线实战项目。**

先立一个判断：**智能来自模型，能力边界全来自 harness（包住模型的那层程序）。**

一个统一定义：**agent = LLM + tool use**。模型负责语言、推理，以及决定下一步调用哪个工具；除此之外的一切——消息维护、工具注册与执行、权限、上下文、会话——都是 harness 的职责。因此，Pi 核心不内置子代理、计划模式、MCP 等高级能力：它们本质上都是一个工具，可以按需扩展，而不是塞进核心。

本课程研究的正是 harness 这一侧——以 Pi 为蓝本，每一章围绕一个大主题，讲清“是什么 / 怎么做 / 为什么”，以少量核心代码（mini_agent / labs / Tau）配合文本解读，重点介绍 Pi 的核心设计。

```
                    THE AGENT PATTERN
                    =================

    User --> messages[] --> model --> response
                                        |
                          stop_reason == "toolUse"?
                         /                          \
                       yes                           no
                        |                             |
                  execute tools                    return text
                  append results
                  loop back -----------------> messages[]

    模型决定何时调用工具、何时停止。
    Harness 只负责执行模型的要求，以及围绕这个循环
    提供工具、上下文、会话、权限与可靠性边界。
```

## 这个仓库真正教什么

一句话：**能跑的 Agent 不止是“调模型的循环”，而是循环周围一整套可验证的工程边界。**

- **Agent 循环**：声明工具 → 模型请求调用 → 执行 → 结果回填 → 再问模型（[02 章](docs/02-agent-loop/README.md)）
- **工具系统**：工具层 + 注册表层 + 权限层；软约束（提示词）与硬闸门（权限）分工（[03 章](docs/03-tools/README.md)）
- **消息与记忆**：消息数组由 harness 维护，不是模型记住的；跨会话记忆的价值在筛选（[04 章](docs/04-messages-and-memory/README.md)）
- **会话管理**：JSONL v3、会话树、append-only 与分支（[05 章](docs/05-sessions/README.md)）
- **事件驱动**：事件契约、subscribe 与 pi.on 的分水岭；高级能力即工具（[06 章](docs/06-events-and-extensions/README.md)）
- **上下文压缩**：窗口即预算；压缩不是丢消息，是让模型总结它自己（[07 章](docs/07-context-and-compaction/README.md)）
- **可靠性**：错误分类、指数退避、错误隔离（[09 章](docs/09-reliability/README.md)）

每章都有核心设计解读、可运行的 Python 实验和自动化测试。**先读结论，再跑代码，最后自己改一版。**

## 这个仓库刻意不教什么

- **不是 Pi SDK、绑定或移植版**：Pi 是 TypeScript 项目，本仓库的 Python 仅是依赖标准库的教学模型。
- **不访问网络、不调用模型、不执行学习者提供的 shell 命令**：所有实验离线、确定、可复现。
- **不覆盖 Pi 的生产细节**：认证、OAuth、权限弹窗、扩展发布流程等，请回到固定基线源码和官方文档（pi.dev）核对。
- **不把教学模型伪装成当前 API**：任何 API 细节以 [Pi 源码映射](docs/pi-source-map.md) 固定基线（0.84.2 @ `914cf1472e715297caa30db4b9535d534a9eb718`）为准。

想看 Pi 的成品 Python 对照实现？请读 [Tau](https://github.com/huggingface/tau)（tau_agent / tau_ai / tau_coding），本课程的 [mini-agent 实验](learn_pi_lab/labs/mini_agent.py) 就是它的最小化镜像。

## 适合谁

- 了解 Python 基础（函数、类、标准库），想理解编码智能体如何工作
- 用过或听说过 Pi / Claude Code / 其他 coding agent，想弄清内部机制
- 准备基于 Pi 做二次开发、接入 SDK/RPC，或实现自己的 Agent 工具链

不需要 Node.js 经验。Pi 本身需要 Node.js 22.19.0 或更高版本，但本课程的 Python 实验只用 `python3`。

## 第一次来，从这里开始

不要随机打开章节。安全路径：

1. 读 [00 课程地图](docs/00-course-map.md) 了解课程结构与主章节。
2. 读 [01 架构总览](docs/01-architecture/README.md) → [02 Agent Loop](docs/02-agent-loop/README.md) → [03 工具系统](docs/03-tools/README.md)。
3. 跑第一个实验，确认最小循环真的能跑：

```sh
cd learn-pi
python3 -m learn_pi_lab lab agent-loop
python3 -m learn_pi_lab lab mini-agent
```

4. 按下面三阶段推进，每阶段结束前，先自己重写一遍最小版本再继续。

## 学习路径（三个阶段）

| 阶段 | 章节 | 动手产物 |
| --- | --- | --- |
| **一、架构与核心机制** | [01 架构总览](docs/01-architecture/README.md)、[02 Agent Loop](docs/02-agent-loop/README.md)、[03 工具系统](docs/03-tools/README.md)、[04 消息与记忆](docs/04-messages-and-memory/README.md) | agent-loop、mini-agent、权限实验 |
| **二、状态与边界** | [05 会话管理](docs/05-sessions/README.md)、[06 事件与扩展](docs/06-events-and-extensions/README.md)、[07 上下文压缩](docs/07-context-and-compaction/README.md) | 会话树、事件总线、压缩实验 |
| **三、集成与实践** | [08 Provider](docs/08-providers-and-models/README.md)、[09 可靠性](docs/09-reliability/README.md)、[10 协议与集成](docs/10-protocol-and-integration/README.md)、[11 实战与评测](docs/11-projects-and-evaluation/README.md) | Provider 目录、重试、JSONL、四个 mini-project |

## 课程地图

| 章节 | 大主题 | 一句话 |
| --- | --- | --- |
| [01](docs/01-architecture/README.md) | 架构总览 | Pi 分层与 Agent 产品通用骨架 |
| [02](docs/02-agent-loop/README.md) | Agent Loop | 模型如何驱动循环：Trace/Turn、stopReason |
| [03](docs/03-tools/README.md) | 工具系统 | 工具如何被声明、注册与约束 |
| [04](docs/04-messages-and-memory/README.md) | 消息与记忆 | 对话历史如何组织与传递 |
| [05](docs/05-sessions/README.md) | 会话管理 | 对话如何存储、恢复与分叉 |
| [06](docs/06-events-and-extensions/README.md) | 事件驱动与扩展 | 事件契约、subscribe vs pi.on、社区扩展 |
| [07](docs/07-context-and-compaction/README.md) | 上下文压缩 | 窗口即预算、切割点、成对不拆 |
| [08](docs/08-providers-and-models/README.md) | Provider 与模型 | 注册表、models.json、认证分离 |
| [09](docs/09-reliability/README.md) | 可靠性 | 错误分类、指数退避、错误隔离 |
| [10](docs/10-protocol-and-integration/README.md) | 协议与集成 | Print/JSON/RPC、JSONL 分帧 |
| [11](docs/11-projects-and-evaluation/README.md) | 实战与评测 | 四个 mini-project、测试与评测 |

配套资料：[Pi 源码映射](docs/pi-source-map.md)（固定基线）、[术语表](docs/glossary.md)。

## Python 实验

| 主题 | 模块 | 运行方式 |
| --- | --- | --- |
| Agent 循环 | learn_pi_lab/labs/agent_loop.py | python3 -m learn_pi_lab lab agent-loop |
| 最小 Agent（Tau 对照） | learn_pi_lab/labs/mini_agent.py | python3 -m learn_pi_lab lab mini-agent |
| 最小权限 | learn_pi_lab/labs/tool_permissions.py | python3 -m learn_pi_lab lab permissions |
| 规则文件 | learn_pi_lab/labs/context_files.py | 见模块测试 |
| 会话分支 | learn_pi_lab/labs/session_tree.py | python3 -m learn_pi_lab lab session-tree |
| 压缩边界 | learn_pi_lab/labs/compaction.py | python3 -m learn_pi_lab lab compaction |
| 资源发现 | learn_pi_lab/labs/resources.py | 见模块测试 |
| 事件派发 | learn_pi_lab/labs/extension_events.py | python3 -m learn_pi_lab lab events |
| Provider 目录 | learn_pi_lab/labs/provider_registry.py | python3 -m learn_pi_lab lab providers |
| 重试模型 | learn_pi_lab/labs/reliability.py | python3 -m learn_pi_lab lab reliability |
| JSONL RPC | learn_pi_lab/labs/rpc_jsonl.py | python3 -m learn_pi_lab lab rpc-jsonl |

## 离线实战项目

- [Session Inspector](projects/session_inspector.py)：只读统计 JSONL 会话记录。
- [Safe Review Runner](projects/safe_review_runner.py)：把审查意图约束为根目录内的只读目标。
- [CI Review Pipeline](projects/ci_review_pipeline.py)：将课程契约、链接和单元测试汇总为稳定结果。
- [RPC Console](projects/rpc_console.py)：使用允许列表处理单条 JSON 请求，不启动子进程。

每个项目都由 [test_11_projects.py](tests/test_11_projects.py) 覆盖。

## 阅读方法

**主路线（推荐）**：按阶段顺序推进，01 → 10。每章先读"机制"确认概念，再看"Pi 源码怎么实现"对照真实代码，跑对应 Python 实验，最后自己改一版。

**先跑起来，再补齐**：跳过背景章节，直接跑 `python3 -m learn_pi_lab lab agent-loop` 和 `mini-agent`，遇到不懂的机制再回到对应章节。

**卡住时**：回到 [00 课程地图](docs/00-course-map.md) 和 [Pi 源码映射](docs/pi-source-map.md) 重置——卡住通常是"这个机制插在哪一层？状态存在哪？"没对上，而不是读不懂代码。

## 仓库结构

```text
learn-pi/
├── docs/                  # 11 章课程资料（中文）
│   ├── 00-course-map.md   # 课程地图与主章节清单
│   ├── 01-architecture/   # 架构总览（Pi 分层 + 通用骨架）
│   ├── 02-agent-loop/     # 每章一个大主题
│   ├── ...                #   （工具/消息/会话/事件/压缩/Provider/可靠/协议/实战）
│   ├── 11-projects-and-evaluation/
│   ├── pi-source-map.md   # Pi 固定基线映射
│   └── glossary.md        # 术语表
├── learn_pi_lab/          # Python 教学实验包（仅标准库）
│   └── labs/              # 11 个实验模块
├── examples/harness/      # 构建路线：裸 API → 完整 Harness（12 步，B01-B06 完成）
├── projects/              # 4 个离线实战项目
├── scripts/               # 课程契约与链接检查、站点构建
└── tests/                 # 108 个单元测试
```

## 快速开始

Pi 当前需要 Node.js 22.19.0 或更高版本。安装和认证请以 Pi 的 Quickstart 与 Settings 文档为准；不要把密钥写进仓库。

```sh
npm install -g @earendil-works/pi-coding-agent
pi
```

本课程的 Python 实验不访问网络、不调用模型，也不会执行学习者提供的 shell 命令：

```sh
cd learn-pi
python3 -m learn_pi_lab lab agent-loop
python3 -m unittest discover -s tests -v
```

## 验证

一键检查 + 站点构建（`docs/` 是单一事实源，发布前必须运行）：

```sh
./scripts/build_and_check.sh                  # 契约 + 链接 + 测试 + mdBook 构建
./scripts/build_and_check.sh --skip-build     # 只检查，不构建站点
```

单独执行：

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_course_contract.py
python3 scripts/check_markdown_links.py
```

三条命令都输出 `OK` / 测试全绿，即视为通过。CI（`.github/workflows/pages.yml`）在每次 push 时自动执行同样的检查并发布网站。

## 教学取舍

为了让"从 0 到 1 可重建"，本仓库做了一些刻意的取舍：

- **核心机制高保真，外围细节从简**：循环、边界、协议、重试讲透；发布、认证、OAuth 等回到固定基线文档。
- **先教最小正确版本，再说明扩展边界**：每个 Python 实验都是标准库、离线、确定性实现。
- **教学模型 ≠ 生产实现**：示例中的固定数据和策略不可直接替代生产配置；迁移到 Pi 时用 TypeScript 重新实现并补齐权限、取消、日志脱敏和端到端测试。
- **文档跟随实现**：任何 Pi 行为描述都以固定基线源码为准，Python 侧永远标注"这不是 Pi SDK"。

## 最终目标

读完本课程，你应该能清晰回答：

- Pi 的 Agent 循环里事件流如何流动？Trace 与 Turn 有什么区别？
- 为什么工具要类型化？为什么路径要在进入执行层前先检查？
- 会话为什么是 JSONL v3 而不是一个 JSON 数组？为什么必须"认父不认子"？
- subscribe 与 pi.on 有什么本质区别？压缩为什么不能拆开成对的工具调用？
- 如何用 Tau / Pi 固定基线源码交叉验证课程中的每一个说法？

如果这些问题你都能答上来，并且能自己重建一个最小版本，本课程就完成了它的任务。

---

**这不是"逐行复制源码"，这是"掌握真正重要的设计，然后自己重建它"。**

## License

本项目采用 [MIT License](LICENSE)。Pi 的源码版权归 earendil-works 所有。
