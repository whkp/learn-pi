# Learn Pi 课程地图

本课程以固定的 Pi 源码版本（0.84.2）为事实基线，用离线、标准库 Python 实验解释可迁移的机制。每一章围绕一个大主题，讲清"是什么 / 怎么做 / 为什么"，并给出 Pi 源码（TypeScript）与 Python 教学模型的双重对照。

<!-- course-chapter-manifest:start -->
- `00-course-map.md`
- `01-architecture/README.md`
- `02-agent-loop/README.md`
- `03-tools/README.md`
- `04-messages-and-memory/README.md`
- `05-sessions/README.md`
- `06-events-and-extensions/README.md`
- `07-context-and-compaction/README.md`
- `08-providers-and-models/README.md`
- `09-reliability/README.md`
- `10-protocol-and-integration/README.md`
- `11-projects-and-evaluation/README.md`
<!-- course-chapter-manifest:end -->

上面的清单是课程契约检查器使用的主章节清单。新写或重写的主章节须先满足本页的教学结构，再加入此清单。

## 学习目标

- 了解课程以哪个 Pi 版本为准，以及如何查找相应的源码说明。
- 区分 Pi 的 TypeScript 实现、Tau 的 Python 实现与本课程的离线 Python 教学模型。
- 使用本仓库的检查脚本验证课程资料。

## 当前 Pi 行为

Pi 的实际行为以固定版本（0.84.2）的源码为准；课程叙述应链接到 [Pi 源码映射](pi-source-map.md)，而不是把示例 Python 当作 Pi 的生产实现。

## Python 实验

课程实验位于 `learn_pi_lab` 包中，且只依赖 Python 标准库。可以先运行：

```sh
python3 -m learn_pi_lab
```

## 验证方式

在仓库根目录运行以下命令：

```sh
python3 scripts/check_course_contract.py
python3 scripts/check_markdown_links.py
```

两条命令成功时都会输出 `OK`。

## 边界与安全

本课程不在检查或实验期间访问网络、调用模型 API、读取本仓库外的 Pi 源码，也不会执行学习者提供的 shell 命令。

## 配套资料

- [Pi 源码映射](pi-source-map.md)（固定基线：0.84.2 @ 914cf147）
- [术语表](glossary.md)
- Tau：Pi 的 Python 对照实现（tau_agent / tau_ai / tau_coding），与本章的 Python 教学模型对照阅读
- 各章引用 Pi 0.84.2 源码路径：`packages/agent/src/...`、`packages/coding-agent/src/...`、`packages/coding-agent/docs/...`
