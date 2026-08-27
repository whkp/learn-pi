# 可靠性 —— 失败如何重试与隔离

> 网络会抖、Provider 会限流、工具会报错。Pi 的可靠性核心设计是**先分类，再重试**：不是所有失败都该重试，重试只适合可安全重放的操作，且必须退避、必须脱敏。

## 学习目标

- 理解可重试与不可重试错误的分类——为什么不能只看状态码。
- 掌握指数退避与注入式 sleep（可测试性）。
- 理解重试、取消、流式错误是三个不同的问题。

## Pi 的核心设计

### 先分类，再重试

按状态码分类不够：同一个 429 既可能是可重试的限流（`too many requests`），也可能是不可重试的配额耗尽（`insufficient_quota`）。Pi 的做法是**按错误内容匹配模式**，集中维护两张表：可重试（overloaded、rate limit、5xx、超时）与不可重试（quota exceeded、out of budget、billing）。新增 Provider 的报错文案，改一处即可。

### 重试的三个约束

1. **幂等**：重试只适合已证明幂等或可安全重放的操作。写文件、创建工单、付款需要幂等键、人工确认或补偿机制。
2. **退避**：指数退避（每次翻倍）+ 上限封顶，避免重试风暴；退避等待期间收到取消信号应立即中断。
3. **脱敏**：失败后只保留异常类型和次数，不把敏感异常文本传播到日志或模型上下文。

### 三个不同的问题

| 问题 | 手段 |
|------|------|
| 重试 | 错误分类 + 指数退避 |
| 取消 | 取消令牌沿调用链传递 |
| 流式错误 | 把已收到的部分与错误一起处理 |

别把它们混为一谈：取消不是重试的对手，而是搭档——退避等待被取消时立即退出。

## 当前 Pi 行为

- Provider 层有统一的重试与退避；取消通过 AbortSignal 传递到流式调用。
- 重试进度以事件形式可见（`ProviderRetryEvent`），用户在 TUI 里看到"第 N 次重试"而不是干等。

## 在 Pi 里怎么操作

- 重试大多自动发生，无需手动操作；网络不可用或配额耗尽时检查 `/login` 状态与 Provider 额度。

## Python 实验

[reliability.py](../../learn_pi_lab/labs/reliability.py) 用注入的 `sleep` 函数实现可测试的指数退避，失败后只保留异常类型和次数：

```python
result = retry(operation, attempts=3, base_delay=0.25)  # sleep 可注入，测试里不真睡
# 成功 → RetryResult(value, attempts, delays)
# 失败耗尽 → RetryExhausted(attempts, error_type)，不携带异常消息文本
```

核心循环：

```python
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

教学点：`RetryExhausted` 只带 `error_type`（如 `"OSError"`），不带 `str(error)`——从 API 上杜绝敏感文本泄漏。Tau 的 `tau_ai/retry.py` 提供了同样的退避函数（`retry_delay_seconds` 指数退避封顶）与可取消的等待（`wait_for_retry` 按 50ms 分片轮询，随时响应取消）。

```sh
python3 -m learn_pi_lab lab reliability   # 打印重试元数据，不真睡
```

## 验证方式

```sh
python3 -m unittest tests.test_09_reliability -v
```

## 边界与安全

- 重试只适合幂等或可安全重放的操作；不要将异常文本无界传播。
- 指数退避必须封顶，否则重试风暴会把瞬时故障放大成自 DDoS。
