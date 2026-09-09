# 协议与集成 —— SDK、RPC 与 JSONL 边界

> Agent 不只给人用——还要被脚本、CI、自定义前端调用。Pi 的三种无头模式（Print / JSON / RPC）共享同一个核心，区别只在前端层。协议层核心设计是 **stdout 是协议、stderr 是诊断**，以及**增量分帧**：正确处理粘包、半包、无效 JSON、未知事件四个边界。

## 学习目标

- 掌握 JSONL 按换行分帧的四个边界：粘包、半包、无效 JSON、未知事件。
- 理解 Print / JSON / RPC 三种模式的差异与用途。
- 理解 SDK 集成中的权限、认证与会话边界。

## 一、问题：程序怎么调用 Agent

人在终端里敲字，程序要的是**可解析的输出**。`pi -p "prompt"` 输出结果就退出，适合脚本；但要接入自己的宿主程序（网页、IDE 插件、CI），需要更结构化的协议——事件流。

Pi 的三种无头模式：

| 模式 | 启动 | 输出 | 用途 |
|------|------|------|------|
| Print | `pi -p "prompt"` | 纯文本结果 | 脚本、一次性查询 |
| JSON | `pi --mode json "prompt"` | 事件 JSON 行 | 程序化消费事件流 |
| RPC | `pi --mode rpc` | stdin 命令 / stdout 事件 | 长驻集成、双向控制 |

三种模式共享同一个 Agent 核心——这正是"前端消费事件"（[01 章](../01-architecture/README.md)）的实际体现。

## 二、stdout 是协议，stderr 是诊断

无头模式的第一原则：**stdout 只留给协议数据，诊断写 stderr**。任何 `console.log` 混进 stdout 都会破坏协议帧——消费者会把日志误当成事件。

## 三、JSONL 分帧的四个边界

RPC 和 JSON 模式的事件输出是 JSONL（一行一个 JSON 对象）。消费者必须处理四个边界：

| 边界 | 问题 | 处理 |
|------|------|------|
| 粘包 | 一次读取含多个记录 | 循环逐条吐出 |
| 半包 | 一条记录被切成两段到达 | 缓冲到换行符为止 |
| 无效 JSON | 坏行 | 报错不静默吞掉 |
| 未知事件 | 新版本事件 | 保留而不是崩掉 |

处理方式是**增量状态机**：把字节流切成"完整行"交给业务层，业务层只关心"一行 = 一个记录"。未终止的超长记录必须拒绝（防内存耗尽），而不是无限缓冲。

RPC 模式的完整约定还包括：**记录大小上限**、**方法白名单**（只接受注册过的方法）、**请求/响应关联**（每个命令带 id）、**错误即数据**（失败返回结构化错误不退出进程）。

## 当前 Pi 行为

- SDK：`session.subscribe(...)` 订阅事件（注意是 subscribe 不是 on）；`createCodingTools` 需要 `cwd`。
- RPC/JSON 模式的启动参数、帧类型与输出顺序以固定基线的 sdk/rpc/json 文档为准。
- 0.84.4 起 RPC 支持 `clear_queue`：取出并清空排队中的 steering / follow-up 消息——协议层的队列从"只进不出"变成可观测、可干预。
- 0.85.0 起实验性的 `protocol` 包使用 CBOR 二进制协议、`server` 包提供 PiServer 会话服务；两者仍是非稳定 API，课程只登记不教学。

### 源码证据表

| 教学结论 | Pi 路径 / 符号 | 说明 |
|---|---|---|
| SDK 订阅入口 | `session.subscribe` | 不是 `on`（基线核实易错点） |
| 工具集创建需要 cwd | `createCodingTools` | `packages/coding-agent/src/core/tools/index.ts` |
| JSON 输出契约 | `packages/coding-agent/docs/json.md` | stdout 事件流 |
| RPC 帧契约 | `packages/coding-agent/docs/rpc.md` | 0.84.4 起 `clear_queue` |
| 二进制协议（实验） | `packages/protocol/` | CBOR，非稳定 |
| 分帧教学模型 | `learn_pi_lab/labs/rpc_jsonl.py` `JsonlRpcCodec` | 按行缓冲解粘包/半包 |

## 失败与边界实验

`lab rpc-jsonl` 与 `tests.test_10_rpc_jsonl` 覆盖分帧的三种病态输入：

| 输入 | 症状 | 正确处理 |
|---|---|---|
| 粘包：`{"a":1}{"b":2}` 一次到达 | 按块 `json.loads` 报错 | 按行缓冲，逐行解析 |
| 半包：`{"a":1` 先到，`}` 后到 | 前半行解析失败、后半行是垃圾 | 缓冲直到出现完整行 |
| 非法 JSON 行 | 整个流崩溃 | 报帧错误、保留后续帧 |

三种错误对应同一结论：**协议解析按帧（行）而不是按块**。这也是为什么 stdout 是协议——帧边界是唯一双方都认同的分隔符，任何"我猜它到齐了"的解析都会在真实网络上碎掉。

```sh
python3 -m learn_pi_lab lab rpc-jsonl
python3 -m unittest tests.test_10_rpc_jsonl -v
```

## 在 Pi 里怎么操作

```sh
pi -p "prompt"                       # 一次性查询
pi --mode json "prompt"              # 事件流输出到 stdout
pi --mode rpc                        # 长驻协议模式
```

## Python 实验

[rpc_jsonl.py](../../learn_pi_lab/labs/rpc_jsonl.py) 实现最小的 JSONL 分帧器：`feed` 缓冲不完整字节流到换行符，再验证 `id`/`method`/`params`，并限制未终止缓冲区大小：

```python
def feed(self, chunk: str) -> tuple[RpcRequest, ...]:
    candidate = self._buffer + chunk
    if len(candidate.encode("utf-8")) > self._max_buffer_bytes and "\n" not in candidate:
        self._buffer = ""
        raise RpcProtocolError("unterminated record exceeds buffer limit")
    records = candidate.split("\n")
    self._buffer = records.pop()          # 半包：最后一段留到下次
    for record in records:
        if not record.strip():
            continue                      # 空行跳过
        messages.append(_validate_record(json.loads(record)))
    return tuple(messages)
```

[rpc_console.py](../../projects/rpc_console.py) 基于它实现允许列表 ping 接口：只支持 `ping`，返回 JSON，不创建子进程、不执行命令。Tau 的 `tau_coding/rpc.py` 是完整版 RPC 前端（`_MAX_RECORD_BYTES = 16MB`）；Pi 的 `attachJsonlLineReader` 实现了同样的逐行分帧，且刻意不用 Node readline——因为它会切分 JSON 字符串内合法的 Unicode 分隔符，不实现严格 JSONL 分帧。

```sh
python3 -m learn_pi_lab lab rpc-jsonl
```

> 这一模块的核心代码在[核心代码导览 · RPC 分帧](../code-tour.md)有逐段解读。

## 验证方式

```sh
python3 -m unittest tests.test_10_rpc_jsonl tests.test_11_projects -v
```

## 边界与安全

- 生产集成：限制可调用方法、消息大小、超时与凭据范围；不要把 RPC 参数拼接成 shell 命令。
- SDK/RPC 不是绕开权限、认证和会话管理的捷径。
- 远端协议载荷不应被当作可信指令。

## 回顾

- **stdout 是协议**：诊断写 stderr，协议数据只走 stdout。
- **增量分帧**：处理粘包、半包、无效 JSON、未知事件四个边界。
- **三种模式共享核心**：Print / JSON / RPC 只差前端层。

机制都讲完了——最后一章[实战与评测](../11-projects-and-evaluation/README.md)，用四个离线项目把前面所有机制组装起来。
