# 工具系统 —— 工具如何被声明、注册与约束

> 模型只能输出文本；工具是它操作世界的唯一通道。这一章拆解工具系统"如何实现"：工具层的类型化定义、注册表层的分发、权限层的执行前检查，以及 bash 这类特权工具的特殊处理。

## 学习目标

- 理解"工具 = schema + executor"的类型化设计。
- 掌握注册表分发：加一个新工具只需要注册一行。
- 分清软约束与硬闸门：提示词教会模型，权限系统拦住模型。
- 理解 bash 工具为什么是特权工具：需要截断、超时、权限三道闸。
- 读 Pi 0.84.2 的工具实现，并对照本课程的 Python 教学模型。

## 机制：工具层、注册表层与权限层

工具系统分三层，职责各自独立：

1. **工具层**：每个工具是一个 `{ name, description, parameters(schema), execute }` 的接口。schema 告诉模型能收什么参数；execute 是真正的执行者。
2. **注册表层**：用一个注册表把声明与分发收拢——工具接口 + 注册表，加工具 = 加一行，而不是在循环里加 case。
3. **权限层**：在 executor 被调用之前插入检查，见下文"软约束与硬闸门"。

### 工具层：schema 是模型看到的全部

模型看到的工具信息只有三样：`name`、`description`、`parameters`（JSON Schema）。description 写得越具体，模型越不会误用；parameters 定义越严格，模型生成的调用越合法。executor 不在模型视野内——它属于你的进程。

### 注册表层：加工具 = 加一行

没有注册表时，加第二个工具要改两处（tools 数组加声明、execute 的 switch 加 case），第三个工具来的时候就开始出错。注册表的做法：

```python
registry = ToolRegistry()
registry.add(read_tool)      # 一行一个工具
registry.add(write_tool)
# 分发：registry.get(name).execute(...)
```

### 软约束与硬闸门

约束工具行为的机制有两种，性质不同：

| 机制 | 问谁 | 强度 | 例子 |
|------|------|------|------|
| 软约束 | 模型愿不愿意 | 因模型而异 | base prompt 里写"改文件前必须先读" |
| 硬闸门 | 不问模型意见 | 与模型无关 | 权限系统在 execute 前拦截 |

软约束的强度取决于你恰好用了哪个模型——同一条规则，一个模型遵守，另一个模型可能不遵守。硬闸门不依赖模型，是唯一可以依赖的防线。权限检查的典型结论分三档：`allow < ask < deny`，多条规则命中时按档位优先级裁决（deny 优先于 ask，ask 优先于 allow），没有任何规则命中时取默认档。

### bash 为什么是特权工具

`bash` 与文件工具不同：它一次调用就能执行任意命令、访问整个系统。因此 bash 工具至少需要三道独立防护：

1. **截断**：输出限行数 + 限字节，防止一条命令的输出占满上下文（见 [07 章](../07-context-and-compaction/README.md) 输入侧防护）。
2. **超时**：默认无超时，但允许调用方指定 timeout，防止命令挂死。
3. **权限**：危险命令（rm -rf 等）在 execute 前被权限层拦截或转人工确认。

## Pi 源码怎么实现（0.84.2）

### 工具定义：AgentTool

工具接口在 `packages/agent/src/types.ts`：

```typescript
// packages/agent/src/types.ts（Pi 0.84.2，节选）
export interface AgentTool<TParameters extends TSchema = TSchema, TDetails = any>
  extends Tool<TParameters> {
  /** Human-readable label for UI display. */
  label: string;
  /** Execute the tool call. Throw on failure instead of encoding errors in content. */
  execute: (
    toolCallId: string,
    params: Static<TParameters>,
    signal?: AbortSignal,
    onUpdate?: AgentToolUpdateCallback<TDetails>,
  ) => Promise<AgentToolResult<TDetails>>;
  /** "sequential": 必须与其他调用串行；"parallel": 可并发。 */
  executionMode?: ToolExecutionMode;
}
```

注意两点：

- **execute 的四个参数**：`toolCallId`（与结果配对）、`params`（已按 schema 校验）、`signal`（取消）、`onUpdate`（流式进度）。前两个是工具的核心契约，后两个是 harness 的支撑。
- **"Throw on failure"**：Pi 约定工具执行失败就抛异常，由循环统一转成错误结果——而不是在每个工具里手工构造错误对象。

### 内置工具：bash 的截断与 schema

内置工具在 `packages/agent/src/harness/tools/`，bash 的定义最能说明"特权工具"的设计：

```typescript
// packages/agent/src/harness/tools/bash.ts（Pi 0.84.2，节选）
const bashSchema = Type.Object({
  command: Type.String({ description: "Bash command to execute" }),
  timeout: Type.Optional(Type.Number({ description: "Timeout in seconds (optional)" })),
});

description: `Execute a bash command in the current working directory.
Output is truncated to last ${DEFAULT_MAX_LINES} lines or ${DEFAULT_MAX_BYTES / 1024}KB
(whichever is hit first). If truncated, full output is saved to a temp file. ...`,
```

截断常量在 `packages/agent/src/harness/utils/truncate.ts`：

```typescript
export const DEFAULT_MAX_LINES = 2000;
export const DEFAULT_MAX_BYTES = 50 * 1024; // 50KB
```

要点：

- description 里**主动声明截断行为**（"截断到最后 2000 行或 50KB"），让模型知道输出可能不完整。
- 截断后的完整输出**保存到临时文件**，把路径放进工具结果——既保护上下文，又不丢信息。
- bash 执行用 `onUpdate` 节流推送实时输出（`BASH_UPDATE_THROTTLE_MS`），UI 能看到命令在跑，而不是干等。

### 组装：createCodingTools

`packages/coding-agent/src/core/tools/index.ts` 的 `createCodingTools` 把内置工具组装成产品工具集——它**必须接收 `cwd`**，因为每个文件/命令工具都以它为边界：

```typescript
// packages/coding-agent/src/core/tools/index.ts（Pi 0.84.2，原文）
export function createCodingTools(cwd: string, options?: ToolsOptions): Tool[] {
  return [
    createReadTool(cwd, options?.read),
    createBashTool(cwd, options?.bash),
    createEditTool(cwd, options?.edit),
    createWriteTool(cwd, options?.write),
  ];
}

export function createReadOnlyTools(cwd: string, options?: ToolsOptions): Tool[] {
  return [
    createReadTool(cwd, options?.read),
    createGrepTool(cwd, options?.grep),
    createFindTool(cwd, options?.find),
    createLsTool(cwd, options?.ls),
  ];
}
```

注意每个 `createXxxTool` 都接收 `cwd`——工具不是全局单例，而是**绑定工作目录的实例**。这就是课程 [10 章](../10-protocol-and-integration/README.md) 说的“createCodingTools 需要该边界”的源码根据。

## 当前 Pi 行为

- 默认四个核心工具：`read`、`write`、`edit`、`bash`；`grep`、`find`、`ls` 等只读工具按配置启用。
- 工具 schema 通过 `parameters` 传给 Provider，模型按 schema 生成调用。
- 执行结果以 `toolResult` 消息回填；执行失败由循环统一转成带 `isError` 的结构化结果。
- 项目信任（project-trust）本身也是三档：`allow` / `ask` / `deny`（默认 ask），首次在未信任目录运行时询问。

## 在 Pi 里怎么操作

- 内置工具无需安装；扩展通过 `pi.registerTool(...)` 注册新工具（见 [06 章](../06-events-and-extensions/README.md)）。
- `pi install npm:包名` 安装带工具的扩展后，重启或 `/reload` 生效。
- 首次进入未信任的项目目录，pi 会询问是否信任，确认后才加载项目设置与扩展。

## Python 对照

[mini_agent.py](../../learn_pi_lab/labs/mini_agent.py) 的 `AgentTool` 就是"schema + executor"的最小形态：

```python
@dataclass(frozen=True)
class AgentTool:
    name: str
    description: str
    parameters: Mapping[str, object]  # JSON-schema 风格元数据
    execute_fn: ToolExecutor           # Callable[[arguments, on_update], AgentToolResult]
```

[tool_permissions.py](../../learn_pi_lab/labs/tool_permissions.py) 演示**硬闸门**：`evaluate_request` 先校验命令令牌与路径，`dispatch_if_allowed` 通过后才调用注入的 executor——被拒绝的请求永远不会触发执行器（测试已证明）。它的策略对应权限层的三档设计：白名单命令直接 `allow`，非白名单命令 `deny`，所有路径都必须在策略根目录内。完整的权限检查顺序是：命令令牌（裸命令、无 shell 语法）→ 命令白名单 → 路径归一化 → 路径包含检查。

```python
# tool_permissions.py 的检查顺序（简化）
def evaluate_request(request, policy) -> Decision:
    token, problem = _command_token(request.command)      # 1. 裸命令令牌
    if problem: return Decision(False, problem, request)
    if token not in policy.allowed_commands:              # 2. 白名单
        return Decision(False, "command_not_allowed", request)
    for path in request.paths:
        normalized, problem = _normalized_path(path, policy.root)  # 3+4. 路径归一化与包含
        if problem: return Decision(False, problem, request)
    return Decision(True, "allowed", normalized_request)
```

## 实现对照：Pi 源码与 Tau 双版本

工具的接口定义，Pi 与 Tau 几乎逐字段对应。

**工具定义**：

```typescript
// Pi 0.84.2: packages/agent/src/types.ts（原文节选）
export interface AgentTool<TParameters extends TSchema, TDetails = any>
  extends Tool<TParameters> {
  label: string;
  execute: (
    toolCallId: string,
    params: Static<TParameters>,
    signal?: AbortSignal,
    onUpdate?: AgentToolUpdateCallback<TDetails>,
  ) => Promise<AgentToolResult<TDetails>>;
  executionMode?: ToolExecutionMode; // "sequential" | "parallel"
}
```

```python
# Tau: tau_agent/tools.py（原文节选）
@dataclass(frozen=True, slots=True)
class AgentTool:
    name: str
    label: str
    description: str
    parameters: Mapping[str, JSONValue]  # JSON-schema 风格元数据
    execute_fn: ToolExecutor
    execution_mode: ToolExecutionMode = "parallel"

    async def execute(self, tool_call_id, arguments, signal=None, on_update=None):
        """以 Pi 兼容的 call-id 与进度语义执行工具。"""
        return await self.execute_fn(tool_call_id, arguments, signal, on_update)
```

对应关系：TS 的 `execute(toolCallId, params, signal, onUpdate)` ↔ Python 的 `execute_fn(tool_call_id, arguments, signal, on_update)`；`executionMode` ↔ `execution_mode`。两处设计一致：**工具是数据（schema）+ 函数（executor）的组合**，`execute` 只是把四个参数转交给 executor。

**工具结果**：

```typescript
// Pi 0.84.2: packages/agent/src/types.ts（原文节选）
export interface AgentToolResult<T> {
  content: (TextContent | ImageContent)[];
  details: T;
  addedToolNames?: string[];
  terminate?: boolean; // 本批所有工具都置 true 才提前终止
}
```

```python
# Tau: tau_agent/tools.py（原文节选）
class AgentToolResult(WireModel):
    content: list[TextContent | ImageContent] = Field(default_factory=list)
    details: JSONValue = None
    added_tool_names: list[str] | None = None
    terminate: bool | None = None

    @property
    def text(self) -> str:
        return "".join(block.text for block in self.content if isinstance(block, TextContent))
```

注意 `terminate` 字段：单批并行工具中，**只有全部工具的结果都置 `terminate=true` 才提前终止**——这是 [02 章](../02-agent-loop/README.md) `shouldTerminateToolBatch` 的字段基础。

## Python 实验

```sh
python3 -m learn_pi_lab lab permissions   # 被拒绝的请求不会调用注入执行器
```

## 验证方式

```sh
python3 -m unittest tests.test_02_tool_permissions tests.test_11_projects -v
```

## 边界与安全

- **允许列表不是沙箱**：生产实现还需要操作系统隔离、最小凭据、审计日志、用户确认，以及针对符号链接和竞态条件的防御。
- 不要由字符串拼接生成 shell 命令；命令令牌必须是白名单内的裸命令。
- 工具是隔离边界：executor 抛出的异常应转成结构化错误结果，而不是让循环崩溃。
- bash 输出必须截断并声明截断行为；危险操作必须经过权限层或人工确认。
