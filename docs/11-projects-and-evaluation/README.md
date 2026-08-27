# 实战与评测 —— 综合应用与验证

> 前面十章讲机制，这一章把它们组装起来：四个离线 mini-project 训练可迁移的 Agent 工程边界，测试与评测构成同一条质量链。

## 学习目标

- 综合运用 Agent 循环、工具边界、会话、协议等机制解决具体问题。
- 区分功能正确性、工具安全性与结果质量三种评测维度。
- 理解确定性测试不能证明模型在开放式任务上永远正确。

## Pi 的核心设计：评测是分层的

| 维度 | 问题 | 手段 |
|------|------|------|
| 功能正确性 | 代码逻辑对不对 | 确定性单元测试 |
| 工具安全性 | 会不会越权/破坏 | 允许列表、路径边界、权限测试 |
| 结果质量 | 模型产出好不好 | 固定样本集、人工复核、回归门槛 |

一个"能运行"的 Agent 不等于"可维护"：行为测试、文档契约、集成项目缺一不可。四个项目各自训练一个具体的工程能力：

| 项目 | 训练的机制 | 对应章节 |
|------|-----------|---------|
| Session Inspector | JSONL 只读解析、角色统计 | [05 章](../05-sessions/README.md) |
| Safe Review Runner | 只读意图 + 路径边界（硬闸门） | [03 章](../03-tools/README.md) |
| CI Review Pipeline | 多检查收敛为稳定报告 | 本章 |
| RPC Console | JSONL 分帧 + 方法白名单 | [10 章](../10-protocol-and-integration/README.md) |

## 当前 Pi 行为

- Pi 仓库用 `npm run check`（lint + 类型检查 + 依赖检查）与 `./test.sh`（跳过依赖 LLM 的测试）验证。
- 迁移思路到 Pi 时：用 TypeScript 和当前 ExtensionAPI / SDK / RPC 文档重新实现，并补上认证、权限、取消、日志脱敏与端到端测试。

## 在 Pi 里怎么操作

```sh
python3 -m unittest discover -s tests -v          # 全部测试
python3 scripts/check_course_contract.py          # 课程契约（基线 + 章节结构）
python3 scripts/check_markdown_links.py           # 本地链接完整性
```

## Python 实验：四个项目的实现要点

**Session Inspector**（[inspect_session_jsonl](../../projects/session_inspector.py)）逐行读 JSONL，用 `Counter` 统计角色、数 `type == "compaction"` 记录，返回不可变的 `SessionReport`。它刻意**不执行记录内容**——会话文件里的命令输出只是数据，不是指令。

**Safe Review Runner**（[review_request](../../projects/safe_review_runner.py)）的检查顺序——意图白名单 → 路径边界：

```python
def review_request(policy, intent, target) -> ReviewDecision:
    if intent not in {"read", "search", "list"}:              # 1. 只读意图白名单
        return ReviewDecision(False, None, "intent is not read-only")
    candidate = PurePosixPath(target)
    if candidate.is_absolute() or ".." in candidate.parts:    # 2. 拒绝绝对路径与父目录跳转
        return ReviewDecision(False, None, "target escapes the review root")
    return ReviewDecision(True, str(policy.root / Path(*candidate.parts)), "allowed")
```

与 [03 章](../03-tools/README.md) 的 tool_permissions 同一思路：先检查、后放行，拒绝的请求不产生任何副作用。

**CI Review Pipeline**（[build_review_report](../../projects/ci_review_pipeline.py)）把三项检查收敛为有序报告，CI 可稳定解析；失败时给出可读原因，而不是崩溃堆栈。

**RPC Console**（[handle_request](../../projects/rpc_console.py)）只响应 `ping`，返回 JSON——演示"stdout 是协议、方法白名单、错误是数据"。

## Python 实验

```sh
python3 -m unittest tests.test_11_projects -v
```

## 验证方式

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_course_contract.py
python3 scripts/check_markdown_links.py
```

三条命令都输出 `OK` / 全绿即视为通过。

## 边界与安全

- 确定性单元测试不能证明模型在开放式任务上永远正确；生产评测还应包含固定样本集、人工复核、失败分类与回归门槛。
- 日志策略不得泄露敏感数据；本课程四个项目不访问网络、不调用模型、不执行 shell 命令。
