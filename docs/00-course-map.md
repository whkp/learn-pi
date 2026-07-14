# Learn Pi 课程地图

本课程以固定的 Pi 源码版本为事实基线，并用离线、标准库 Python 实验解释可迁移的机制。

<!-- course-chapter-manifest:start -->
- `00-course-map.md`
- `20-safety/README.md`
- `21-reliability/README.md`
- `22-composition-and-mcp/README.md`
- `23-testing-and-evaluation/README.md`
<!-- course-chapter-manifest:end -->

上面的清单是课程契约检查器使用的主章节清单。既有 01 至 19 章节保留为参考路线；新写或重写的主章节须先满足本页的教学结构，再加入此清单。

## 学习目标

- 了解课程以哪个 Pi 版本为准，以及如何查找相应的源码说明。
- 区分 Pi 的 TypeScript 实现和本课程的离线 Python 教学模型。
- 使用本仓库的检查脚本验证课程资料。

## 当前 Pi 行为

Pi 的实际行为以固定版本的源码为准；课程叙述应链接到 [Pi 源码映射](pi-source-map.md)，而不是把示例 Python 当作 Pi 的生产实现。

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

- [Pi 源码映射](pi-source-map.md)
- [术语表](glossary.md)
- [20 安全与权限边界](20-safety/README.md)
- [21 可靠性、取消与错误边界](21-reliability/README.md)
- [22 组合、资源与 MCP 边界](22-composition-and-mcp/README.md)
- [23 测试与评测](23-testing-and-evaluation/README.md)
