# 工具系统 —— 工具如何被声明、注册与约束

> 模型只能输出文本；工具是它操作世界的唯一通道。工具系统的设计质量，直接决定 Agent 能不能安全、可靠地"干活"。Pi 在工具上投入的设计有三条主线：**类型化定义**（工具 = schema + executor）、**注册表分发**（加工具 = 加一行）、**两道约束**（软约束教会模型，硬闸门拦住模型）。

## 学习目标

- 理解"工具 = schema + executor"的类型化设计，以及为什么模型只能看到 schema。
- 理解软约束与硬闸门的本质区别：一个依赖模型，一个不依赖模型。
- 掌握"先检查、后执行"的安全顺序，理解 bash 为什么是特权工具。

## 一、问题：模型怎么知道它能干什么

模型不知道你的文件系统、你的终端、你的业务。它唯一能"知道"的，是你喂给它的工具信息——而这三样信息决定了它的全部能力：

```
name        —— 工具叫什么
description —— 工具干什么、什么时候用（写得好，模型才不会误用）
parameters  —— 工具收什么参数（JSON Schema，越严格，模型生成的调用越合法）
```

**executor 不在模型视野内**——它是你的进程里的真实执行者，可以注入、替换、mock。这正是可测试性的来源：测试时注入一个假 executor，就能验证"模型要求调工具时，循环是否正确调用"。

## 二、注册表：加工具 = 加一行

没有注册表时，加第二个工具要改两处：工具声明数组加一项、执行分发 switch 加一个 case。第三个工具来的时候，就开始出错。

注册表的做法是**把声明与分发收拢**：

```python
registry = ToolRegistry()
registry.add(read_tool)      # 一行一个工具
registry.add(write_tool)
# 分发：registry.get(name).execute(...)
```

工具的边界还锚定在**工作目录**上：Pi 的 `createCodingTools(cwd)` 必须接收 `cwd`，每个文件/命令工具都以它为边界。工具不是全局单例，而是绑定工作目录的实例——这决定了 Agent 只能操作它被允许操作的项目。

## 三、两道约束：软约束与硬闸门

约束工具行为的机制有两种，性质完全不同：

| 机制 | 问谁 | 强度 | 例子 |
|------|------|------|------|
| 软约束 | 模型愿不愿意 | 因模型而异 | base prompt 写"改文件前必须先读" |
| 硬闸门 | 不问模型意见 | 与模型无关 | 权限系统在 execute 前拦截 |

**软约束的强度取决于你恰好用了哪个模型**——同一条规则，一个模型遵守，另一个可能不遵守。硬闸门不依赖模型，是唯一可以依赖的防线。所以 Pi 的权限检查是硬闸门：模型想干什么是一回事，干不干得成由权限层说了算。

权限检查的典型结论分三档：`allow < ask < deny`。多条规则命中时按档位优先级裁决（**deny 赢 ask，ask 赢 allow**），没有任何规则命中时取默认档。项目信任（project-trust）也是同一套三档（默认 ask）：首次进入未信任目录时询问。

## 四、bash 是特权工具

`bash` 与文件工具不同：一次调用就能执行任意命令、访问整个系统。因此 Pi 给 bash 三道独立防护：

1. **截断**：输出限 2000 行 / 50KB，防止一条命令的输出占满上下文（详见 [07 章](../07-context-and-compaction/README.md) 输入侧防护）；截断后的完整输出保存到临时文件，把路径放进结果——既保护上下文，又不丢信息。
2. **超时**：可选 timeout，防止命令挂死。
3. **权限**：危险命令（如 `rm -rf`）在 execute 前被权限层拦截或转人工确认。

工具执行的失败也有统一约定：**执行失败就抛异常，由循环统一转成带 `isError` 的结构化结果**——而不是在每个工具里手工构造错误对象。

## 当前 Pi 行为

- 默认四个核心工具：`read`、`write`、`edit`、`bash`；`grep`/`find`/`ls` 等只读工具按配置启用。
- 执行结果以 `toolResult` 消息回填（含 `toolCallId` 配对），循环才能继续。
- 工具有 `executionMode` 元数据：任一被调工具声明为 `"sequential"`，本批全部改为串行执行；否则按全局配置并行。并发安全因此成为**工具作者的责任**，不是循环的猜测。
- 0.84.3 起提供可选的 PowerShell 工具（Windows 原生命令执行）；文件探索指南会按工具集改写措辞。
- 模型看到的工具清单由 `toolSnippets` 决定：注册了工具但没给一行描述，模型就"看不见"它。

### 源码证据表

| 教学结论 | Pi 路径 / 符号 | 说明 |
|---|---|---|
| 默认工具集四件套 | `packages/coding-agent/src/core/system-prompt.ts` `DEFAULT_TOOLS` | `read, bash, edit, write` |
| 并行/串行调度 | `packages/agent/src/agent-loop.ts` `executeToolCalls` | `executionMode === "sequential"` 强制整批串行 |
| 参数截断防护 | `packages/agent/src/agent-loop.ts` `failToolCallsFromTruncatedMessage` | `length` 截断时整批失败 |
| 工具创建与 cwd 绑定 | `packages/coding-agent/src/core/tools/index.ts` | `createCodingTools` 需要 cwd |
| 工具清单进提示词 | `packages/coding-agent/src/core/system-prompt.ts` `visibleTools` | 无 snippet 则清单为 `(none)` |

## 失败与边界实验

`lab permissions` 用同一个策略函数走四条路径：

| 场景 | 输入 | 谁拦下 | 结果 |
|---|---|---|---|
| 命令不在白名单 | `rm -rf /` | 硬闸门（命令令牌） | 拒绝，executor 未被调用 |
| 相对路径穿越 | `../../etc/passwd` | 硬闸门（归一化 + 包含检查） | 拒绝 |
| 符号链接逃逸 | 指向边界外的链接 | 硬闸门（`realpath` 后再判断） | 拒绝 |
| 白名单内的合法读 | `ls` + 边界内路径 | — | 执行 |

三条拒绝路径的共同点：**executor 完全没有运行**，因此零副作用。这就是"硬闸门"的定义——检查发生在执行之前，而不是靠事后撤销。

```sh
python3 -m learn_pi_lab lab permissions
python3 -m unittest tests.test_02_tool_permissions -v
```

## 在 Pi 里怎么操作

- 内置工具无需安装；扩展通过 `pi.registerTool(...)` 注册新工具（见 [06 章](../06-events-and-extensions/README.md)）。
- 首次进入未信任的项目目录，pi 会询问是否信任，确认后才加载项目设置与扩展。

## Python 实验

[mini_agent.py](../../learn_pi_lab/labs/mini_agent.py) 的 `AgentTool` 就是"schema + executor"的最小形态：

```python
@dataclass(frozen=True)
class AgentTool:
    name: str
    description: str
    parameters: Mapping[str, object]  # JSON-schema 风格元数据
    execute_fn: ToolExecutor           # (arguments, on_update) -> AgentToolResult
```

[tool_permissions.py](../../learn_pi_lab/labs/tool_permissions.py) 演示硬闸门的检查顺序——**先检查意图与路径、通过后才调用执行器**（测试证明被拒绝的请求永远不触发执行器）：

```python
def evaluate_request(request, policy) -> Decision:
    token, problem = _command_token(request.command)      # 1. 裸命令令牌（无 shell 语法）
    if token not in policy.allowed_commands:              # 2. 命令白名单
        return Decision(False, "command_not_allowed", request)
    for path in request.paths:
        normalized, problem = _normalized_path(path, policy.root)  # 3. 路径归一化与包含检查
        if problem:
            return Decision(False, problem, request)
    return Decision(True, "allowed", normalized_request)
```

Tau 对照：`tau_agent/tools.py` 的 `AgentTool` 字段一致，只是 `execute_fn` 是异步并支持 `on_update` 流式进度回调。

```sh
python3 -m learn_pi_lab lab permissions
```

> 这一模块的核心代码在[核心代码导览 · 工具权限闸门](../code-tour.md)有逐段解读。

## 验证方式

```sh
python3 -m unittest tests.test_02_tool_permissions tests.test_11_projects -v
```

## 边界与安全

- **允许列表不是沙箱**：生产实现还需要操作系统隔离、最小凭据、审计日志、用户确认，以及针对符号链接和竞态条件的防御。
- 不要由字符串拼接生成 shell 命令；命令令牌必须是白名单内的裸命令。
- 工具是隔离边界：executor 抛出的异常应转成结构化错误结果，而不是让循环崩溃。

## 回顾

- **类型化**：工具 = schema + executor，模型只看到 schema。
- **注册表**：加工具 = 加一行；工具绑定 cwd。
- **两道约束**：软约束教会模型（不依赖），硬闸门拦住模型（可依赖）。
- **bash 特权工具**：截断 + 超时 + 权限三道防护。

工具执行的结果要回填给模型——这就是下一章的主题：[消息与记忆](../04-messages-and-memory/README.md)，看对话历史如何组织。
