# 测试与评测

能运行一次不等于可维护。课程把行为测试、文档契约和小型集成项目作为同一条质量链。

## 学习目标

- 用确定性测试覆盖允许、拒绝与异常路径。
- 检查 Markdown 本地链接和课程基线标记。
- 为真实 Agent 评测区分功能正确性、工具安全性与结果质量。

## 当前 Pi 行为

Pi 的实际测试、构建和发布流程属于其自身仓库。本课程只验证 Learn Pi 的 Python 教学模型与本地文档，不会替 Pi 的 TypeScript 测试套件背书。

## Python 实验

CI Review Pipeline 将三项检查收敛为稳定报告：

    from projects.ci_review_pipeline import build_review_report

    print(build_review_report(
        markdown_links_ok=True,
        course_contract_ok=True,
        unit_tests_ok=True,
    ))

## 验证方式

    python3 -m unittest discover -s tests -v
    python3 scripts/check_course_contract.py
    python3 scripts/check_markdown_links.py

## 边界与安全

确定性单元测试不能证明模型在开放式任务上永远正确。生产评测还应包含固定样本集、人工复核、失败分类、回归门槛和不得泄露敏感数据的日志策略。
