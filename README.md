# Learn Pi

**面向开发者的 Pi 编码智能体学习仓库：准确资料、可运行的 Python 实验、自动化测试与离线实战项目。**

先立一个判断：**模型负责推理，Harness 负责给它双手、眼睛和工作台。**

智能体产品 = 模型 + Harness。模型决定何时思考、何时调用工具、何时停下；Harness 决定模型能不能真正读文件、改代码、跑命令、记住会话。本课程研究的正是 Harness 这一侧——以 Pi 为蓝本，用离线、可运行、可测试的 Python 教学模型把关键机制讲清楚。

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

一句话：**能跑的 Agent 不止是"调模型的循环"，而是循环周围一整套可验证的工程边界。**

- **Agent 循环**：消息进、事件出——谁在驱动循环，谁在消费事件
- **工具系统**：类型化工具、注入式执行器、执行前检查（意图 → 路径 → 执行）
- **会话与分支**：JSONL 逐帧、会话树、压缩切割边界
- **上下文与资源**：规则文件发现、资源扫描、技能/模板的目录规则
- **可靠性**：有限重试、错误隔离、可观测结果
- **协议边界**：JSONL RPC 的粘包/半包/校验

每章都有可运行的 Python 实验和自动化测试。**先读结论，再跑代码，最后自己改一版。**

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
2. 读 [01 什么是 AI Coding Agent](docs/01-what-is-coding-agent/README.md) → [02 Pi 概览](docs/02-pi-overview/README.md) → [03 架构深入解析](docs/03-architecture-deep-dive/README.md)。
3. 跑第一个实验，确认最小循环真的能跑：

```sh
cd learn-pi
python3 -m learn_pi_lab lab agent-loop
python3 -m learn_pi_lab lab mini-agent
```

4. 按下面五个阶段推进，每阶段结束前，先自己重写一遍最小版本再继续。

## 学习路径（五个阶段）

| 阶段 | 阅读重点 | 动手产物 |
| --- | --- | --- |
| **一、基础** | [01 Agent](docs/01-what-is-coding-agent/README.md)、[02 Pi 概览](docs/02-pi-overview/README.md)、[03 架构](docs/03-architecture-deep-dive/README.md) | agent-loop、mini-agent Python 实验 |
| **二、运行机制** | [04 核心模块](docs/04-core-modules/README.md)、[05 扩展](docs/05-extension-system/README.md)、[08 会话](docs/08-session-management/README.md) | 工具策略、会话树、事件总线 |
| **三、配置与集成** | [09 模型](docs/09-providers-and-models/README.md)、[11 扩展开发](docs/11-extensions-development/README.md)、[16 压缩](docs/16-compaction/README.md)、[17 SDK/RPC](docs/17-sdk-and-rpc/README.md) | Provider 注册表、重试、JSONL 编解码 |
| **四、工程实践** | [19 实战项目](docs/19-real-projects/README.md)、[20 安全](docs/20-safety/README.md)、[21 可靠性](docs/21-reliability/README.md)、[22 组合](docs/22-composition-and-mcp/README.md)、[23 评测](docs/23-testing-and-evaluation/README.md) | 四个离线 mini-project |

主章节（20-23）由课程契约检查器强制校验；01-19 是参考路线，帮助你按需深入具体主题。

## 课程地图

| 章节 | 主题 | 一句话 |
| --- | --- | --- |
| [01](docs/01-what-is-coding-agent/README.md) | 什么是 AI Coding Agent | 从代码补全到自主 Agent 的概念跃迁 |
| [02](docs/02-pi-overview/README.md) | Pi 项目概览 | 定位、核心特性、设计哲学 |
| [03](docs/03-architecture-deep-dive/README.md) | 架构深入解析 | 包边界、数据流、Tau 对照实验 |
| [04](docs/04-core-modules/README.md) | 核心模块源码解读 | ai / agent / coding-agent 职责 |
| [05](docs/05-extension-system/README.md) | 扩展系统与工具链 | 事件名、改写边界、社区扩展参考 |
| [06](docs/06-install-and-quickstart/README.md) | 安装与快速上手 | Node 22.19+、npm / curl 安装 |
| [07](docs/07-interactive-mode/README.md) | 交互模式详解 | 编辑器、斜杠命令、快捷键 |
| [08](docs/08-session-management/README.md) | 会话管理 | JSONL v3、/tree、分支 |
| [09](docs/09-providers-and-models/README.md) | Provider 与模型配置 | models.json、registerProvider |
| [10](docs/10-skills-system/README.md) | Skills 技能系统 | SKILL.md、渐进式加载 |
| [11](docs/11-extensions-development/README.md) | Extensions 扩展开发 | 注册工具、命令、UI |
| [12](docs/12-prompt-templates/README.md) | Prompt Templates | /name 模板展开 |
| [13](docs/13-themes-and-ui/README.md) | 主题与 UI 定制 | themes/*.json |
| [14](docs/14-common-extensions/README.md) | 常用扩展实践 | 工具、命令、快捷键案例 |
| [15](docs/15-pi-packages/README.md) | Pi Packages 包管理 | pi install npm:/git: |
| [16](docs/16-compaction/README.md) | 会话压缩与上下文管理 | session_before_compact 边界 |
| [17](docs/17-sdk-and-rpc/README.md) | SDK 与 RPC 编程接口 | session.subscribe、JSONL 帧 |
| [18](docs/18-desktop-design/README.md) | 桌面端集成案例研究 | 基于 SDK/RPC 的推测性案例 |
| [19](docs/19-real-projects/README.md) | 实战项目 | 四个离线 mini-project |
| [20](docs/20-safety/README.md) | 安全与权限边界 | 允许列表、路径边界 |
| [21](docs/21-reliability/README.md) | 可靠性、取消与错误边界 | 有限重试、错误数据流 |
| [22](docs/22-composition-and-mcp/README.md) | 组合、资源与 MCP 边界 | 资源发现、JSONL 逐帧 |
| [23](docs/23-testing-and-evaluation/README.md) | 测试与评测 | 行为测试、契约、报告 |

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

**主路线（推荐）**：按阶段顺序推进，01 → 19 → 20-23。每章先读"当前 Pi 行为"确认事实边界，再跑对应 Python 实验，最后自己改一版。

**先跑起来，再补齐**：跳过背景章节，直接跑 `python3 -m learn_pi_lab lab agent-loop` 和 `mini-agent`，遇到不懂的机制再回到对应章节。

**卡住时**：回到 [00 课程地图](docs/00-course-map.md) 和 [Pi 源码映射](docs/pi-source-map.md) 重置——卡住通常是"这个机制插在哪一层？状态存在哪？"没对上，而不是读不懂代码。

## 仓库结构

```text
learn-pi/
├── docs/                  # 23 章课程资料（中文）
│   ├── 00-course-map.md   # 课程地图与主章节清单
│   ├── 01-19/             # 参考路线章节
│   ├── 20-23/             # 主章节（契约检查）
│   ├── pi-source-map.md   # Pi 固定基线映射
│   └── glossary.md        # 术语表
├── learn_pi_lab/          # Python 教学实验包（仅标准库）
│   └── labs/              # 11 个实验模块
├── projects/              # 4 个离线实战项目
├── scripts/               # 课程契约与链接检查脚本
└── tests/                 # 101 个单元测试
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

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_course_contract.py
python3 scripts/check_markdown_links.py
```

三条命令都输出 `OK` / 测试全绿，即视为通过。

## 教学取舍

为了让"从 0 到 1 可重建"，本仓库做了一些刻意的取舍：

- **核心机制高保真，外围细节从简**：循环、边界、协议、重试讲透；发布、认证、OAuth 等回到固定基线文档。
- **先教最小正确版本，再说明扩展边界**：每个 Python 实验都是标准库、离线、确定性实现。
- **教学模型 ≠ 生产实现**：示例中的固定数据和策略不可直接替代生产配置；迁移到 Pi 时用 TypeScript 重新实现并补齐权限、取消、日志脱敏和端到端测试。
- **文档跟随实现**：任何 Pi 行为描述都以固定基线源码为准，Python 侧永远标注"这不是 Pi SDK"。

## 最终目标

读完本课程，你应该能清晰回答：

- Pi 的 Agent 循环里事件流如何流动？谁在驱动循环，谁在消费事件？
- 为什么工具要类型化？为什么路径要在进入执行层前先检查？
- 会话为什么是 JSONL v3 而不是一个 JSON 数组？
- 压缩、重试、权限、逐帧解析各自解决什么问题？
- 如何用 Tau / Pi 固定基线源码交叉验证课程中的每一个说法？

如果这些问题你都能答上来，并且能自己重建一个最小版本，本课程就完成了它的任务。

---

**这不是"逐行复制源码"，这是"掌握真正重要的设计，然后自己重建它"。**

## License

本项目采用 [MIT License](LICENSE)。Pi 的源码版权归 earendil-works 所有。
