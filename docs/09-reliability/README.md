# 可靠性 —— 失败如何重试与隔离

> 网络会抖、Provider 会限流、工具会报错。可靠的 Agent 不是"不出错"，而是**错误被设计成明确的数据流**。Pi 的可靠性核心设计是**先分类，再重试**：不是所有失败都该重试，重试只适合可安全重放的操作，且必须退避、必须脱敏。

## 学习目标

- 理解可重试与不可重试错误的分类——为什么不能只看状态码。
- 掌握指数退避与注入式 sleep（可测试性）。
- 理解重试、取消、流式错误是三个不同的问题。

## 一、问题：失败是常态，不是异常

Agent 的每一次模型调用都依赖网络和第三方服务。过载、限流、超时、配额耗尽……失败是常态。关键不是"会不会失败"，而是**失败发生时，程序的行为是可预测的**：该重试的重试、该停的停、该报告的报告。

## 二、先分类，再重试

**不是所有失败都该重试**。按状态码分类不够：同一个 429 既可能是可重试的限流（`too many requests`），也可能是不可重试的配额耗尽（`insufficient_quota`）。Pi 的做法是**按错误内容匹配模式**，集中维护两张表：

| 分类 | 错误模式（节选） | 重试？ |
|------|-----------------|--------|
| 可重试 | overloaded、rate limit、429、500、502、503、504、service unavailable | 是 |
| 不可重试 | insufficient_quota、out of budget、billing | 否——重试只会放大成本 |

为什么集中维护？因为新增 Provider 的报错文案，改一处即可；分类策略与具体调用解耦。

## 三、重试的三个约束

1. **幂等**：重试只适合已证明幂等或可安全重放的操作。写文件、创建工单、付款需要幂等键、人工确认或补偿机制——不能靠"多试几次"。
2. **退避**：指数退避（每次翻倍）+ 上限封顶，避免重试风暴；**退避等待期间收到取消信号应立即中断**。
3. **脱敏**：失败后只保留异常类型和次数，不把敏感异常文本传播到日志或模型上下文。

## 四、三个不同的问题

| 问题 | 手段 |
|------|------|
| 重试 | 错误分类 + 指数退避 |
| 取消 | 取消令牌沿调用链传递 |
| 流式错误 | 把已收到的部分与错误一起处理 |

别把它们混为一谈：取消不是重试的对手，而是搭档——退避等待被取消时立即退出，而不是死等。

## 当前 Pi 行为

- Provider 层有统一的重试与退避；取消通过 AbortSignal 传递到流式调用。
- 重试进度以事件形式可见（`ProviderRetryEvent`），用户在 TUI 里看到"第 N 次重试"而不是干等。
- 重试与流式输出不冲突：`runLoop` 的流式请求失败时错误通过 `stopReason = "error"` 走正常终止路径（`agent-loop.ts` 215 行），而不是抛出未捕获异常——可靠性是"变成一种消息"，不是"变成一种崩溃"。
- 0.84.4 起支持 RPC 队列清理（`clear_queue`）：积压的 steering / follow-up 消息可以取出并清空，而不是只能默默执行。

### 源码证据表

| 教学结论 | Pi 路径 / 符号 | 说明 |
|---|---|---|
| 错误变成消息而非异常 | `packages/agent/src/agent-loop.ts`（215） | `stopReason === "error"` 走终止路径 |
| 取消信号贯通 | `executeToolCalls(..., signal)`（409–415） | AbortSignal 传到每个工具 |
| 重试对用户可见 | `ProviderRetryEvent` | TUI 显示第 N 次重试 |
| 队列可清空 | v0.84.4 release notes（RPC `clear_queue`） | 取出并清空积压消息 |
| 退避教学模型 | `learn_pi_lab/labs/reliability.py` `retry()` | 分类→退避→封顶 |

## 失败与边界实验

`lab reliability` 与 `tests/test_09_reliability` 覆盖的重试矩阵：

| 失败类型 | 分类 | 策略 | 为什么 |
|---|---|---|---|
| 429 限流 | 可重试 | 指数退避 + 封顶 + 看 `Retry-After` | 服务端明确说"稍后再来" |
| 5xx | 可重试 | 指数退避 + 封顶 | 瞬时故障概率高 |
| 401 / 403 | 不可重试 | 立即失败并提示配认证 | 重试只是刷错误日志 |
| 400 参数错误 | 不可重试 | 立即失败 | 重试同样的错误参数没有意义 |
| 网络中断（流中途） | 视情况 | 已产出部分按截断处理 | 不能重复计费整轮 |

关键不变量：**重试发生在"一次模型调用"的边界内**。工具已经产生的副作用不会因重试消失——所以有副作用的工具必须自己幂等，重试机制救不了它。

```sh
python3 -m learn_pi_lab lab reliability
python3 -m unittest tests.test_09_reliability -v
```

## 在 Pi 里怎么操作

- 重试大多自动发生，无需手动操作；网络不可用或配额耗尽时检查 `/login` 状态与 Provider 额度。

## Python 实验

[reliability.py](../../learn_pi_lab/labs/reliability.py) 用注入的 `sleep` 函数实现可测试的指数退避，失败后只保留异常类型和次数：

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

```python
result = retry(operation, attempts=3, base_delay=0.25)  # sleep 可注入，测试里不真睡
# 成功 → RetryResult(value, attempts, delays)
# 失败耗尽 → RetryExhausted(attempts, error_type)，不携带异常消息文本
```

教学点：`RetryExhausted` 只带 `error_type`（如 `"OSError"`），不带 `str(error)`——从 API 上杜绝敏感文本泄漏。Tau 的 `tau_ai/retry.py` 提供了同样的退避函数（`retry_delay_seconds` 指数退避封顶）与可取消的等待（`wait_for_retry` 按 50ms 分片轮询，随时响应取消）。

```sh
python3 -m learn_pi_lab lab reliability   # 打印重试元数据，不真睡
```

> 这一模块的核心代码在[核心代码导览 · 重试与退避](../code-tour.md)有逐段解读。

## 验证方式

```sh
python3 -m unittest tests.test_09_reliability -v
```

## 边界与安全

- 重试只适合幂等或可安全重放的操作；写文件、支付、外部部署需要幂等键、人工确认或补偿机制。
- 不要将异常文本无界传播到日志或模型上下文。
- 指数退避必须封顶，否则重试风暴会把瞬时故障放大成自 DDoS。

## 回顾

- **先分类再重试**：按错误内容匹配，不看状态码；不可重试的错误重试只会放大成本。
- **三个约束**：幂等、退避必封顶、脱敏。
- **三个不同问题**：重试 / 取消 / 流式错误——取消是重试的搭档。

Agent 不只是人用的——它还要被程序用。下一章[协议与集成](../10-protocol-and-integration/README.md)讲 SDK、RPC 与 JSONL 边界。
