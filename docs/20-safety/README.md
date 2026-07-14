# 安全与权限边界

本章将 Agent 的能力拆成可审查的意图、目标与执行边界，而不是把模型输出直接交给 shell。

## 学习目标

- 为工具调用建立明确的允许列表。
- 在文件路径进入执行层前完成归一化和边界检查。
- 区分课程中的安全模型与 Pi 的实际 TypeScript 权限、工具和扩展 API。

## 当前 Pi 行为

Pi 通过 coding-agent 的工具、设置和扩展机制执行工作流。扩展可以在工具调用生命周期中观察或修改输入；当前扩展事件名称和返回约定应以固定基线的 extensions 文档及类型定义为准。课程不把一个 Python 允许列表描述为 Pi 的内置权限系统。

## Python 实验

tool_permissions.py 只接受裸命令 ls、cat、grep，并将路径限制在注入的根目录内；它从不调用真实 shell。

    python3 -m learn_pi_lab lab permissions

safe_review_runner.py 进一步把审查限制为 read、search、list 三种意图：

    from pathlib import Path
    from projects.safe_review_runner import ReviewPolicy, review_request

    decision = review_request(ReviewPolicy(Path.cwd()), "read", "README.md")
    print(decision)

## 验证方式

    python3 -m unittest tests.test_02_tool_permissions tests.test_11_projects -v

## 边界与安全

允许列表不是沙箱。生产实现还需要操作系统隔离、最小凭据、审计日志、用户确认和针对符号链接及竞态条件的防御。不要由字符串拼接生成 shell 命令。
