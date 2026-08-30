# B01 · 裸 API 调用

> 一次性调用模型拿回一个回复。没有循环、没有工具、没有历史——这是"最没有 agent 味的代码"，但它是主线的地基：**模型调用必须被包在函数后面**，后面换真实 Provider 时调用方不用改。

## 本章要解决的问题

"调用一次 LLM 拿一个回复"——最简单的形态是什么？答案是 20 行以内：一个函数、一个 prompt、一个返回字符串。

## 核心设计

```python
def mock_chat(system: str, user: str) -> str:
    return f"你说的是：「{user}」。这是 mock 模型的回复。"

def chat_once(prompt: str) -> str:
    return mock_chat(system="", user=prompt)
```

三个决策及原因：

1. **mock 模型**：主线全程离线。`mock_chat` 的签名（`system, user -> str`）刻意对齐真实 API 的形状，后面换成真实 Provider 时只需改这一个函数。
2. **返回字符串**：此时模型输出就是纯文本。B04 之后输出会变成结构化的（可能带工具调用），返回类型会演进。
3. **`system` 参数先留着**：虽然 B01 忽略它，但它是后面 prompt 装配的起点——现在留接口，后面填内容。

## 运行

```sh
cd examples/harness/step_01_bare_api
python3 chat_once.py
```

预期输出：

```
你说的是：「什么是 agent？」。这是 mock 模型的回复。
```

## 测试

```sh
python3 -m unittest discover -s tests -v
```

## 失败实验：如果 mock 返回空字符串

`mock_chat` 改成 `return ""`，`chat_once` 会静默返回空——调用方拿到空串但没有任何错误信号。这提示一个将要出现的需求：**回复可能失败或为空，不能假设每次都有内容**（B06 的错误回填会处理）。

## 下一步

[B02 messages 多轮历史](../step_02_messages/README.md)：一次调用不够——对话要连续，于是 messages 数组出场。
