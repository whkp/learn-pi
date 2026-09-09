# 实战与评测 —— 综合应用与验证

> 前面十章讲机制，这一章把它们组装起来。四个离线 mini-project 训练可迁移的 Agent 工程边界，测试与评测构成同一条质量链：能运行不等于可维护，功能正确、工具安全、结果质量是三个不同的评测维度。

## 学习目标

- 综合运用 Agent 循环、工具边界、会话、协议等机制解决具体问题。
- 区分功能正确性、工具安全性与结果质量三种评测维度。
- 理解确定性测试不能证明模型在开放式任务上永远正确。

## 一、问题：怎么知道一个 Agent 是"好的"

"能运行"是最低标准。可维护的 Agent 需要回答三个不同的问题：

| 维度 | 问题 | 手段 |
|------|------|------|
| 功能正确性 | 代码逻辑对不对 | 确定性单元测试 |
| 工具安全性 | 会不会越权/破坏 | 允许列表、路径边界、权限测试 |
| 结果质量 | 模型产出好不好 | 固定样本集、人工复核、回归门槛 |

确定性测试（本课程的主线）解决前两个；结果质量需要生产级评测（固定样本集、人工复核、失败分类）——**确定性单元测试不能证明模型在开放式任务上永远正确**。

## 二、四个项目：每个训练一个工程能力

| 项目 | 训练的机制 | 对应章节 |
|------|-----------|---------|
| Session Inspector | JSONL 只读解析、角色统计 | [05 章](../05-sessions/README.md) |
| Safe Review Runner | 只读意图 + 路径边界（硬闸门） | [03 章](../03-tools/README.md) |
| CI Review Pipeline | 多检查收敛为稳定报告 | 本章 |
| RPC Console | JSONL 分帧 + 方法白名单 | [10 章](../10-protocol-and-integration/README.md) |

### Session Inspector：只读解析

[inspect_session_jsonl](../../projects/session_inspector.py) 逐行读 JSONL，用 `Counter` 统计角色、数 `type == "compaction"` 记录，返回不可变的 `SessionReport`。它刻意**不执行记录内容**——会话文件里的命令输出只是数据，不是指令。

### Safe Review Runner：意图 + 路径双重闸门

[review_request](../../projects/safe_review_runner.py) 的检查顺序——意图白名单 → 路径边界：

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

### CI Review Pipeline：稳定报告

[build_review_report](../../projects/ci_review_pipeline.py) 把三项检查（课程契约、Markdown 链接、单元测试）收敛为有序报告，CI 可稳定解析；失败时给出可读原因，而不是崩溃堆栈。

### RPC Console：白名单接口

[handle_request](../../projects/rpc_console.py) 用课程 JSONL 编解码器解析单行请求，只响应 `ping`，返回 JSON——不创建子进程、不执行命令。演示"stdout 是协议、方法白名单、错误是数据"三个原则。

## 当前 Pi 行为

- Pi 仓库用 `npm run check`（lint + 类型检查 + 依赖检查）与 `./test.sh`（跳过依赖 LLM 的测试）验证。
- 迁移思路到 Pi 时：用 TypeScript 和当前 ExtensionAPI / SDK / RPC 文档重新实现，并补上认证、权限、取消、日志脱敏与端到端测试。
- Pi 仓库自带 `evals` 包（实验性），说明"评测与运行时分离"是官方方向：评测不是测试的附属品，而是独立的一层。
- 0.85.1 新增 GPT-6 Astra 一类新模型时，`models.json` 目录与评测基线需要同步更新——模型升级对评测结果的影响是这个章节存在的理由。

### 源码证据表

| 教学结论 | Pi 路径 / 符号 | 说明 |
|---|---|---|
| 质量门槛命令 | `npm run check`、`./test.sh` | Pi 仓库验证入口 |
| 评测独立成包 | `packages/evals/`（实验性） | 评测与运行时分离 |
| 离线评测教学模型 | `learn_pi_lab/labs/` 各 lab | 全部不访问网络 |
| 项目级测试 | `learn_pi_lab` + `tests/` | 108+ 单元测试 |

## 失败与边界实验

评测本身也会失败——而且是安静地失败。三类最常见：

1. **评测过拟合。** 任务样例全部来自同一个 fixture，模型学会了"这个仓库的套路"，评测 100 分，真实任务一塌糊涂。修法：fixture 至少按难度和错误类型分层（`examples/fixtures/` 的设计初衷）。
2. **把人工评分伪装成确定性测试。** "看起来更好"不是断言。修法：人工评分单独成列，永不进入 CI 门槛。
3. **安全回归没有门槛。** 功能正确性 100%，但某次改动让工具能写到边界外——评测只测了"做对了"，没测"没越权"。修法：禁止越权、禁止未授权写入、工具调用必须在允许列表，这三条是**硬门槛**，与功能正确性并列。

```sh
python3 -m unittest discover -s tests -v
python3 -m learn_pi_lab lab mini-agent
```

## 在 Pi 里怎么操作

```sh
python3 -m unittest discover -s tests -v          # 全部测试
python3 scripts/check_course_contract.py          # 课程契约（基线 + 章节结构）
python3 scripts/check_markdown_links.py           # 本地链接完整性
```

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
- 迁移到 Pi 前，用 TypeScript 重新实现并补齐生产级边界（认证、权限、取消、脱敏、端到端测试）。

## 回顾

- **评测三层**：功能正确性、工具安全性、结果质量——确定性测试覆盖前两层。
- **四个项目**：Session Inspector（只读解析）、Safe Review Runner（意图+路径闸门）、CI Review Pipeline（稳定报告）、RPC Console（白名单接口）。
- **质量链**：行为测试 + 文档契约 + 集成项目，缺一不可。

课程到此结束。回到 [课程地图](../00-course-map.md) 或 [源码映射](../pi-source-map.md)，把每一章的机制放到 Pi 的真实源码里对照验证——**这不是"逐行复制源码"，这是"掌握真正重要的设计，然后自己重建它"**。
