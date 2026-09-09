# 术语表

按主题分组的课程术语。每条给出**课程内的定义**，并链接到首次展开讨论的章节。带「元」字样的条目描述课程本身的约定，不是 Pi 的概念。

## 课程约定（元术语）

### Pi 基线

课程资料所依据的 Pi 版本与提交。准确值记录在 [Pi 源码映射](pi-source-map.md) 中。所有「当前 Pi 行为」断言都锚定在这个固定基线上，基线升级必须同步更新映射、章节与契约测试。

### 当前 Pi 行为

由固定 Pi 基线源码支持的行为描述；它与课堂中的简化示例分开表述。一个断言只有能在基线源码里指出符号或行号，才能写进「当前 Pi 行为」小节。

### Python 教学模型

本仓库 `learn_pi_lab` 中只使用标准库的离线实验代码。它说明机制，不是 Pi 的生产实现或兼容 API。

### 主章节

课程地图中明确声明、并必须具有统一教学结构的 Markdown 章节。契约要求的五个小节见 [检查脚本](../scripts/check_course_contract.py)。

## 架构

### harness

模型之外的一切：工具、权限、消息数组、会话、压缩、技能加载。**智能来自模型，能力边界全来自 harness**，这是全书贯穿始终的核心命题（与「最小闭环」口号的对照见下一条）。见 [01 章](01-architecture/README.md)。

### agent = LLM + tool use

**核心循环的最小闭环**，不是 Agent 系统的能力全集：模型只负责「决定下一步调用哪个工具」，其余全部由 harness 供给。经典组件图（Agent = LLM + Planning + Memory + Tools）中的 Planning 由模型在循环内自主承担，Memory 拆成消息数组、会话与压缩三件机制，都不是核心循环的黑盒组件。对照表见 [01 章](01-architecture/README.md)。

### 三层架构

模型无关的核心（pi-agent-core）→ 产品环境（pi-coding-agent）→ 前端。层与层之间靠类型化事件流解耦，不靠函数调用。见 [01 章](01-architecture/README.md)。

### 高级能力即工具

子代理、MCP、计划模式都不是核心内置，而是「一个工具」：对模型来说它们和读文件没有区别。核心保持小，能力按需生长。见 [01 章](01-architecture/README.md)。

## Agent Loop

### Agent Loop

驱动模型工作的循环：发请求 → 解析响应 → 执行工具 → 回填结果 → 再发请求，直到满足终止条件。见 [02 章](02-agent-loop/README.md)。

### Trace 与 Turn

Trace 是一次完整任务，Turn 是循环里的一次模型调用。一个 Trace 包含多个 Turn；工具调用会让一个 Turn 之间再插入执行步骤。见 [02 章](02-agent-loop/README.md)。

### stopReason

模型 API 返回的重要状态（如 `end_turn`、`tool_use`、`length`）。**它不是唯一的终止信号**：`stopReason=length` 但带工具调用时，循环会继续执行工具。见 [02 章](02-agent-loop/README.md)。

### steering / follow-up

在 Agent 工作期间插入的用户指令（转向）与排队消息（跟进）。它们影响循环的继续条件，而不是等本轮结束才生效。见 [02 章](02-agent-loop/README.md)。

## 工具

### schema + executor

工具的两次声明：schema 告诉模型怎么调，executor 定义 harness 怎么执行。两者分离，模型永远不直接执行代码。见 [03 章](03-tools/README.md)。

### 注册表分发

模型返回工具名与参数后，harness 在注册表里查到对应 executor 再执行；未知工具返回错误而不是崩溃。见 [03 章](03-tools/README.md)。

### 软约束与硬闸门

软约束写进提示词（模型可以违反）；硬闸门在执行前强制检查（违反即拒绝）。安全设计的关键是把重要边界放进硬闸门。见 [03 章](03-tools/README.md)。

### bash 特权工具

能执行任意命令的工具。正因为它是最高风险面，Pi 用它示范权限设计：allow / ask / deny 三态。见 [03 章](03-tools/README.md)。

## 消息与提示词

### 判别联合（role）

消息的类型由 `role` 字段判别：`user`、`assistant`、`toolResult` 等。Python 教学模型用 dataclass 的默认字段实现。见 [04 章](04-messages-and-memory/README.md)。

### 工具结果成对回填

`toolCall` 与 `toolResult` 必须成对出现：模型每发起一次调用，harness 必须回填一条结果，否则下轮请求不合法。见 [04 章](04-messages-and-memory/README.md)。

### 系统提示词

每轮请求的第一条 system 消息，由 harness 五段拼装：人设 → 追加规则 → 项目上下文 → 技能摘要 → 工作目录。见 [04b 章](04b-system-prompt/README.md)。

### customPrompt 路径

传入自定义人设后走的简化拼装分支：**跳过**工具清单、指南和文档指针。想「只换人设、保留编程助手行为」应走追加规则而不是它。见 [04b 章](04b-system-prompt/README.md)。

### 三级回退链

人设来源的优先级：代码层 `systemPromptOverride` > 文件层 `SYSTEM.md`（项目级需信任）> 硬编码兜底。见 [04b 章](04b-system-prompt/README.md)。

### 项目信任

项目级 `.pi/SYSTEM.md`、`APPEND_SYSTEM.md` 只有在 `isProjectTrusted()` 为真时生效。防止克隆来的仓库悄悄改写 Agent 人设。见 [04b 章](04b-system-prompt/README.md)。

### 技能（skill）

放在 skills 目录里的可发现能力，其摘要会被注入提示词。注入前提是工具集里有能读技能文件的 `read` 或 `bash`（0.85.1 起放宽，0.84.2 只认 `read`）。见 [04b 章](04b-system-prompt/README.md)。

### 上下文文件

从 `cwd` 向上逐级发现的 `AGENTS.md` / `CLAUDE.md`，注入为 `<project_context>`。不创建文件即为空，无需显式关闭。见 [04b 章](04b-system-prompt/README.md)。

## 会话与状态

### JSONL v3

会话的存储格式：每行一个 JSON 记录、append-only。只追加意味着崩溃恢复简单——最多丢最后一行，不会损坏已有历史。见 [05 章](05-sessions/README.md)。

### 认父不认子

会话树的构建规则：每条记录只记录父指针，读取时由子找父重建整棵树。这让分支成为「从某个节点重新开始」的自然结果，而不是特殊操作。见 [05 章](05-sessions/README.md)。

### append-only

只追加、不修改。会话、日志都遵循这一原则；修改历史的操作（如压缩）实际是追加新记录而非改写旧记录。见 [05 章](05-sessions/README.md)。

## 事件与扩展

### 事件即契约

核心与前端之间不靠函数调用，而靠类型化事件流。事件名和 payload 是公开契约，前端怎么变核心都不用改。见 [06 章](06-events-and-extensions/README.md)。

### subscribe 与 pi.on 的分水岭

`session.subscribe` 消费事件（只读观察）；`pi.on` 是扩展注册钩子（可返回值改变行为）。前者是消费者 API，后者是扩展 API。见 [06 章](06-events-and-extensions/README.md)。

### 扩展钩子

扩展在特定时机介入的回调，如 `before_agent_start`（改写本轮系统提示词）、`session_before_compact`（压缩边界）。handler 的返回值就是介入手段。见 [06 章](06-events-and-extensions/README.md) 与 [04b 章](04b-system-prompt/README.md)。

### session_shutdown

扩展收到的关闭事件。基线核实：没有 `settings_change`，也不是 `session_end`。见 [06 章](06-events-and-extensions/README.md)。

## 上下文管理

### 上下文压缩（compaction）

对话超过预算时，让模型总结自己的历史，用摘要替换旧消息。压缩后工具调用必须成对完整，否则下轮请求不合法。见 [07 章](07-context-and-compaction/README.md)。

### 窗口即预算

模型上下文窗口是硬资源。harness 的职责是估算占用、在逼近上限前触发压缩，而不是等 API 报错。见 [07 章](07-context-and-compaction/README.md)。

### 压缩边界

扩展介入压缩的时机（`session_before_compact`）。可以在此保护敏感信息不被写进摘要。见 [07 章](07-context-and-compaction/README.md)。

## Provider 与可靠性

### Provider 三层分离

元数据（模型叫什么、多大窗口）、协议（怎么发请求）、认证（用什么密钥）三者分离。换模型不换代码。见 [08 章](08-providers-and-models/README.md)。

### models.json

模型目录的配置文件：声明 Provider、模型与认证方式。`pi.registerProvider()` 是自定义 Provider 的入口。见 [08 章](08-providers-and-models/README.md)。

### 先分类再重试

错误处理的顺序：先判断错误类型（可重试/不可重试），再决定策略。对 429 重试有意义，对 401 重试只是浪费。见 [09 章](09-reliability/README.md)。

### 指数退避必封顶

重试间隔指数增长，但必须有上限，否则一次长时间故障会把调用挂死。见 [09 章](09-reliability/README.md)。

### 错误隔离

一个工具失败不应拖垮整个 Agent：错误要被捕获、分类、回填给模型，让模型决定下一步。见 [09 章](09-reliability/README.md)。

## 集成

### stdout 是协议

`pi --mode json` / `--mode rpc` 把事件流写到 stdout。消费方与 Agent 的全部交互就是这个流。见 [10 章](10-protocol-and-integration/README.md)。

### 粘包与半包

JSONL 分帧读取的两个经典问题：一次读到多行（粘包）、一次只读到半行（半包）。正确做法是按行缓冲，而不是按块解析。见 [10 章](10-protocol-and-integration/README.md)。

### RPC

stdin/stdout 上的请求-响应协议，让外部进程（编辑器、IDE）驱动 Agent。见 [10 章](10-protocol-and-integration/README.md)。

## 参考实现

### Tau

Pi 的 Python 对照实现（tau_agent / tau_ai / tau_coding），镜像同一套设计。它是「同一架构的另一种语言」的样本，**不是** Pi SDK。见 [01 章](01-architecture/README.md)。

### mini_agent.py

课程的单文件缩影：`messages`/`tools`/`provider`/`events` 对应核心，`AgentHarness` 对应产品包装。文件内小节标题标注了对应 Pi/Tau 的源文件。见 [01 章](01-architecture/README.md)。

返回 [课程地图](00-course-map.md)。
