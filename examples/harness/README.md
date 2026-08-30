# 构建路线：从裸 API 到完整 Harness

> 机制章节讲"是什么 / 为什么"，这条主线讲"怎么写"。借鉴 learn-agent-the-hard-way 的连续练习方式：从一次裸 API 调用开始，一步步长出工具循环、会话、压缩、事件流——每一步都是独立可运行的代码，且只在上一步之上加一点点。

## 怎么读

- **跟着敲，不要复制粘贴**。每步代码都控制在几十行，卡住了再看参考实现。
- **每一步都能单独跑**：`python3 step_xx/xxx.py`。
- **每步的测试独立**：`python3 -m unittest discover -s examples/harness/step_xx/tests`。
- **离线约束**：主线全程用脚本化 mock provider，不调用真实模型、不访问网络——与课程其余部分一致。

## 主线 12 步

| 步骤 | 主题 | 最小产物 | 学到什么 |
| --- | --- | --- | --- |
| B01 | 裸 API 调用 | `chat_once.py` | 一次调用 = 一次对话 |
| B02 | messages 多轮历史 | `conversation.py` | 模型无状态，历史由 harness 维护 |
| B03 | 流式输出 | `streaming.py` | 增量展示，UI 需要 |
| B04 | 第一个工具 | `read_file` | agent loop 五步闭环 |
| B05 | 工具注册表 | `ToolRegistry` | 加工具 = 加一行 |
| B06 | 工具结果与错误回填 | `ToolResult` | 结果是数据，错误不中断循环 |
| B07 | 权限与工作目录 | allow/ask/deny | 硬闸门不依赖模型 |
| B08 | JSONL 会话 | append-only transcript | 认父不认子、分支 |
| B09 | 上下文预算与压缩 | compaction | 窗口即预算、成对不拆 |
| B10 | 事件流与前端适配 | `subscribe()` | 事件是契约 |
| B11 | Provider / RPC | provider registry + JSONL | 三者分离、分帧 |
| B12 | 组合成可评测 Harness | 完整项目 | 综合应用 |

**进度**：B01-B06 已完成；B07-B12 见 [todo.md](../../todo.md) 的 P1-01。

## 每步的标准结构

```
step_xx_name/
├── README.md        # 本章要解决的问题、核心设计、运行命令、预期输出
├── main.py          # 完整可运行实现（带少量注释）
└── tests/           # 独立单元测试
```

文档明确"上一阶段已有 / 本阶段新增"，解释每个新增函数和字段的**原因**，不把所有说明塞进代码。

## 回到章节

主线的每一步都能回到机制章节对照：B01-B03 ↔ [02 Agent Loop](../../docs/02-agent-loop/README.md)，B04-B06 ↔ [03 工具系统](../../docs/03-tools/README.md)，B07 ↔ [03 工具系统](../../docs/03-tools/README.md) 的权限部分，B08 ↔ [05 会话管理](../../docs/05-sessions/README.md)，B09 ↔ [07 上下文压缩](../../docs/07-context-and-compaction/README.md)，B10 ↔ [06 事件驱动](../../docs/06-events-and-extensions/README.md)。
