# 架构总览 —— Pi 的分层与核心设计

> 学习任何系统，都先看它为什么长成这个样子。Pi 的架构回答一个问题：**一个能自主工作的编码 Agent，究竟由什么组成？** 答案是：模型负责思考，harness 负责提供"手和眼睛"。本章先立起这个框架，后面每一章讲的机制都能对号入座。

## 学习目标

- 理解 Pi 的分层：模型无关的核心 / 产品环境 / 前端，三者通过事件契约解耦。
- 理解"高级能力即工具"这一设计取舍：为什么核心保持小而可扩展。
- 认识 Pi 0.85.1 的包拓扑与依赖方向，并能在任何 Agent 产品中认出这些层。

## 一、问题：Agent 产品由什么组成

先用一个思想实验切入。同一个模型——同一天、同一个版本、同一个 API——装进两个产品：一个是网页聊天框，一个是 Pi。前者只会跟你聊天；后者能读你的仓库、改你的代码、跑你的测试、在删文件前停下来问你。

**模型一模一样，能力天差地别。差别是谁给的？**

把"你以为是模型能力"的东西逐项拆开看：

| 你看到的 | 实际是谁提供的 |
|---|---|
| 它记得这段对话说过什么 | harness——消息数组是 harness 维护的 |
| 它会读文件、跑命令 | harness——工具是 harness 注册的 |
| 它删文件前会先问你 | harness——权限是 harness 设计的 |
| 聊了一下午也没失忆 | harness——压缩是 harness 触发的 |
| 它"学会"了新技能 | harness——skill 是 harness 加载的 |

模型提供的是什么？语言、推理，以及最关键的一件事：**决定下一步调用哪个工具**。这已经足够惊人——但仅此而已。**智能来自模型，能力边界全来自 harness**。于是就有了全书的第一句话：

> **agent = LLM + tool use**

先别急着挑这句口号的刺。它描述的是**核心循环的最小闭环**——让循环转起来，少一个零件都不行，所以只保留了两样东西。至于你在经典组件图里见过的 Planning 和 Memory，它们没有被扔掉，只是换了住处。住哪了？往下看。

### 常见疑问：Planning 和 Memory 呢？

翻开任何一本 Agent 教材，组件图几乎都长一个样：**Agent = LLM + Planning + Memory + Tools**。对照上面的口号，Planning 和 Memory 两个组件凭空消失了——是 Pi 没做，还是这句口号偷了懒？

都不是。两个框架回答的是不同的问题：组件图回答"**一个 Agent 系统由什么组成**"，这个口号回答"**让循环转起来，最少的机制是什么**"。前者是能力清单，后者是引擎剖视图。消失的两个组件，在 Pi 里各有承担者：

| 经典组件 | Pi 里的承担者 | 为什么不进核心循环 |
|---|---|---|
| LLM | 模型调用（Provider 层，[08 章](../08-providers-and-models/README.md)） | — |
| Tools | 工具系统（[03 章](../03-tools/README.md)） | — |
| Planning | **模型在循环内自主规划**：每一轮"决定调用哪个工具"就是一次规划动作 | Pi 刻意不内置 planner——任务分解是模型的推理能力；把流程硬编码进框架反而退化成 Workflow（本章开头的三种用法对照） |
| Memory | **短期**：harness 维护的消息数组，每轮重发（[04 章](../04-messages-and-memory/README.md)）；**长期**：会话文件与上下文文件，压缩控制预算（[05](../05-sessions/README.md)、[07](../07-context-and-compaction/README.md)、[04b](../04b-system-prompt/README.md) 章） | 核心只保留"消息数组"这一个最小机制；持久化、压缩、注入是产品层职责，可以各自独立演进 |

所以完整的表述是两层：

```text
最小闭环（核心循环）：   agent = LLM + tool use
完整系统（产品 harness）：+ 消息与记忆 + 上下文管理 + 会话 + 权限 + 事件 ...
```

Pi 的架构选择由此说得通：**Planning 交给模型**（它本来就擅长，硬编码流程只会限制它），**Memory 拆成消息数组、会话、压缩三件机制分别讲清**（[04](../04-messages-and-memory/README.md)、[05](../05-sessions/README.md)、[07](../07-context-and-compaction/README.md) 章）——而不是提供一个名为 memory 的黑盒组件。这也是本课程的立场：凡是被包装成"组件"的能力，都要能拆到机制层看懂。

**一句话总结**：口号没有漏掉 Planning 和 Memory——Planning 是模型在循环里每一步"选哪个工具"时顺便完成的，Memory 则被拆成消息数组、会话、压缩三件机制，由产品层各自承担。

组件的问题说清了，回到主线。

## 二、Pi 的三层架构

既然 harness 决定了能力边界，harness 内部又怎么组织？Pi 的分层可以用三句话概括：

1. **模型无关的核心**（pi-agent-core）：Agent 循环、消息、工具、事件——不依赖具体 UI、具体 Provider、具体文件布局。这一层可以在任何前端、任何模型下复用。
2. **产品环境**（pi-coding-agent）：把核心组装成真正的编码 Agent——工作目录、会话、权限、扩展、上下文文件。
3. **前端消费事件**（TUI / RPC / JSON）：前端是事件流的消费者，不直接操作核心内部状态。

三个理由决定这条边界：

- **可测试性**：核心不依赖 UI 和文件布局，就能用脚本化模型做确定性测试——本课程 Python 实验正是这么做的。
- **可移植性**：同一套核心可以驱动终端、Web、RPC 多个前端，而不改动循环代码。
- **可替换性**：换 Provider、换 UI、换存储，都不需要重写 Agent 逻辑。

### 包拓扑

核心四包：

| 包 | npm 名 | 职责 |
|---|---|---|
| ai | @earendil-works/pi-ai | Provider 适配、统一流式消息、模型目录 |
| agent | @earendil-works/pi-agent-core | Agent 循环、消息、工具、事件（模型无关） |
| coding-agent | @earendil-works/pi-coding-agent | CLI 产品：会话、设置、扩展、SDK/RPC |
| tui | @earendil-works/pi-tui | 终端 UI 组件 |

依赖方向：**ai ← agent ← coding-agent**（tui 被 coding-agent 使用）。另有 client、protocol、server、evals、telemetry 等实验性包，API 可能变化，不构成稳定契约。

### 事件契约是分层的粘合剂

核心和前端之间不靠函数调用，而靠**类型化事件流**：核心每走一步发一个事件（`agent_start`、`turn_start`、`message_start`、`tool_execution_*`……），前端订阅事件并渲染。这个设计在 [06 章](../06-events-and-extensions/README.md) 展开，但它的意义现在就能看到：**前端怎么变，核心不用改**。

## 三、高级能力即工具

Pi 刻意不内置子代理、计划模式、权限弹窗、MCP。为什么？每个团队的工作流不同，内置会限制灵活性。更根本的原因是：**这些能力本质上都是一个工具**。

- `pi-subagents` 用一个 `subagent` 工具实现子代理——子代理本身又是一个独立的 Agent Loop，但对外表现为一次工具调用。
- MCP 适配器把外部服务器的工具接入当前工具池——对外同样是工具。

核心保持小，能力按需生长。这就是 Pi"极致可扩展"的架构来源：**不是功能多，而是扩展面清晰**。

## 当前 Pi 行为

- 固定基线：Pi 0.85.1 @ `d981de1229ef899957bbe968bc8dcda02a21f477`。
- 四种运行模式（TUI / Print / JSON / RPC）共享同一个 Agent 核心，区别只在前端层。
- 核心包仍为 `ai`、`agent`、`tui`、`coding-agent` 四个；实验性包 0.85 新增 `chord`（插件加载/服务声明/对称 RPC/状态复制的应用中立基础，官方标注尚非稳定 API）。
- 分层可从源码目录直接验证：`packages/agent/src/agent-loop.ts` 不 import 任何 Provider 与 UI；`packages/coding-agent/src/` 才出现会话、设置、扩展。

### 源码证据表

| 教学结论 | Pi 路径 / 符号 | 说明 |
|---|---|---|
| 循环不依赖 Provider 与 UI | `packages/agent/src/agent-loop.ts` | 整个文件只消费 `config` 抽象 |
| 事件类型是显式判别联合 | `packages/agent/src/types.ts`（433–446） | `agent_start` 到 `tool_execution_end` 全部列出 |
| 包拓扑 | `packages/` 目录 | 0.85.1 实测：ai/agent/tui/coding-agent + client/protocol/server/evals/telemetry/session-backends/chord |
| 四种运行模式 | `packages/coding-agent/docs/sdk.md`、`rpc.md`、`json.md` | 同一核心、不同前端 |

## 失败与边界实验

分层边界违反时会发生什么？三个思想实验，都可以在源码里验证"为什么做不到"：

1. **让核心直接调用模型 API**：`agent-loop.ts` 没有任何 import 指向 Provider 实现——它只接受调用方注入的流式函数。要换模型，改的是调用方，不是循环。
2. **让前端直接改消息数组**：前端拿到的是事件流和消息副本，没有对核心内部状态的引用。TUI 想高亮某条消息，只能订阅 `message_update`，不能"伸手进去改"。
3. **把权限检查塞进循环里**：循环只在 `executeToolCalls` 处调用工具，不知道权限的存在。硬闸门属于工具的 executor 层——这正是为什么权限策略可以每个项目不同，而循环代码不变。

第三个实验是分层最有力的证据：**边界画在包之间，而不是画在 if 语句里**。

```sh
python3 -m unittest tests.test_13_mini_agent -v
```

## 在 Pi 里怎么操作

```sh
pi                 # 交互式 TUI
pi -p "prompt"     # Print：输出结果后退出
pi --mode json     # JSON：事件流输出到 stdout
pi --mode rpc      # RPC：stdin/stdout 协议
```

## Python 实验

本课程的 [mini_agent.py](../../learn_pi_lab/labs/mini_agent.py) 是同一分层的**单文件缩影**：`messages`/`tools`/`provider`/`events` 对应模型无关的核心，`AgentHarness` 对应有状态的产品包装，`dump_messages`/`load_messages` 对应会话持久化。文件内的小节标题直接标注了每个部分对应 Pi / Tau 的哪个源文件。

Tau（Pi 的 Python 对照实现）用三个包实现同一个分层：`tau_ai`（Provider 层）← `tau_agent`（Agent 核心层）← `tau_coding`（产品层）。它是"同一架构的另一种语言"的直接样本——读它和读 Pi，看到的是同一套设计。

```sh
python3 -m learn_pi_lab lab mini-agent
```

> 这一模块的核心代码在[核心代码导览 · 架构分层](../code-tour.md)有逐段解读。

## 验证方式

```sh
python3 -m unittest tests.test_13_mini_agent -v
python3 scripts/check_course_contract.py
```

## 边界与安全

- 分层是设计边界，不是安全边界：权限、认证、沙箱必须在产品层实现，核心不替你兜底。
- 本课程 Python 教学模型只覆盖可迁移的机制，不复制 Pi 的全部产品细节。

## 回顾

- **agent = LLM + tool use（最小闭环）**：智能来自模型，能力边界全来自 harness；Planning 由模型在循环内承担，Memory 拆成消息数组、会话与压缩，都不是核心循环的黑盒组件。
- **三层架构**：模型无关的核心 / 产品环境 / 前端，事件契约是粘合剂。
- **高级能力即工具**：核心保持小，能力按需生长。

下一章进入最核心的机制——[Agent Loop](../02-agent-loop/README.md)，看循环如何让模型真正"动起来"。
