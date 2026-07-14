# Learn Pi

面向开发者的 Pi 编码智能体学习仓库：准确资料、可运行的 Python 实验、自动化测试与离线实战项目。

## 先读这里

- 事实基线：Pi 0.75.3，提交 144b93861f339ce353531f6873d377a1e4b2f5c4。
- 基线与源码入口见 [Pi 源码映射](docs/pi-source-map.md)；任何 API 细节以该版本源码和官方文档为准。
- Pi 本身是 TypeScript 项目；本仓库的 Python 仅是依赖标准库的教学模型，既不是 Pi SDK，也不是 Pi 的移植版。
- 当前 Pi Monorepo 的包是 ai、agent、tui、coding-agent；课程不再把不存在的 pi-web-ui 当作当前包。

## 快速开始

Pi 当前需要 Node.js 22.19.0 或更高版本。安装和认证请以 Pi 的 Quickstart 与 Settings 文档为准；不要把密钥写进仓库。

    npm install -g @earendil-works/pi-coding-agent
    pi

本课程的 Python 实验不访问网络、不调用模型，也不会执行学习者提供的 shell 命令：

    cd learn-pi
    python3 -m learn_pi_lab lab agent-loop
    python3 -m unittest discover -s tests -v

## 学习路径

| 阶段 | 阅读重点 | 动手产物 |
| --- | --- | --- |
| 基础 | [01 Agent](docs/01-what-is-coding-agent/README.md)、[02 Pi 概览](docs/02-pi-overview/README.md)、[03 架构](docs/03-architecture-deep-dive/README.md) | agent-loop Python 实验 |
| 运行机制 | [04 核心模块](docs/04-core-modules/README.md)、[05 扩展](docs/05-extension-system/README.md)、[08 会话](docs/08-session-management/README.md) | 工具策略、会话树、事件总线 |
| 配置与集成 | [09 模型](docs/09-providers-and-models/README.md)、[11 扩展开发](docs/11-extensions-development/README.md)、[16 压缩](docs/16-compaction/README.md)、[17 SDK/RPC](docs/17-sdk-and-rpc/README.md) | Provider 注册表、重试、JSONL 编解码 |
| 工程实践 | [19 实战项目](docs/19-real-projects/README.md)、[20 安全](docs/20-safety/README.md)、[21 可靠性](docs/21-reliability/README.md)、[22 组合](docs/22-composition-and-mcp/README.md)、[23 评测](docs/23-testing-and-evaluation/README.md) | 四个离线 mini-project |

完整术语请看 [术语表](docs/glossary.md)，课程资料的验证约定见 [课程地图](docs/00-course-map.md)。

## Python 实验

| 主题 | 模块 | 运行方式 |
| --- | --- | --- |
| Agent 循环 | learn_pi_lab/labs/agent_loop.py | python3 -m learn_pi_lab lab agent-loop |
| 最小权限 | learn_pi_lab/labs/tool_permissions.py | python3 -m learn_pi_lab lab permissions |
| 规则文件 | learn_pi_lab/labs/context_files.py | 见模块测试 |
| 会话分支 | learn_pi_lab/labs/session_tree.py | python3 -m learn_pi_lab lab session-tree |
| 压缩边界 | learn_pi_lab/labs/compaction.py | python3 -m learn_pi_lab lab compaction |
| 资源发现 | learn_pi_lab/labs/resources.py | 见模块测试 |
| 事件派发 | learn_pi_lab/labs/extension_events.py | python3 -m learn_pi_lab lab events |
| Provider 目录 | learn_pi_lab/labs/provider_registry.py | python3 -m learn_pi_lab lab providers |
| 重试模型 | learn_pi_lab/labs/reliability.py | python3 -m learn_pi_lab lab reliability |
| JSONL RPC | learn_pi_lab/labs/rpc_jsonl.py | python3 -m learn_pi_lab lab rpc-jsonl |

## 离线实战项目

- [Session Inspector](projects/session_inspector.py)：只读统计 JSONL 会话记录。
- [Safe Review Runner](projects/safe_review_runner.py)：把审查意图约束为根目录内的只读目标。
- [CI Review Pipeline](projects/ci_review_pipeline.py)：将课程契约、链接和单元测试汇总为稳定结果。
- [RPC Console](projects/rpc_console.py)：使用允许列表处理单条 JSON 请求，不启动子进程。

每个项目都由 [test_11_projects.py](tests/test_11_projects.py) 覆盖。

## 验证

    python3 -m unittest discover -s tests -v
    python3 scripts/check_course_contract.py
    python3 scripts/check_markdown_links.py

## 课程边界

本课程使用 Python 来展示安全边界、状态快照、重试与协议解析等通用设计。生产环境中应使用 Pi 的 TypeScript API、实际认证与权限机制；示例中的固定数据和策略不可直接替代生产配置。

## License

本项目采用 [MIT License](LICENSE)。Pi 的源码版权归 earendil-works 所有。
