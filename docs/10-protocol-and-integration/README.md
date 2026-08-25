# 协议与集成 —— SDK、RPC 与 JSONL 边界

> 把 Pi 接入自己的宿主程序：Print、JSON、RPC 三种无头模式，以及它们共同的 JSONL 分帧基础。这一章拆解协议层"如何实现"：分帧状态机、stdin/stdout 约定、SDK 集成边界。

## 学习目标

- 掌握 JSONL 按换行分帧的解析约束：粘包、半包、无效 JSON、未知事件。
- 理解 Print / JSON / RPC 三种模式的差异与用途。
- 理解 SDK 集成中的权限、认证与会话边界。

## 机制：stdout 是协议，stderr 是诊断

无头模式的基本原则：**stdout 只留给协议数据，诊断写 stderr**。RPC/JSON 模式在 stdin 上收命令、在 stdout 上发事件；任何 `console.log` 混进 stdout 都会破坏协议帧。

### JSONL 分帧的四个边界

消费者必须处理：

1. **粘包**：一次读取可能包含多个记录。
2. **半包**：一条记录可能被切成两段到达。
3. **无效 JSON**：坏行不能静默吞掉。
4. **未知事件**：新版本的事件类型要保留而不是崩掉。

处理方式是一个**增量状态机**：把字节流切成"完整行"交给业务层，业务层只关心"一行 = 一个记录"。未终止的超长记录必须拒绝（防内存耗尽），而不是无限缓冲。

### 三种模式的差异

| 模式 | 启动 | 输出 | 用途 |
|------|------|------|------|
| Print | `pi -p "prompt"` | 纯文本结果 | 脚本、一次性查询 |
| JSON | `pi --mode json "prompt"` | 事件 JSON 行 | 程序化消费事件流 |
| RPC | `pi --mode rpc` | stdin 命令 / stdout 事件 | 长驻集成、双向控制 |

三种模式共享同一个 Agent 核心，区别只在前端层。

## Pi 源码怎么实现（0.84.2）

RPC 模式在 `packages/coding-agent/src/modes/rpc/rpc-mode.ts`：

```typescript
// packages/coding-agent/src/modes/rpc/rpc-mode.ts（Pi 0.84.2，注释）
// RPC mode: Headless operation with JSON stdin/stdout protocol.
// Receives commands as JSON on stdin, outputs events and responses as JSON on stdout.

// 关键：用逐行读取器把 stdin 流切成行，再逐行反序列化
const detachJsonl = attachJsonlLineReader(process.stdin, (line) => {
  // 每收到一行 JSON 命令 → 处理 → 在 stdout 上写一行 JSON 事件
});
```

`attachJsonlLineReader` 负责把字节流按换行切成完整行（处理半包/粘包），业务层只关心"一行 = 一个命令"。JSON 模式（`modes/json-event.ts`）复用同一套事件序列化，把 `JsonAgentSessionEvent` 逐行输出。

### RPC 帧的完整约定

生产 RPC 还包含：

- **记录大小上限**：Tau 的实现里 `_MAX_RECORD_BYTES = 16MB`，超过即拒绝——防恶意/损坏输入撑爆内存。
- **方法白名单**：服务端只接受注册过的方法，未注册返回错误。
- **请求/响应关联**：每个命令带 `id`，响应与事件都携带该 id，调用方才能配对。
- **错误是数据**：方法执行失败返回结构化错误，不退出进程。

## 当前 Pi 行为

- Print：`pi -p "prompt"`，输出结果后退出。
- JSON：`pi --mode json "prompt"`，所有会话事件以 JSON 行输出到 stdout。
- RPC：`pi --mode rpc [options]`，stdin 收 JSON 命令、stdout 发事件/响应。
- SDK：`session.subscribe(...)` 订阅事件；`createCodingTools` 需要 `cwd`。

## 在 Pi 里怎么操作

```sh
pi -p "prompt"                       # 一次性查询
pi --mode json "prompt"              # 事件流输出到 stdout
pi --mode rpc                        # 长驻协议模式
```

## Python 对照

[rpc_jsonl.py](../../learn_pi_lab/labs/rpc_jsonl.py) 实现一个最小的 JSONL 分帧器：`feed` 缓冲不完整字节流到换行符，再验证 `id`/`method`/`params`，并限制未终止缓冲区大小：

```python
codec = JsonlRpcCodec()
messages = codec.feed('{"id":"1","method":"ping","params":{}}\n')
```

核心是增量缓冲与上限：

```python
def feed(self, chunk: str) -> tuple[RpcRequest, ...]:
    candidate = self._buffer + chunk
    if len(candidate.encode("utf-8")) > self._max_buffer_bytes and "\n" not in candidate:
        self._buffer = ""
        raise RpcProtocolError("unterminated record exceeds buffer limit")
    records = candidate.split("\n")
    self._buffer = records.pop()          # 最后一段不完整，留到下次
    for record in records:
        if not record.strip():
            continue                      # 空行跳过
        messages.append(_validate_record(json.loads(record)))
    return tuple(messages)
```

设计要点：`split("\n")` 后 `pop()` 保留尾巴（半包）；空行跳过；未终止记录超过缓冲上限即失败并清空（防内存耗尽）。[rpc_console.py](../../projects/rpc_console.py) 基于它实现允许列表 ping 接口：只支持 `ping`，返回 JSON，不创建子进程、不执行命令。

Tau 对照：`tau_coding/rpc.py` 是完整的 Pi 兼容 RPC 前端，`tau_agent/session/jsonl.py` 是 JSONL 会话存储（追加、读取、恢复）。

## 实现对照：Pi 源码与 Tau 双版本

RPC 前端两套实现共享同一个协议思路：stdin 收 JSON 行、stdout 发 JSON 行、限制记录大小。

**帧读取**——Pi 的 JSONL 逐行分帧器（核心实现）：

```typescript
// packages/coding-agent/src/modes/rpc/jsonl.ts（Pi 0.84.2，原文节选）
/**
 * 分帧只认 LF。载荷字符串里可能含其他 Unicode 分隔符（如 U+2028/U+2029），
 * 客户端必须只在 \n 上切分记录。
 */
export function serializeJsonLine(value: unknown): string {
  return `${JSON.stringify(value)}\n`;
}

/**
 * 给流挂一个只认 LF 的 JSONL 读取器。
 *
 * 刻意不用 Node readline：readline 会额外切分 JSON 字符串内合法的 Unicode 分隔符，
 * 因此不实现严格 JSONL 分帧。
 */
export function attachJsonlLineReader(stream: Readable, onLine: (line: string) => void): () => void {
  const decoder = new StringDecoder("utf8");
  let buffer = "";

  const onData = (chunk: string | Buffer) => {
    buffer += typeof chunk === "string" ? chunk : decoder.write(chunk);
    while (true) {
      const newlineIndex = buffer.indexOf("\n");
      if (newlineIndex === -1) {
        return;  // 半包：留到下次
      }
      onLine(buffer.slice(0, newlineIndex));  // 粘包：一次吐一行
      buffer = buffer.slice(newlineIndex + 1);
    }
  };
  const onEnd = () => {
    buffer += decoder.end();
    if (buffer.length > 0) {
      onLine(buffer);
      buffer = "";
    }
  };
  stream.on("data", onData);
  stream.on("end", onEnd);
  return () => {
    stream.off("data", onData);
    stream.off("end", onEnd);
  };
}
```

三个要点：

- **半包**：`buffer.indexOf("\n") === -1` 时把数据留在缓冲区，等下一个 chunk。
- **粘包**：一次 data 事件可能含多条记录，`while` 循环逐条吐出。
- **为什么不用 readline**：Node 的 readline 会切分 JSON 字符串内合法的 U+2028/U+2029 分隔符——严格 JSONL 分帧必须只认 `\n`。

Tau 用 `stdin.readline` 实现同一件事（`tau_coding/rpc.py` 的 `run()`）：

```python
# Tau: tau_coding/rpc.py（原文节选）
async def run(self) -> None:
    """服务命令直到 stdin 到达 EOF。"""
    await self._session.emit_pending_session_start()
    async with anyio.create_task_group() as tasks:
        while True:
            line = await anyio.to_thread.run_sync(self._stdin.readline)
            if line == "":
                break
            if line.endswith("\n"):
                line = line[:-1]
            if line.endswith("\r"):
                line = line[:-1]  # 兼容 CRLF
            if not line:
                continue
            # ...解析 JSON、路由到方法、写响应
```

对应关系：Pi 的 `attachJsonlLineReader` ↔ Tau 的 `readline` 循环；Pi 的 `onLine` 回调 ↔ Tau 的循环体。两者的共同点：**逐行消费、兼容 CRLF、空行跳过**。

## Python 实验

```sh
python3 -m learn_pi_lab lab rpc-jsonl   # 打印一条校验后的请求
```

## 验证方式

```sh
python3 -m unittest tests.test_10_rpc_jsonl tests.test_11_projects -v
```

## 边界与安全

- 生产集成：限制可调用方法、消息大小、超时与凭据范围；不要把 RPC 参数拼接成 shell 命令。
- SDK/RPC 不是绕开权限、认证和会话管理的捷径。
- 远端技能描述、工具注释、协议载荷都不应被当作可信指令。
- stdout 只留给协议数据，诊断一律写 stderr。
