# 会话管理

Pi 会话用于恢复上下文和导航历史；会话文件是需要兼容性约束的持久化数据，而不是可随意改写的数组。

## 当前 Pi 行为

当前基线将会话保存为 JSONL v3：文件由一行一个 JSON 记录构成，不是一个 JSON 数组。记录类型与字段可随着版本演进，因此解析工具应保留未知记录而非静默重写。

/tree 的职责是导航会话历史和分支，不是导出命令。使用 /new、/resume、继续或 fork 等会话命令时，请以固定基线的 sessions 与 session-format 文档为准。

## Python 对照实验

[session_tree.py](../../learn_pi_lab/labs/session_tree.py) 建立课程专用的不可变 transcript tree，拒绝重复、悬空、自指和循环节点：

    python3 -m learn_pi_lab lab session-tree

它明确不是 Pi JSONL v3 解析器。[session_inspector.py](../../projects/session_inspector.py) 则只读统计 JSONL 行，不修改会话。

## 安全提示

不要由第三方工具直接改写正在使用的会话文件。保留备份、在写入前验证版本，并在恢复后审计工具调用记录。
