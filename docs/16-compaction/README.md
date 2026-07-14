# 会话压缩与上下文管理

压缩是会话生命周期的一部分：它应在保留近期上下文、工具因果关系和用户目标之间取得平衡。

## 当前 Pi 行为

当前 Pi 的压缩配置、触发条件和会话条目格式必须以固定基线的 compaction 与 session-format 文档为准。扩展在压缩前的定制边界是 session_before_compact。/tree 切换分支时，Pi 可以为离开的分支生成摘要；它是会话导航的上下文保留行为，不是导出功能。

## Python 对照实验

[compaction.py](../../learn_pi_lab/labs/compaction.py) 使用固定的 transcript units 计算保留集合，并保证成对的工具调用与结果不会在切割点被拆开：

    python3 -m learn_pi_lab lab compaction
    python3 -m unittest tests.test_05_compaction -v

它没有估算 token、没有调用 LLM，也不写 Pi 的会话文件。

## 设计检查

压缩前后都应能回答：保留了哪个用户目标、哪些文件被修改、哪些工具结果仍相关、哪些事实只是旧摘要。摘要中的不确定性必须被标明，不能伪造验证结果。
