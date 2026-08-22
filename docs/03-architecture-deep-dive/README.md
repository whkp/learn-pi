# 架构深入解析

本章依据 [Pi 源码映射](../pi-source-map.md) 的固定基线说明当前的包边界。

## 当前包结构

当前 Monorepo 的核心包有四个：

- ai（pi-ai）：模型、Provider 适配和统一的流式消息类型。
- agent（pi-agent-core）：通用 Agent 循环、消息与工具运行时。
- tui（pi-tui）：终端 UI 组件。
- coding-agent（pi-coding-agent）：命令行产品、会话、设置、扩展与 SDK/RPC 集成入口。

0.81 之后新增了 client、protocol、server、evals、telemetry、session-backends 等实验性包，API 可能变化；课程旧图中的 pi-web-ui 不是该基线中的包，不能作为当前架构描述。coding-agent 将产品级能力组合在一起；它不等于所有通用 Agent 行为都位于同一个类。

## 数据流

一个典型请求经过：用户输入 → 会话状态和系统提示 → 模型流 → 工具调用与结果 → 会话 JSONL 条目 → TUI 或 JSON/RPC 输出。每一层都可能失败，因此产品代码应保留取消、限流、权限和会话恢复边界。

自定义 Provider 的当前入口是 `pi.registerProvider()`，配 pi-ai 的 `createProvider` 与 `api`（如 `openAICompletionsApi()`）；`streamSimple` 已移到 `@earendil-works/pi-ai/compat`，属于兼容导出，不要把它当作首选适配接口。

## 课程实验

[agent_loop.py](../../learn_pi_lab/labs/agent_loop.py) 把模型、工具字典与不可变 trace 分离，方便观察循环终止、未知工具和异常工具三种情况。它是教学模型，不使用 Pi 的 TypeScript runtime。

    python3 -m learn_pi_lab lab agent-loop

[mini_agent.py](../../learn_pi_lab/labs/mini_agent.py) 是参照 Tau（Pi 的 Python 对照实现）核心设计的极简 Agent：role 判别消息、`AgentTool` 类型化工具（支持流式进度回调）、`ModelProvider` 协议、事件流（agent_start → turn_start → message → tool → turn_end → agent_end）、`AgentHarness` 订阅（subscribe/prompt）与 append-only JSONL 会话（dump/load）。它是同步版，便于逐行阅读；Tau 的真实循环是 asyncio 版，事件契约相同。

    python3 -m learn_pi_lab lab mini-agent
    python3 -m unittest tests.test_13_mini_agent -v

## 延伸阅读

- [核心模块](../04-core-modules/README.md)
- [扩展系统](../05-extension-system/README.md)
- [会话管理](../08-session-management/README.md)
