# 实战项目

这里提供四个可运行、无网络、无模型调用、无 shell 执行的 Python mini-project。它们训练的是可迁移的 Agent 工程边界，不是 Pi TypeScript 扩展的复制品。

## 项目一：Session Inspector

[session_inspector.py](../../projects/session_inspector.py) 逐行读取 JSONL，会统计消息角色和压缩记录，不执行记录中的内容。

## 项目二：Safe Review Runner

[safe_review_runner.py](../../projects/safe_review_runner.py) 将审查限定为只读意图，并拒绝绝对路径、父目录跳转和非读取操作。

## 项目三：CI Review Pipeline

[ci_review_pipeline.py](../../projects/ci_review_pipeline.py) 把课程契约、Markdown 链接和单元测试结果汇总成有序报告。

## 项目四：RPC Console

[rpc_console.py](../../projects/rpc_console.py) 使用课程 JSONL 编解码器实现一个允许列表 ping 接口；它不调用任何命令。

## 验证

    python3 -m unittest tests.test_11_projects -v
    python3 -m unittest discover -s tests -v

## 迁移到 Pi 前

如果要把任一思路迁移到 Pi，请重新用 TypeScript 和当前 ExtensionAPI、SDK 或 RPC 文档实现，并逐项补上认证、权限、取消、日志脱敏和端到端测试。
