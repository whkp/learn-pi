# 可靠性 —— 失败如何重试与隔离

> 网络会抖、Provider 会限流、工具会报错。可靠的 Agent 把"可重试错误、终止条件、可观测结果"设计成明确的数据流。这一章拆解可靠性"如何实现"：错误分类、重试策略、退避算法、取消传递。

## 学习目标

- 理解可重试错误与不可重试错误的分类——不是所有失败都该重试。
- 掌握指数退避与注入式 sleep（可测试性）。
- 理解重试、取消、模型流式错误是不同的问题。
- 读 Pi 0.84.2 的重试实现，并对照本课程的 Python 教学模型。

## 机制：先分类，再重试

### 为什么不是所有失败都重试

重试的前提是**错误可分类**：

- **可重试**：过载、限流、5xx、瞬时网络错误——重试有意义。
- **不可重试**：配额耗尽、计费问题、参数错误——重试只会浪费时间并放大成本。

按状态码分类不够：同一个 429 既可能是可重试的限流，也可能是不可重试的配额（`insufficient_quota`）。可靠的实现要按**错误内容**分类，而不是只看状态码。

### 重试的三个约束

1. **幂等**：重试只适合已证明幂等或可安全重放的操作。写文件、创建工单、付款需要幂等键、人工确认或补偿机制。
2. **退避**：指数退避（每次翻倍）+ 上限封顶，避免重试风暴。
3. **脱敏**：失败后只保留异常类型和次数，不把敏感异常文本传播到日志或模型上下文。

### 三个不同的问题

| 问题 | 手段 |
|------|------|
| 重试 | 错误分类 + 指数退避 |
| 取消 | 取消令牌（AbortSignal）沿调用链传递，中断流式与退避等待 |
| 流式错误 | 流中途失败时，把已收到的部分与错误一起处理 |

别把它们混为一谈：取消不是重试的对手，而是重试的搭档——退避等待期间收到取消信号应立即中断。

## Pi 源码怎么实现（0.84.2）

Provider 层的重试分类在 `packages/ai/src/utils/retry.ts`：

```typescript
// packages/ai/src/utils/retry.ts（Pi 0.84.2，节选）
const NON_RETRYABLE_PROVIDER_LIMIT_ERROR_PATTERN = buildProviderErrorPattern([
  "GoUsageLimitError", "FreeUsageLimitError",
  "insufficient_quota", "out of budget", "quota exceeded", "billing",
]);

const RETRYABLE_PROVIDER_ERROR_PATTERN = buildProviderErrorPattern([
  "overloaded", "rate.?limit", "too many requests",
  "429", "500", "502", "503", "504", "524",
  "service.?unavailable", "server.?error", "internal.?error",
]);
```

要点：

- 用**正则模式**匹配错误文本，而不是只看状态码——`429` 同时出现在两个模式里，靠上下文文本（`quota exceeded` vs `too many requests`）区分。
- 模式表是集中维护的：新增 Provider 的报错文案，改这一处即可。
- `packages/ai/src/utils/provider-retry.ts` 实现退避并发射进度事件（`ProviderRetryEvent`），让用户看到"第 N 次重试"而不是干等。

### 退避与取消

`tau_ai/retry.py`（Tau 的实现）展示了退避与取消如何协作：

```python
def retry_delay_seconds(attempt: int, *, max_delay_seconds: float) -> float:
    """指数退避，按上限封顶。"""
    if max_delay_seconds <= 0:
        return 0.0
    base_delay = min(RETRY_BASE_DELAY_SECONDS, max_delay_seconds)  # 0.25s
    return float(min(max_delay_seconds, base_delay * (2**attempt)))

async def wait_for_retry(delay_seconds: float, *, signal: CancellationToken | None) -> bool:
    """退避等待；收到取消信号立即返回 False。"""
    remaining = delay_seconds
    while remaining > 0:
        if signal is not None and signal.is_cancelled():
            return False
        step = min(RETRY_POLL_SECONDS, remaining)  # 50ms 分片轮询
        await sleep(step)
        remaining -= step
    return signal is None or not signal.is_cancelled()
```

设计要点：退避等待按 50ms 分片，随时可以响应取消——重试不是"死等"，而是可中断的。

## 当前 Pi 行为

- Provider 层有统一的重试与退避；取消通过 AbortSignal 传递到流式调用。
- 模型流式错误、工具执行错误、会话恢复错误各自有独立的错误边界。
- 错误信息脱敏：重试日志保留类型与次数，不复制敏感异常消息。

## 在 Pi 里怎么操作

- 重试大多自动发生，无需手动操作；`ProviderRetryEvent` 会在 TUI 中显示重试进度。
- 网络不可用或配额耗尽时，检查 `/login` 状态与 Provider 额度。

## Python 对照

[reliability.py](../../learn_pi_lab/labs/reliability.py) 用注入的 `sleep` 函数实现可测试的指数退避，失败后只保留异常类型和次数：

```python
result = retry(operation, attempts=3, base_delay=0.25)  # sleep 可注入，测试里不真睡
# 成功 → RetryResult(value, attempts, delays)
# 失败耗尽 → RetryExhausted(attempts, error_type)，不携带异常消息文本
```

教学点：`retry` 是一个纯函数式的数据流——`RetryResult(value, attempts, delays)` 把"成功值、尝试次数、退避延迟"都变成可断言的结果；`RetryExhausted` 只带 `error_type`（如 `"OSError"`），不带 `str(error)`，从 API 上杜绝敏感文本泄漏。

```python
# reliability.py 的核心循环（简化）
for current_attempt in range(1, attempts + 1):
    try:
        return RetryResult(operation(), current_attempt, tuple(delays))
    except Exception as error:
        if current_attempt == attempts:
            raise RetryExhausted(current_attempt, type(error).__name__) from error
        delay = float(base_delay) * (2 ** (current_attempt - 1))
        delays.append(delay)
        if sleep is not None:
            sleep(delay)
```

## 实现对照：Pi 源码与 Tau 双版本

重试的两套实现分工略有不同：Pi 在 Provider 层做**错误分类**，Tau 把**退避与取消**做成可复用的工具函数。

**错误分类（Pi）**：

```typescript
// Pi 0.84.2: packages/ai/src/utils/retry.ts（原文节选）
const NON_RETRYABLE_PROVIDER_LIMIT_ERROR_PATTERN = buildProviderErrorPattern([
  "insufficient_quota", "out of budget", "quota exceeded", "billing",
]);
const RETRYABLE_PROVIDER_ERROR_PATTERN = buildProviderErrorPattern([
  "overloaded", "rate.?limit", "too many requests",
  "429", "500", "502", "503", "504", "524",
  "service.?unavailable", "server.?error", "internal.?error",
]);
```

**退避与取消（Tau）**：

```python
# Tau: tau_ai/retry.py（原文节选）
def retry_delay_seconds(attempt: int, *, max_delay_seconds: float) -> float:
    """指数退避，按上限封顶。"""
    if max_delay_seconds <= 0:
        return 0.0
    base_delay = min(RETRY_BASE_DELAY_SECONDS, max_delay_seconds)  # 0.25s
    return float(min(max_delay_seconds, base_delay * (2**attempt)))

async def wait_for_retry(delay_seconds, *, signal) -> bool:
    """退避等待；收到取消信号立即返回 False。"""
    remaining = delay_seconds
    while remaining > 0:
        if signal is not None and signal.is_cancelled():
            return False
        step = min(RETRY_POLL_SECONDS, remaining)  # 50ms 分片轮询
        await sleep(step)
        remaining -= step
    return signal is None or not signal.is_cancelled()
```

对应关系：

- Pi 的分类表 → Tau 没有直接对应（Tau 把分类留给具体 Provider 适配层）；Tau 的退避工具 → 对应 Pi 的 provider-retry.ts。
- 两者共同的设计约束：**指数退避必封顶**、**退避可被取消中断**（Tau 用 50ms 分片轮询响应取消；Pi 在调用链上传递 AbortSignal）。

**进度事件**——两套都把重试变成可观测数据：Pi 发 `ProviderRetryEvent`，Tau 的 `provider_retry_event` 构造同样的消息（`Retrying provider request N/M after <reason>...`）。

## Python 实验

```sh
python3 -m learn_pi_lab lab reliability   # 打印重试元数据，不真睡
```

## 验证方式

```sh
python3 -m unittest tests.test_09_reliability -v
```

## 边界与安全

- 重试只适合已证明幂等或可安全重放的操作；写文件、支付、外部部署需要幂等键、人工确认或补偿机制。
- 不要将异常文本无界地传播到日志或模型上下文。
- 超时、取消信号与流式错误是不同问题，别混为一谈。
- 指数退避必须封顶，否则重试风暴会把瞬时故障放大成自 DDoS。
