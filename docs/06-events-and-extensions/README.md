# 事件驱动与扩展 —— 事件即契约

> Pi 最核心的设计是 **"事件是契约"**：Agent 每走一步都发出类型化事件，前端（TUI / JSON / RPC / 自定义）都消费同一个事件流，不直接读取核心内部状态。扩展则通过事件观察甚至改写行为。

## 学习目标

- 理解"事件是契约"：核心发事件、前端渲染，两者解耦。
- 分清两条监听通道：`session.subscribe`（只读观察）与扩展的 `pi.on`（可拦截改写）。
- 理解扩展能注册什么、生命周期事件有哪些，以及事件名的易错点。

## Pi 的核心设计

### 事件是契约

Pi 的事件按生命周期分组：Agent 级（`agent_start`/`agent_end`）、Turn 级（`turn_start`/`turn_end`）、消息级（`message_start`/`message_update`/`message_end`）、工具级（`tool_execution_start`/`tool_execution_update`/`tool_execution_end`）。四个运行模式（TUI/Print/JSON/RPC）都是这些事件的消费者——这正是"核心可移植"的机制保证：**前端怎么变，核心不用改**。

### 两条监听通道的分水岭

Pi 有两套并行的监听机制，共享同一批事件源，但"**Agent 等不等你的 listener**"是分水岭：

| 维度 | `session.subscribe` | 扩展的 `pi.on` |
|------|--------------------|----------------|
| 用途 | 只读观察：日志、UI、统计 | 拦截与改写：权限、输入改写 |
| Agent 是否等待 | 不等（fire-and-forget） | 等（await 处理完再继续） |
| 适用方 | SDK 宿主程序 | TypeScript 扩展 |

只学一套一定会遇到"代码写了却静默不生效"：在 `subscribe` 里想拦截工具调用是做不到的，必须用 `pi.on`。

### 扩展 = 能力按需注入

扩展可以注册工具、命令、快捷键、UI 组件、Provider，以及监听生命周期事件。**高级能力即工具**：子代理、MCP、计划模式都是通过扩展用工具实现的，Pi 核心刻意不内置（见 [01 章](../01-architecture/README.md)）。

### 事件名易错点

- 会话关闭事件是 `session_shutdown`，不是 `session_end`。
- 没有 `settings_change` 事件。
- 工具输入改写是在事件对象上原地进行，不存在返回 `modifiedInput` 的协议。
- 压缩前定制用 `session_before_compact`。

## 当前 Pi 行为

- 扩展事件覆盖：会话生命周期（`session_start`/`session_shutdown`）、上下文注入（`context`）、Provider 请求改写（`before_provider_request` 等）、Agent 循环观察、用户操作观察（`model_select`/`user_bash`）。
- 事件名与 payload 类型以固定基线的 `extensions.md` 与 `src/core/extensions/types.ts` 为准，不要从旧示例复制。

## 在 Pi 里怎么操作

- 安装：`pi install npm:包名` 或 `pi install git:github.com/user/repo`；查看 `pi list`；移除 `pi remove`；单次 `pi -e`。
- 一个真实扩展就是默认导出函数接收 `ExtensionAPI`：`pi.registerTool(helloTool)` 注册工具、`pi.on("session_shutdown", ...)` 订阅生命周期。

### 社区扩展参考

Pi 生态有 5500+ 包，生态地图见 [awesome-pi](https://github.com/BubblePtr/awesome-pi)。高 star 代表（star 以调研时为准）：

- **子代理**：pi-subagents（3255★，官方异步子代理）、@tintinweb/pi-subagents（943★）
- **记忆**：pi-hermes-memory（366★，持久记忆+会话搜索+密钥扫描）
- **手机连接**：pi-telegram（281★，Telegram DM 桥）、pi-web（593★，手机浏览器监督）
- **Web 访问**：pi-web-access（1190★，多 Provider 降级链）
- **上下文**：pi-context-prune（214★，工具调用树剪枝）
- **精读推荐**：pi-llama（HuggingFace 官方，单文件演示 registerProvider）、narumiruna/pi-extensions（27 包 monorepo，沉淀扩展工程约定）

> 国内渠道：飞书有 pi-feishu 系列（官方 Bot API + WebSocket 长连接，无需公网 IP）；微信无（无官方 Bot API，个人号自动化有封号风险）；钉钉仅雏形。star 不代表质量，安装前先读源码确认权限与网络行为。

## Python 实验

[extension_events.py](../../learn_pi_lab/labs/extension_events.py) 是课程自己的事件总线，演示按注册顺序派发、异常隔离（普通 `Exception` 变成数据）、幂等退订与深度快照：

```python
bus = LessonEventBus()
bus.on("turn", lambda payload: "first")              # 返回 Subscription
outcomes = bus.emit("turn", {"lesson": "events"})    # 每个 handler 一个 EventOutcome
```

它不是 Pi ExtensionAPI 的 Python 绑定——Pi 扩展是 TypeScript 代码。Tau 的 `tau_agent/harness.py` 的 `subscribe(listener)` 返回退订函数，语义与本课程一致。

```sh
python3 -m learn_pi_lab lab events
```

## 验证方式

```sh
python3 -m unittest tests.test_07_extension_events -v
```

## 边界与安全

- 事件名、payload、返回约定以固定基线（0.84.2）为准，不要从旧 README 复制。
- 扩展应验证所有外部输入、限制可执行操作，把异常变成明确的用户反馈或日志。
