# 会话管理 —— 对话如何存储、恢复与分叉

> 会话让 Agent 的记忆跨越进程存活：存到哪、长什么样、怎么分支、怎么恢复。这一章拆解会话系统"如何实现"：JSONL v3 的文件结构、9 种记录类型、会话树的"认父不认子"、以及回退与分支的操作语义。

## 学习目标

- 理解会话为什么是 JSONL v3（一行一个记录）而不是 JSON 数组。
- 认识 9 种记录类型，以及各自承载什么。
- 理解会话树"认父不认子"为什么是 append-only 的必要条件。
- 理解回退只是移动 leafId、分支是回退后追加的自然结果。

## 机制：append-only 的树

### 为什么是 JSONL 而不是数组

- **JSONL 可追加**：新记录永远写在文件末尾，不需要读入整个文件、改完再写回——追加是 O(1)。
- **JSONL 可流式读**：恢复会话时逐行读取即可，不需要一次解析整个 JSON 数组。
- **JSONL 容忍损坏**：某一行坏了，其余行仍可读；数组格式一行坏则整体不可解析。

### 认父不认子

会话树上的节点**只知道自己的 `parentId`，不知道孩子**。这个"认父不认子"是 append-only 的必要条件：

- 追加新节点时，旧节点一律不动——O(1)。
- 如果"认子"，回退后追加新分支，旧父节点的子列表就要被改写，就违反了 append-only。

### 回退与分支

- **回退**：`/tree` 跳到历史点，**只是移动当前 leafId**，不删任何节点。
- **分支**：从回退点继续对话，新节点自然长出**新分支**。
- 推论：**分支不是独立的功能，而是 append-only 的自然结果**。

### 记录类型按职责分组

9 种记录可以分三组：

| 分组 | 类型 | 作用 |
|------|------|------|
| 会话元数据 | session（头）、session_info（会话名）、label（标记点） | 会话本身的信息 |
| 对话内容 | message、compaction、branch_summary、custom_message | 模型的上下文 |
| 操作记录 | model_change、thinking_level_change、custom | 用户操作与扩展数据 |

操作记录也上树（如"切换了模型"也是一个节点），这样回退到任何历史点都能还原当时的会话状态。

## Pi 源码怎么实现（0.84.2）

会话格式在 `packages/coding-agent/docs/session-format.md`，版本 3。头记录：

```json
{"type":"session","version":3,"id":"uuid","timestamp":"2024-12-03T14:00:00.000Z","cwd":"/path/to/project","parentSession":"/path/to/original/session.jsonl"}
```

对话记录（消息节点）：

```json
{"type":"message","id":"a1b2c3d4","parentId":"prev1234","timestamp":"2024-12-03T14:00:01.000Z","message":{"role":"user","content":"Hello"}}
{"type":"message","id":"b2c3d4e5","parentId":"a1b2c3d4","timestamp":"2024-12-03T14:00:02.000Z","message":{"role":"assistant","content":[{"type":"text","text":"Hi!"}],"stopReason":"stop"}}
{"type":"message","id":"c3d4e5f6","parentId":"b2c3d4e5","timestamp":"2024-12-03T14:00:03.000Z","message":{"role":"toolResult","toolCallId":"call_123","toolName":"bash","content":[{"type":"text","text":"output"}],"isError":false}}
```

压缩记录（保留"切掉之前"的信息）：

```json
{"type":"compaction","id":"f6g7h8i9","parentId":"e5f6g7h8","timestamp":"2024-12-03T14:10:00.000Z","summary":"User discussed X, Y, Z...","firstKeptEntryId":"c3d4e5f6","tokensBefore":50000}
```

分支摘要记录（离开分支时生成）：

```json
{"type":"branch_summary","id":"g7h8i9j0","parentId":"a1b2c3d4","timestamp":"2024-12-03T14:15:00.000Z","fromId":"f6g7h8i9","summary":"Branch explored approach A..."}
```

要点：

- 每个节点都有 `id` 和 `parentId`；`parentId` 指向文件里更早的节点，形成树。
- `compaction` 记录带 `firstKeptEntryId`（压缩后保留的第一条）与 `tokensBefore`（压缩前 token 数）——恢复时能重建"压缩发生在哪、省了多少"。
- `branch_summary` 带 `fromId`（离开的分支叶子），摘要本身不进入主上下文，但恢复分支时可读。
- 扩展可以用 `custom` / `custom_message` 写入自己的数据，前提是结构合法。

## 当前 Pi 行为

- 会话自动保存到 `~/.pi/agent/sessions/`，按工作目录组织。
- `/tree` 导航会话树与分支；`/export` 才生成 HTML——两者职责不同。
- 旧版本会话加载时自动迁移到 v3。
- `/tree` 切换分支时可为离开的分支生成摘要（分支摘要，见 [07 章](../07-context-and-compaction/README.md)）。

## 在 Pi 里怎么操作

- `/new`：开始新会话；`/resume`（或启动时 `pi -r`）：浏览并选择历史会话。
- `/tree`：在会话树中导航，从任意历史点继续。
- `/fork`：从某条历史用户消息创建新会话，等价于 `pi --fork <path|id>`。
- `/export [file]`：把会话导出为 HTML。

## Python 对照

[session_tree.py](../../learn_pi_lab/labs/session_tree.py) 实现课程专用的不可变 transcript tree，`validate()` 拒绝四种结构错误：重复 id、悬空父节点、自指、循环：

```python
class TranscriptTree:
    def validate(self) -> None:
        # 1. 重复 id：entries_by_id 冲突
        # 2. 悬空 parent：parent_id 不在表里
        # 3. 自指：parent_id == id
        # 4. 循环：沿 parent 链走，用 visited 集合检测
        ...
```

`path_to(leaf_id)` 沿 `parentId` 链回溯到根再反转，得到 root → leaf 分支——与 Pi 的 `path_to_entry`（`tau_agent/session/tree.py`，用 `seen` 集合检测环）逻辑一致。

[session_inspector.py](../../projects/session_inspector.py) 逐行读取 JSONL，统计消息角色与压缩记录（`type == "compaction"`），不执行记录内容、不修改会话——是"解析工具应保留未知记录"的只读示例。

## 实现对照：Pi 源码与 Tau 双版本

会话 entry 是两套实现里对应最整齐的部分——Tau 的 `tau_agent/session/entries.py` 与 Pi 的 session-format 几乎一一对应。

**entry 类型对照**：

| Pi 0.84.2（session-format.md） | Tau（entries.py） |
| --- | --- |
| `message` | `MessageEntry` |
| `model_change` | `ModelChangeEntry` |
| `thinking_level_change` | `ThinkingLevelChangeEntry` |
| `compaction` | `CompactionEntry` |
| `branch_summary` | `BranchSummaryEntry` |
| `label` | `LabelEntry` |
| `session_info` | `SessionInfoEntry` |
| `custom` / `custom_message` | `CustomEntry` |

**共同基类**（append-only 的结构基础）：

```python
# Tau: tau_agent/session/entries.py（原文节选）
class BaseSessionEntry(BaseModel):
    """所有 append-only 会话 entry 的公共字段。"""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=new_entry_id)  # uuid4().hex
    parent_id: str | None = None
    timestamp: float = Field(default_factory=current_timestamp)
```

```json
// Pi 0.84.2: session-format.md 的对应记录
{"type":"message","id":"a1b2c3d4","parentId":"prev1234","timestamp":"2024-12-03T14:00:01.000Z","message":{...}}
```

概念对照：TS/JSON 的 `parentId` ↔ Python 的 `parent_id`；每个 entry 只带 `parent_id`、不带孩子——正是“认父不认子”的字段级实现。

**压缩 entry**（记录切掉了什么）：

```python
# Tau: tau_agent/session/entries.py（原文节选）
class CompactionEntry(BaseSessionEntry):
    """替换旧消息 entry 的上下文摘要，回放时生效。"""
    type: Literal["compaction"] = "compaction"
    summary: str
    replaces_entry_ids: list[str] = Field(default_factory=list)  # 被压缩覆盖的 entry
    first_kept_entry_id: str | None = None
    tokens_before: int | None = None
```

与 Pi 的 `compaction` 记录（`summary` + `firstKeptEntryId` + `tokensBefore`）同构；Tau 额外用 `replaces_entry_ids` 明确列出被替换的 entry，回放时据此重建。

**回放应用**（Tau `memory.py` 的 `_apply_compaction`）：把被替换的 message 行换成一条摘要消息，只插入一次：

```python
# Tau: tau_agent/session/memory.py（原文节选）
def _apply_compaction(message_rows, entry):
    replaced_ids = set(entry.replaces_entry_ids)
    retained = []
    inserted_summary = False
    for entry_id, message in message_rows:
        if entry_id not in replaced_ids:
            retained.append((entry_id, message))
            continue
        if not inserted_summary:
            retained.append((entry.id, UserMessage(content=_format_compaction_summary(entry.summary))))
            inserted_summary = True
    if not inserted_summary:
        retained.append((entry.id, UserMessage(content=_format_compaction_summary(entry.summary))))
    return retained
```

这正是 [07 章](../07-context-and-compaction/README.md) 说的“摘要继续保留因果”：压缩不是删除，而是用一条摘要消息替换旧消息。

**JSONL 编解码**（Tau `jsonl.py`）——每一行的写入与读回都走同一个判别模型：

```python
# Tau: tau_agent/session/jsonl.py（原文节选）
_SESSION_ENTRY_ADAPTER: TypeAdapter[SessionEntry] = TypeAdapter(SessionEntry)

class SessionJsonlError(ValueError):
    """一行会话 JSONL 无法解码时抛出。"""

def entry_to_json_line(entry: SessionEntry) -> str:
    """序列化一条 entry，只使用规范的 Pi wire 形态（驼峰别名）。"""
    return _SESSION_ENTRY_ADAPTER.dump_json(entry, exclude_none=True).decode() + "\n"

def entry_from_json_line(line: str, *, line_number: int | None = None) -> SessionEntry:
    """反序列化一条 entry；旧版本消息先迁移再校验。"""
    try:
        payload = json.loads(line)
        migrated = _migrate_session_entry(payload)
        return _SESSION_ENTRY_ADAPTER.validate_python(migrated)
    except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
        raise SessionJsonlError(f"Invalid session entry{location}: {exc}") from exc

def entries_from_json_lines(lines: list[str]) -> list[SessionEntry]:
    """按顺序反序列化非空 JSONL 行。"""
    entries = []
    for index, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        entries.append(entry_from_json_line(line, line_number=index))
    return entries
```

两个设计要点：

- **迁移在持久化边界做**（`_migrate_session_entry`）：旧版消息字段在**读回时**迁移，而不是改历史文件——用户会话历史不能因 API 演进而失效。
- **坏行报错不静默**：`SessionJsonlError` 带行号；与 [10 章](../10-protocol-and-integration/README.md) 的“无效 JSON 不能静默吞掉”一致。

## Python 实验

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
- 恢复会话后，工具调用记录可能已过期或无效，需要审计而非直接信任。
