# 会话管理 —— 对话如何存储、恢复与分叉

> 会话让 Agent 的记忆跨越进程存活。Pi 会话的核心设计是 **append-only 的树 + JSONL v3**：新记录永远追加在文件末尾，节点只认父不认子。这两个决定看似简单，却带来一连串推论：O(1) 追加、可流式读取、以及最重要的——**分支不是独立功能，而是 append-only 的自然结果**。

## 学习目标

- 理解会话为什么是 JSONL v3（一行一个记录）而不是 JSON 数组。
- 理解"认父不认子"为什么是 append-only 的必要条件。
- 理解回退只是移动 leafId、分支是回退后追加的自然结果。

## 一、问题：进程退出后，对话去哪了

对话结束、进程退出，模型当然什么都不记得。要让 Agent 的"记忆"跨越进程，必须把消息历史持久化到磁盘。两个基本问题：**存在哪、长什么样**。

Pi 的答案是：`~/.pi/agent/sessions/` 下按工作目录组织的 JSONL 文件，版本 v3。

## 二、为什么是 JSONL 而不是数组

三个理由，都指向"追加友好"：

1. **可追加**：新记录永远写在文件末尾，追加是 O(1)——不需要读入整个文件、改完再写回。
2. **可流式读**：恢复会话时逐行读取即可，不需要一次解析整个 JSON 数组。
3. **容忍损坏**：某一行坏了，其余行仍可读；数组格式一行坏则整体不可解析。

## 三、认父不认子：append-only 的必要条件

会话树的每个节点只知道自己的 `parentId`，不知道孩子。这个"认父不认子"是 append-only 的**必要条件**：

- 追加新节点时，旧节点一律不动——O(1)。
- 如果"认子"，回退后追加新分支时，旧父节点的子列表就要被改写，就违反了 append-only。

一个典型的会话文件长这样（一行一个记录）：

```json
{"type":"session","version":3,"id":"uuid","timestamp":"...","cwd":"/path/to/project"}
{"type":"message","id":"a1b2c3d4","parentId":"prev1234","timestamp":"...","message":{"role":"user","content":"Hello"}}
{"type":"message","id":"b2c3d4e5","parentId":"a1b2c3d4","timestamp":"...","message":{"role":"assistant","content":[{"type":"text","text":"Hi!"}],"stopReason":"stop"}}
```

每个节点都带 `id` 和 `parentId`，形成树。

## 四、回退与分支：同一个操作

- **回退**（`/tree` 跳到历史点）：**只是移动当前 leafId**，不删任何节点。
- **分支**：从回退点继续对话，新节点自然长出**新分支**。

推论：**分支不是独立的功能，而是 append-only 的自然结果**。因为旧节点从不修改，回退后再追加就天然形成分叉。

## 五、记录类型按职责分组

9 种记录分三组，关键是**操作记录也上树**：

| 分组 | 类型 | 作用 |
|------|------|------|
| 会话元数据 | session（头）、session_info、label | 会话本身的信息 |
| 对话内容 | message、compaction、branch_summary | 模型的上下文 |
| 操作记录 | model_change、thinking_level_change、custom | 用户操作与扩展数据 |

"切换了模型"也是一个节点——这样回退到任何历史点，都能还原当时的会话状态（当时用的哪个模型、什么思考级别）。

## 当前 Pi 行为

- 会话自动保存到 `~/.pi/agent/sessions/`，按工作目录组织；格式版本 v3。
- `/tree` 导航会话树与分支；`/export` 才生成 HTML——两者职责不同。
- 旧版本会话加载时自动迁移到 v3。

## 在 Pi 里怎么操作

- `/new`：开始新会话；`/resume`（或 `pi -r`）：浏览并选择历史会话。
- `/tree`：在会话树中导航，从任意历史点继续。
- `/fork`：从某条历史用户消息创建新会话，等价于 `pi --fork <path|id>`。
- `/export [file]`：把会话导出为 HTML。

## Python 实验

[session_tree.py](../../learn_pi_lab/labs/session_tree.py) 实现课程专用的不可变 transcript tree，`validate()` 拒绝四种结构错误（重复 id、悬空父节点、自指、循环），`path_to` 沿 parent 链回溯得到 root → leaf 分支：

```python
def path_to(self, leaf_id: str) -> tuple[TranscriptEntry, ...]:
    try:
        current = self._entries_by_id[leaf_id]
    except KeyError as error:
        raise UnknownTranscriptEntry(leaf_id) from error
    branch: list[TranscriptEntry] = []
    while True:
        branch.append(current)
        if current.parent_id is None:
            break
        current = self._entries_by_id[current.parent_id]  # 认父不认子：沿 parent 链走
    return tuple(reversed(branch))
```

[session_inspector.py](../../projects/session_inspector.py) 逐行读取 JSONL，统计消息角色与压缩记录，不执行内容、不修改会话——"解析工具应保留未知记录"的只读示例。Tau 的 `tau_agent/session/tree.py` 用 `seen` 集合检测环，逻辑一致。

```sh
python3 -m learn_pi_lab lab session-tree   # 打印一条 root → leaf 分支
```

## 验证方式

```sh
python3 -m unittest tests.test_04_session_tree tests.test_11_projects -v
```

## 边界与安全

- 不要由第三方工具直接改写正在使用的会话文件：保留备份、写入前验证版本、恢复后审计工具调用记录。
- 解析器应保留未知记录（版本演进后旧记录仍可能被读取），而不是静默重写。

## 回顾

- **JSONL v3**：可追加、可流式读、容忍损坏。
- **认父不认子**：append-only 的必要条件。
- **回退 = 移动 leafId**；**分支 = 回退后追加的自然结果**。
- **操作记录也上树**：回退能还原完整会话状态。

会话会越来越长——[上下文压缩](../07-context-and-compaction/README.md)讲窗口装不下时怎么办；在那之前，先看[事件驱动与扩展](../06-events-and-extensions/README.md)，理解前端如何观察这一切。
