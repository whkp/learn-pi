# 架构总览 —— Pi 的分层与 Agent 产品的通用骨架

> 在拆解具体机制之前，先看整体：Pi 这个 monorepo 如何分层，一个 Agent 产品通常由哪些层组成，以及"模型无关的核心"与"产品环境""前端"之间的边界在哪。这一章是全课程的坐标轴——后续每一章讨论的机制，都可以在章末的通用骨架表里找到它的层位。

## 学习目标

- 理解 Pi 0.84.2 的包结构：核心四包 + 实验性包，以及依赖方向。
- 掌握核心边界：可复用的大脑（Agent core）、产品环境（coding-agent）、前端（TUI / RPC / JSON）彼此独立。
- 理解常见 Agent 产品架构的通用分层，并能在任意 Agent 产品中认出这些层。
- 建立两个定位工具：「这个机制属于哪一层？」「这一层的状态存在哪？」

## 机制：分层的三句话

### 三句判断

1. **模型无关的核心**：Agent 循环、消息、工具、事件与 Provider 协议——不依赖具体 UI、具体 Provider、具体文件布局。把这一层抽出来，它可以在任何前端、任何模型、任何产品形态下复用。
2. **产品环境**：把核心组装成真正的编码 Agent——工作目录、会话持久化、权限、扩展、上下文文件。这是"产品"与"库"的分界。
3. **前端消费事件**：TUI、Print、JSON、RPC 都是事件流的消费者，不直接操作核心内部状态。核心发事件，前端渲染，两者通过事件契约解耦。

### 为什么这样分

三个理由决定了这条边界的位置：

- **可测试性**：核心不依赖 UI 和文件布局，就能用脚本化模型做确定性测试（本课程 Python 实验正是这么做的）。
- **可移植性**：同一套核心可以驱动终端、Web、RPC 多个前端，而不改动循环代码。
- **可替换性**：换 Provider、换 UI、换存储，都不需要重写 Agent 逻辑。

### 一个统一定义

**agent = LLM + tool use**。模型提供语言与推理，以及"下一步调用哪个工具"的决策；其余一切（消息维护、工具注册与执行、权限、上下文、会话）都由包住模型的 harness 提供。因此，**核心不内置子代理、计划模式、MCP**——它们本质上都是一个工具，可以在产品层按需扩展。

## Pi 整体架构（0.84.2）

### 包拓扑

| 包 | npm 名 | 职责 | 状态 |
| --- | --- | --- | --- |
| ai | @earendil-works/pi-ai | Provider 适配、统一流式消息、模型目录 | 核心 |
| agent | @earendil-works/pi-agent-core | Agent 循环、消息、工具、事件（模型无关） | 核心 |
| coding-agent | @earendil-works/pi-coding-agent | CLI 产品：会话、设置、扩展、SDK/RPC | 核心 |
| tui | @earendil-works/pi-tui | 终端 UI 组件 | 核心 |
| client / protocol / server | — | 实验性：客户端、CBOR 二进制协议、会话服务 | 实验 |
| evals / telemetry / session-backends | — | 实验性：评测、遥测、会话存储后端 | 实验 |

依赖方向：**ai ← agent ← coding-agent**（tui 被 coding-agent 使用；实验性包的 API 可能变化，不构成稳定契约）。

### 关键源码入口

| 想找什么 | 去哪看（相对仓库根） |
| --- | --- |
| Agent 循环 | packages/agent/src/agent-loop.ts |
| 消息类型 | packages/agent/src/types.ts、packages/agent/src/harness/messages.ts |
| 工具定义 | packages/agent/src/types.ts（`AgentTool`）、packages/agent/src/harness/tools/ |
| 内置工具实现 | packages/agent/src/harness/tools/{read,write,edit,bash}.ts |
| 会话运行时与事件发射 | packages/coding-agent/src/core/agent-session-runtime.ts |
| 模型注册表 | packages/coding-agent/src/core/model-registry.ts |
| 压缩 | packages/agent/src/harness/compaction/compaction.ts |
| SDK 入口 | packages/coding-agent/src/core/sdk.ts |
| RPC / JSON 模式 | packages/coding-agent/src/modes/rpc/、modes/json-event.ts |

### 典型数据流

```
用户输入 → 会话状态与系统提示 → 模型流（Provider 层）
        → 工具调用与结果（Agent 核心层）→ 会话 JSONL 条目（产品层）
        → TUI / JSON / RPC 输出（前端层）
```

每一层都可能失败：Provider 超时、工具报错、会话写入失败、前端断线。因此产品代码要保留取消、限流、权限与会话恢复边界——这些主题在后续章节逐个展开。

## 常见 Agent 产品架构

把 Pi 的包结构抽象一层，就得到一个通用骨架——几乎所有 Agent 产品（Claude Code、Cursor、各类开源 harness）都能对号入座：

| 层 | 职责 | 本课程对应 |
| --- | --- | --- |
| Provider 层 | 统一多家模型协议、认证、重试 | [08 章](../08-providers-and-models/README.md)、[09 章](../09-reliability/README.md) |
| Agent 核心层 | 循环、消息、工具、事件（模型无关） | [02 章](../02-agent-loop/README.md)、[03 章](../03-tools/README.md)、[04 章](../04-messages-and-memory/README.md) |
| 产品层 | 会话、上下文、权限、扩展、上下文文件 | [05 章](../05-sessions/README.md)、[06 章](../06-events-and-extensions/README.md)、[07 章](../07-context-and-compaction/README.md) |
| 前端层 | TUI、Web、RPC、JSON——消费事件流 | [10 章](../10-protocol-and-integration/README.md) |

### 一个最小 harness 的组成清单

从零写一个可用的编码 Agent（参考 learn-agent-the-hard-way 的练习顺序），最少需要：

1. **Provider 抽象**：一个 `stream_response` 接口，隔离具体模型协议。
2. **工具循环**：声明工具 → 模型请求 → 执行 → 回填 → 再问（[02 章](../02-agent-loop/README.md)）。
3. **消息数组**：role 判别，工具结果成对回填（[04 章](../04-messages-and-memory/README.md)）。
4. **工具注册表**：加工具 = 加一行（[03 章](../03-tools/README.md)）。
5. **权限闸门**：执行前检查，不问模型意见（[03 章](../03-tools/README.md)）。
6. **上下文预算与压缩**：窗口不会无限大（[07 章](../07-context-and-compaction/README.md)）。
7. **会话持久化**：进程退出后还能恢复（[05 章](../05-sessions/README.md)）。

后面的高级能力（skill、subagent、MCP、浏览器）都是在 2-7 之上叠加的工具，不改变核心形状。

### 两个定位工具

读任何 Agent 项目的源码，先回答两个问题：

- **这个机制属于哪一层？**（Provider / Agent 核心 / 产品 / 前端）——决定它依赖谁、被谁依赖。
- **这一层的状态存在哪？**（消息数组、会话文件、设置文件、UI 状态）——决定它怎么持久化、怎么恢复。

卡住时回到本表重置。

## 当前 Pi 行为

- 固定基线：Pi 0.84.2 @ `914cf1472e715297caa30db4b9535d534a9eb718`；包拓扑、API 以该版本源码为准。
- 旧图中的 pi-web-ui 不是当前包；课程也不把实验性包当作稳定契约。
- 各章引用的源码路径均为该基线的真实路径，可直接对照阅读。

## 在 Pi 里怎么操作

```sh
pi                 # 交互式 TUI
pi -p "prompt"     # Print：输出结果后退出
pi --mode json     # JSON：事件流输出到 stdout
pi --mode rpc      # RPC：stdin/stdout 协议
```

四种模式共享同一个 Agent 核心，区别只在前端层——这正是"前端消费事件"的实际体现。

## Python 对照

[mini_agent.py](../../learn_pi_lab/labs/mini_agent.py) 是同一个分层的**单文件缩影**，文件内小节标题直接标注了每个部分对应 Pi / Tau 的哪个源文件：

```text
mini_agent.py 的节          →  对应 Pi / Tau 源码
messages（role 判别消息）     →  packages/agent/src/types.ts / tau_agent/messages.py
tools（AgentTool）           →  packages/agent/src/types.ts / tau_agent/tools.py
provider（ModelProvider）    →  tau_agent/provider.py
events（AgentEvent 联合）    →  tau_agent/events.py
loop（run_agent_loop）       →  packages/agent/src/agent-loop.ts / tau_agent/loop.py
harness（AgentHarness）      →  tau_agent/harness.py
session（dump/load JSONL）   →  tau_agent/session/jsonl.py
```

Tau 对照：`tau_ai`（Provider 层）← `tau_agent`（Agent 核心层）← `tau_coding`（产品层），与 Pi 的包结构一一对应，是"同一架构的另一种语言实现"的直接样本。

## 实现对照：Pi 源码与 Tau 双版本

同一架构的两种语言实现——包级对照：

| Pi 0.84.2 | Tau | 职责 |
| --- | --- | --- |
| packages/ai | tau_ai | Provider 层：统一模型协议、目录、重试 |
| packages/agent | tau_agent | Agent 核心层：循环、消息、工具、事件、会话 entry |
| packages/coding-agent | tau_coding | 产品层：CLI、TUI、上下文、技能、RPC、会话存储 |
| packages/tui | tau_coding/tui | 前端层：终端 UI |

模块级对照（想找同一个机制在另一套实现里的位置）：

| 机制 | Pi | Tau |
| --- | --- | --- |
| Agent 循环 | packages/agent/src/agent-loop.ts | tau_agent/loop.py |
| 消息类型 | packages/agent/src/types.ts + packages/ai/src/types.ts | tau_agent/messages.py |
| 工具定义 | packages/agent/src/types.ts（AgentTool） | tau_agent/tools.py |
| 事件 | packages/agent/src/types.ts（AgentEvent） | tau_agent/events.py |
| 会话 entry | packages/coding-agent/docs/session-format.md | tau_agent/session/entries.py |
| 会话树 | （session-manager） | tau_agent/session/tree.py |
| JSONL 会话 | （session-backends） | tau_agent/session/jsonl.py |
| 压缩 | packages/agent/src/harness/compaction/compaction.ts | tau_agent/session/memory.py |
| Provider 目录 | packages/coding-agent/src/core/model-registry.ts | tau_coding/provider_catalog.py |
| 重试 | packages/ai/src/utils/retry.ts | tau_ai/retry.py |
| RPC | packages/coding-agent/src/modes/rpc/rpc-mode.ts | tau_coding/rpc.py |
| SDK 入口 | packages/coding-agent/src/core/sdk.ts | tau_agent/harness.py |

这张表就是本课程每章“实现对照”小节的索引：遇到任何机制，先在本表找到两套实现的位置，再去对照读。

## Python 实验

```sh
python3 -m learn_pi_lab lab mini-agent
```

## 验证方式

```sh
python3 -m unittest tests.test_13_mini_agent -v
python3 scripts/check_course_contract.py
```

## 边界与安全

- 分层是设计边界，不是安全边界：权限、认证、沙箱必须在产品层实现，核心不替你兜底。
- 本课程 Python 教学模型刻意只覆盖"可迁移的机制"，不复制 Pi 的全部产品细节。
- 实验性包（protocol/server/client）可能随时变化，课程不把它们纳入契约。
