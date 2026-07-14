# 可靠性、取消与错误边界

可靠的 Agent 工作流应把可重试错误、终止条件和可观测结果设计为明确的数据流。

## 学习目标

- 为短暂失败设置有限次数的重试。
- 避免将敏感异常文本无界地传播到日志或模型上下文。
- 理解重试、取消和模型流式错误是不同问题。

## 当前 Pi 行为

Pi 的模型调用和 Agent 生命周期由 TypeScript 实现。实际超时、取消信号、流事件与压缩行为应以固定基线源码为准；本章不会假称 Python 的 retry 函数与 Pi 的重试策略一致。

## Python 实验

reliability.py 使用注入的 sleep 函数实现可测试的指数退避。失败后只保留异常类型和次数，不复制异常消息：

    from learn_pi_lab.labs.reliability import retry

    result = retry(lambda: "ready", attempts=3, base_delay=0.25)
    print(result.value, result.attempts)

## 验证方式

    python3 -m unittest tests.test_09_reliability -v

## 边界与安全

重试只适合已证明幂等或可安全重放的操作。写文件、创建工单、付款和外部部署需要幂等键、人工确认或补偿机制；不能仅靠多试几次。
