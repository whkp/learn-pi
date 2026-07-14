# 扩展系统与工具链

Pi 扩展是 TypeScript 代码。课程在此只陈述固定基线能够支持的事件和改写边界。

## 扩展能做什么

扩展可以注册工具、命令、快捷键、UI 组件和 Provider 集成，也可以订阅生命周期事件。事件名与 payload 类型应从当前 ExtensionAPI 类型定义读取，而不是从旧示例复制。

## 容易混淆的修正

- 会话关闭事件名是 session_shutdown，不是 session_end。
- 当前没有 settings_change 事件。
- 工具调用输入的改写是在事件对象上原地进行；不存在返回 modifiedInput 的协议。
- 在压缩开始前定制行为应使用 session_before_compact。

扩展应该验证所有外部输入、限制可执行操作，并把异常变成明确的用户反馈或日志。

## Python 对照实验

[extension_events.py](../../learn_pi_lab/labs/extension_events.py) 演示按注册顺序派发、异常隔离、可重复取消订阅与深度快照：

    python3 -m learn_pi_lab lab events
    python3 -m unittest tests.test_07_extension_events -v

这是课程自己的事件总线，不是 Pi ExtensionAPI 的 Python 绑定。
