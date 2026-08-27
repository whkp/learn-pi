# 架构总览 —— Pi 的分层与核心设计

> Pi 的核心设计可以浓缩成一句话：**agent = LLM + tool use**。模型提供语言与推理，以及"下一步调用哪个工具"的决策；其余一切——消息、工具、权限、上下文、会话——都由包住模型的 harness 提供。因此 Pi 的核心不内置子代理、计划模式、MCP：它们本质上都是一个工具，按需扩展。

## 学习目标

- 理解 Pi 的分层：模型无关的核心 / 产品环境 / 前端，三者通过事件契约解耦。
- 理解"高级能力即工具"这一设计取舍：为什么核心保持小而可扩展。
- 认识 Pi 0.84.2 的包拓扑与依赖方向。

## Pi 的核心设计

### 三句话分层

1. **模型无关的核心**（pi-agent-core）：循环、消息、工具、事件——不依赖具体 UI、具体 Provider、具体文件布局。这一层可以在任何前端、任何模型下复用。
2. **产品环境**（pi-coding-agent）：把核心组装成真正的编码 Agent——工作目录、会话、权限、扩展。
3. **前端消费事件**（TUI / RPC / JSON）：前端是事件流的消费者，不直接操作核心内部状态。

三个理由决定这条边界：**可测试性**（核心不依赖 UI 就能用脚本化模型测）、**可移植性**（同一套核心驱动多个前端）、**可替换性**（换 Provider/UI/存储不重写循环）。

### 包拓扑

核心四包：**ai**（Provider 适配与模型目录）、**agent**（循环/消息/工具/事件）、**coding-agent**（CLI 产品）、**tui**（终端 UI）。依赖方向：ai ← agent ← coding-agent。另有 client、protocol、server 等实验性包，API 可能变化，不构成稳定契约。

### 高级能力即工具

Pi 刻意不内置子代理、计划模式、权限弹窗、MCP——每个团队的工作流不同，内置会限制灵活性。这些能力**本质上都是一个工具**，通过扩展系统按需提供：`pi-subagents` 用一个 `subagent` 工具实现子代理，MCP 适配器把外部工具接入工具池。核心保持小，能力可生长。

### 一个最小 harness 长什么样

本课程的 [mini_agent.py](../../learn_pi_lab/labs/mini_agent.py) 是同一分层的单文件缩影：`messages`/`tools`/`provider`/`events` 对应核心层，`AgentHarness` 对应有状态的产品包装，`dump_messages`/`load_messages` 对应会话持久化。Tau 用三个包（tau_ai ← tau_agent ← tau_coding）实现同一个分层，是"同一架构的另一种语言"的直接样本。

## 当前 Pi 行为

- 固定基线：Pi 0.84.2 @ `914cf1472e715297caa30db4b9535d534a9eb718`。
- 四种运行模式（TUI / Print / JSON / RPC）共享同一个 Agent 核心，区别只在前端层——这正是"前端消费事件"的实际体现。

## 在 Pi 里怎么操作

```sh
pi                 # 交互式 TUI
pi -p "prompt"     # Print：输出结果后退出
pi --mode json     # JSON：事件流输出到 stdout
pi --mode rpc      # RPC：stdin/stdout 协议
```

## Python 实验

```sh
python3 -m learn_pi_lab lab mini-agent   # 单文件缩影：事件流 + JSONL 往返
```

## 验证方式

```sh
python3 -m unittest tests.test_13_mini_agent -v
python3 scripts/check_course_contract.py
```

## 边界与安全

- 分层是设计边界，不是安全边界：权限、认证、沙箱必须在产品层实现，核心不替你兜底。
- 本课程 Python 教学模型只覆盖可迁移的机制，不复制 Pi 的全部产品细节。
