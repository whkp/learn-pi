# B03 · 流式输出

> 模型回复不再"等完再给"，而是增量吐出。流式让"等待模型"变成"边收边显示"——这是 TUI 能实时显示回复的前提。教学上它也是后面事件流（B10）的雏形：**消费者按片段消费，而不是等完整结果**。

## 上一阶段已有 / 本阶段新增

- 已有：messages 多轮历史。
- 新增：`stream_reply` 生成器（逐块 yield）、`collect` 消费者（拼回完整文本）。

## 核心设计

```python
def stream_reply(text: str, chunk_size: int = 2) -> Iterator[str]:
    for index in range(0, len(text), chunk_size):
        yield text[index : index + chunk_size]

def collect(stream: Iterator[str]) -> str:
    return "".join(stream)
```

三个决策及原因：

1. **生成器（yield）**：这是 Python 里表达"流"的自然方式——`stream_reply` 调用时不执行，消费时才逐块产出。
2. **消费者与生产分离**：`collect` 是一个独立消费者。真实场景里消费者是 TUI（显示）、日志（记录）、RPC（转发）——同一个流，多个消费者。
3. **教学简化**：真实流式是网络分块到达，这里用字符串切片模拟——机制（生成器消费）一致，简化在传输层。

## 运行

```sh
cd examples/harness/step_03_streaming
python3 streaming.py
```

预期输出（每 2 个字符一块）：

```
流式|输出|让等|待变|成可|见的|进度|。
```

## 失败实验：不消费生成器

`stream_reply(...)` 直接打印，得到的是 `generator object`——生成器是惰性的，不迭代就没有输出。这提示：**流式接口要求消费者主动消费**，这是 API 设计的隐性契约。

## 下一步

[B04 第一个工具](../step_04_first_tool/README.md)：模型开始"伸手"——返回工具调用请求，agent loop 第一次完整闭环。
