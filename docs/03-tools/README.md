# 工具系统 —— 工具如何被声明、注册与约束

> 工具是 Agent 操作世界的唯一通道，也是 Pi 设计投入最多的地方。核心设计有三条：**工具 = schema + executor**（类型化，不是魔法字符串）；**注册表分发**（加工具 = 加一行）；**两道约束**——软约束教会模型，硬闸门拦住模型。

## 学习目标

- 理解"工具 = schema + executor"的类型化设计。
- 理解软约束与硬闸门的本质区别：一个依赖模型，一个不依赖模型。
- 掌握"先检查、后执行"的安全顺序。

## Pi 的核心设计

### 工具 = schema + executor

模型看到的工具信息只有三样：`name`、`description`、`parameters`（JSON Schema）。description 写得越具体，模型越不会误用；executor 是真正的执行者，可以注入、替换、mock——这正是可测试性的来源。工具执行结果以 `toolResult` 消息结构化回填（含 `toolCallId` 与调用配对），循环才能继续。

### 软约束 vs 硬闸门

约束工具行为的机制有两种，性质完全不同：

| 机制 | 问谁 | 强度 | 例子 |
|------|------|------|------|
| 软约束 | 模型愿不愿意 | 因模型而异 | base prompt 写"改文件前必须先读" |
| 硬闸门 | 不问模型意见 | 与模型无关 | 权限系统在 execute 前拦截 |

软约束的强度取决于你恰好用了哪个模型——同一条规则，一个模型遵守，另一个可能不遵守。**硬闸门不依赖模型，是唯一可以依赖的防线**。权限检查的典型结论分三档：`allow < ask < deny`，多条规则命中时按档位优先级裁决（deny 赢 ask，ask 赢 allow），无规则命中时取默认档。

### bash 是特权工具

`bash` 一次调用就能访问整个系统，因此 Pi 给它三道独立防护：**截断**（输出限 2000 行/50KB，防占满上下文）、**超时**（可选）、**权限**（危险命令执行前拦截或转人工）。截断的完整输出保存到临时文件并把路径放进结果——既保护上下文，又不丢信息。

### 工具的边界锚定在 cwd

Pi 的 `createCodingTools(cwd)` 必须接收工作目录——每个文件/命令工具都以它为边界。工具不是全局单例，而是绑定工作目录的实例。

## 当前 Pi 行为

- 默认四个核心工具：`read`、`write`、`edit`、`bash`；`grep`/`find`/`ls` 等只读工具按配置启用。
- 执行失败由循环统一转成带 `isError` 的结构化结果，不中断循环。
- 项目信任（project-trust）也是三档：`allow`/`ask`/`deny`（默认 ask）。

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
    token, problem = _command_token(request.command)      # 1. 裸命令令牌
    if token not in policy.allowed_commands:              # 2. 命令白名单
        return Decision(False, "command_not_allowed", request)
    for path in request.paths:
        normalized, problem = _normalized_path(path, policy.root)  # 3. 路径归一化与包含检查
        if problem:
            return Decision(False, problem, request)
    return Decision(True, "allowed", normalized_request)
```

Tau 对照：`tau_agent/tools.py` 的 `AgentTool` 字段一致，只是 `execute_fn` 是异步并支持 `on_update` 流式进度。

```sh
python3 -m learn_pi_lab lab permissions
```

## 验证方式

```sh
python3 -m unittest tests.test_02_tool_permissions tests.test_11_projects -v
```

## 边界与安全

- **允许列表不是沙箱**：生产实现还需要操作系统隔离、最小凭据、审计日志、用户确认，以及针对符号链接和竞态条件的防御。
- 不要由字符串拼接生成 shell 命令；命令令牌必须是白名单内的裸命令。
