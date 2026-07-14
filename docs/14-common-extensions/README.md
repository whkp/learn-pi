# 常用扩展实践

扩展能把 Pi 接入团队工作流，但它们与普通应用代码一样拥有完整的系统权限。先建立边界，再增加便利功能。

## 当前 Pi 行为

扩展可注册工具、命令、快捷键和 UI 行为，也可订阅当前 ExtensionAPI 声明的事件。清理资源应监听 session_shutdown。不要使用旧的 session_end 或 settings_change，也不要通过 modifiedInput 返回值改写工具输入。

扩展、技能、提示词和主题可来自项目目录、用户目录或安装包。自动发现、加载顺序和重载行为请查看固定基线的 extensions、skills、prompt-templates、themes 与 packages 文档。

## 适合从小开始的三种扩展

1. 只读检查：收集版本、测试结果或 git 状态，输出结构化报告。
2. 受控工作流：将预先定义的参数传给已有工具，并保留用户确认。
3. 会话辅助：为特定里程碑添加标签或在压缩前提供摘要提示。

每种扩展都应显式验证输入，在异常时留下可理解的错误，并允许用户禁用它。

## Python 对照实验

本课程不执行 TypeScript 扩展。使用下面的安全实验理解相同的工程原则：

    python3 -m learn_pi_lab lab events
    python3 -m learn_pi_lab lab permissions
    python3 -m unittest tests.test_02_tool_permissions tests.test_07_extension_events -v

## 安全清单

- 安装第三方包前审查源码和依赖。
- 为写文件、提交、网络和命令执行增加独立确认。
- 不记录令牌、环境变量或完整的私密命令输出。
- 在临时工作区测试，再扩大作用域。
