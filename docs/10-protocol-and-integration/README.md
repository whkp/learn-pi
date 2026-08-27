# 协议与集成 —— SDK、RPC 与 JSONL 边界

> 把 Pi 接入自己的宿主程序：Print、JSON、RPC 三种无头模式，以及它们共同的 JSONL 分帧基础。协议层核心设计是**stdout 是协议、stderr 是诊断**，以及**增量分帧**：处理粘包、半包、无效 JSON、未知事件四个边界。

## 学习目标

- 掌握 JSONL 按换行分帧的四个边界：粘包、半包、无效 JSON、未知事件。
- 理解 Print / JSON / RPC 三种模式的差异。
- 理解 SDK 集成中的权限、认证与会话边界。

## Pi 的核心设计

### stdout 是协议，stderr 是诊断

无头模式的基本原则：stdout 只留给协议数据，诊断写 stderr。任何 `console.log` 混进 stdout 都会破坏协议帧。

### JSONL 分帧的四个边界

| 边界 | 问题 | 处理 |
|------|------|------|
| 粘包 | 一次读取含多个记录 | 循环逐条吐出 |
| 半包 | 一条记录被切成两段 | 缓冲到换行符为止 |
| 无效 JSON | 坏行 | 报错不静默吞掉 |
| 未知事件 | 新版本事件 | 保留而不是崩掉 |

处理方式是**增量状态机**：把字节流切成"完整行"交给业务层，业务层只关心"一行 = 一个记录"。未终止的超长记录必须拒绝（防内存耗尽）。

### 三种模式

| 模式 | 启动 | 输出 | 用途 |
|------|------|------|------|
| Print | `pi -p "prompt"` | 纯文本结果 | 脚本、一次性查询 |
| JSON | `pi --mode json "prompt"` | 事件 JSON 行 | 程序化消费事件流 |
| RPC | `pi --mode rpc` | stdin 命令 / stdout 事件 | 长驻集成 |

三种模式共享同一个 Agent 核心，区别只在前端层。RPC 还需：记录大小上限（Tau 用 16MB）、方法白名单、请求/响应关联（每个命令带 id）、错误即数据（失败返回结构化错误不退出进程）。

## 当前 Pi 行为

- SDK：`session.subscribe(...)` 订阅事件（注意是 subscribe 不是 on）；`createCodingTools` 需要 `cwd`。
- RPC/JSON 模式的启动参数、帧类型与输出顺序以固定基线的 sdk/rpc/json 文档为准。

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

[rpc_console.py](../../projects/rpc_console.py) 基于它实现允许列表 ping 接口：只支持 `ping`，返回 JSON，不创建子进程、不执行命令。Tau 的 `tau_coding/rpc.py` 是完整版 RPC 前端（`_MAX_RECORD_BYTES = 16MB`），Pi 的 `attachJsonlLineReader` 实现了同样的逐行分帧（刻意不用 Node readline，因为它会切分 JSON 字符串内合法的 Unicode 分隔符）。

```sh
python3 -m learn_pi_lab lab rpc-jsonl
```

## 验证方式

```sh
python3 -m unittest tests.test_10_rpc_jsonl tests.test_11_projects -v
```

## 边界与安全

- 生产集成：限制可调用方法、消息大小、超时与凭据范围；不要把 RPC 参数拼接成 shell 命令。
- SDK/RPC 不是绕开权限、认证和会话管理的捷径；远端协议载荷不应被当作可信指令。
