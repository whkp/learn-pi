# B02 · messages 多轮历史

> 一次调用不够——对话要连续。本阶段引入 messages 数组：**模型每次调用只看传入的数组，它不记得上次；"记住聊到哪"是 harness 的职责**。这是[消息与记忆](../../../docs/04-messages-and-memory/README.md)一章的第一个落地。

## 上一阶段已有 / 本阶段新增

- 已有：一次模型调用（`chat_once`）。
- 新增：`messages` 数组（role + content）、多轮循环、`mock_chat` 接收整个数组。

## 核心设计

```python
Message = dict[str, str]  # {"role": "user"|"assistant", "content": "..."}

def conversation() -> list[Message]:
    messages: list[Message] = []
    for user_turn in ("你好", "什么是 harness？", "谢谢"):
        messages.append({"role": "user", "content": user_turn})
        reply = mock_chat(messages)          # 把整个历史喂回模型
        messages.append({"role": "assistant", "content": reply})
    return messages
```

三个决策及原因：

1. **role 判别**：每条消息标明 user / assistant——这就是 [04 章](../../../docs/04-messages-and-memory/README.md) 的 role 判别，此处用 dict 表达（B06 会换成 dataclass）。
2. **历史整体回传**：每次调用都传整个 `messages`，而不是只传新消息——模型需要完整上下文才能连续。
3. **harness 追加**：谁往数组里追加？是 harness（这里就是 `conversation()` 的循环），不是模型——模型的"记忆"是 harness 喂给它的。

## 运行

```sh
cd examples/harness/step_02_messages
python3 conversation.py
```

## 失败实验：只传最后一条消息

把 `mock_chat(messages)` 改成 `mock_chat([messages[-1]])`，模型就"忘记"了之前的对话——这正是"模型无状态"的直接演示：**记忆不在模型里，在你喂给它的数组里**。

## 下一步

[B03 流式输出](../step_03_streaming/README.md)：模型回复不再是"等完再给"，而是增量吐出——UI 需要。
