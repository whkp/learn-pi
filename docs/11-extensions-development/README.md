# Extensions 扩展开发

本章给出扩展开发的正确起点：先用当前类型和文档确认 API，再把副作用置于可测试边界内。

## 当前 Pi 行为

扩展以 TypeScript 加载，可注册工具、命令和 UI 行为，并订阅 ExtensionAPI 声明的生命周期事件。session_shutdown 是正确的关闭事件名；settings_change 不在当前事件集合中。工具调用输入在 hook 内原地变更，不通过 modifiedInput 返回值替换。

创建或更新扩展前，读取固定基线的 extensions 文档、扩展类型定义和内置扩展示例。不要从本仓库 Python 代码推断 TypeScript 参数类型。

## 推荐开发循环

1. 为单一工具或 hook 写一个最小扩展。
2. 显式校验参数和工作目录。
3. 对危险副作用增加确认、允许列表和失败信息。
4. 在临时会话中测试，再加入项目或全局扩展目录。

## Python 对照实验

[extension_events.py](../../learn_pi_lab/labs/extension_events.py) 将 handler 异常记录为数据，保证后续 handler 仍能执行：

    python3 -m unittest tests.test_07_extension_events -v

该实验不加载或运行 TypeScript 扩展。
